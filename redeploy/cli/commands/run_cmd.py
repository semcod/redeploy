"""`redeploy run` command — spec-driven plan + apply."""
from __future__ import annotations

import sys
from pathlib import Path

import click
from loguru import logger
from rich.console import Console

from ..display import print_plan_table
from .plan_apply_report import write_markdown_report
from .plan_apply_run import run_lint_phase, run_preflight_phase, setup_run_logging
from .plan_apply_shared import (
    apply_manifest_to_spec,
    detect_project_version,
    ensure_redeployignore,
    inject_project_sync_step,
    load_dotenv_for_heal,
    load_spec_for_run,
    perform_live_detect,
    print_heal_banner,
    print_spec_summary,
    run_apply,
)


@click.command()
@click.argument("spec_file", default=None, required=False, type=click.Path(), metavar="SPEC")
@click.option("--dry-run", is_flag=True, help="Show steps without executing")
@click.option("--plan-only", is_flag=True, help="Generate plan but do not apply")
@click.option("--detect", "do_detect", is_flag=True, help="Run live detect first (overrides source state from spec)")
@click.option("--plan-out", default=None, type=click.Path(), help="Save generated plan to file")
@click.option("-o", "--output", default=None, type=click.Path(), help="Save apply results to file")
@click.option("--report/--no-report", default=False, show_default=True, help="Write Markdown execution report next to the spec file.")
@click.option("--report-file", default=None, type=click.Path(), help="Override Markdown report output path.")
@click.option("--sync-project/--no-sync-project", default=True, show_default=True, help="Before apply, sync full local project tree to target.remote_dir.")
@click.option("--env", "env_name", default="", help="Named environment from redeploy.yaml (e.g. prod, dev, rpi5)")
@click.option("--progress-yaml", is_flag=True, help="Emit machine-readable YAML progress events to stdout")
@click.option("--resume", is_flag=True, help="Skip steps already completed in the persisted checkpoint.")
@click.option("--from-step", "from_step", default=None, help="Force start from this step id")
@click.option("--state-file", default=None, type=click.Path(), help="Override the path of the checkpoint file.")
@click.option("--no-state", is_flag=True, help="Disable checkpoint persistence for this run.")
@click.option("--heal/--no-heal", default=False, help="Self-healing: on failure, collect diagnostics and ask LLM to fix the spec, then retry.")
@click.option("--fix", "fix_hint", default=None, metavar="TEXT", help='Report a known problem to guide the LLM, e.g. --fix "brak ikon SVG w menu"')
@click.option("--max-heal-retries", default=3, show_default=True, help="Maximum number of LLM self-healing attempts.")
@click.option("--lint/--no-lint", default=True, show_default=True, help="Run static analysis before deployment.")
@click.option("--preflight/--no-preflight", default=True, show_default=True, help="Generate operational preflight schema before apply.")
@click.option("--preflight-schema-out", default=".redeploy/preflight-schema.yaml", show_default=True, type=click.Path())
@click.option("--preflight-remote/--no-preflight-remote", default=True, show_default=True)
@click.option("--strict-preflight/--no-strict-preflight", default=True, show_default=True)
@click.pass_context
def run(
    ctx, spec_file, dry_run, plan_only, do_detect, plan_out, output,
    report, report_file, sync_project, env_name, progress_yaml, resume, from_step,
    state_file, no_state, heal, fix_hint, max_heal_retries, lint,
    preflight, preflight_schema_out, preflight_remote, strict_preflight,
):
    """Execute migration from a single YAML spec (source + target in one file)."""
    from ...models import ProjectManifest
    from ...plan import Planner
    from ...plugins import load_user_plugins

    console = Console()
    ensure_redeployignore(Path.cwd(), console)

    manifest = ProjectManifest.find_and_load(Path.cwd())
    resolved_spec, spec = load_spec_for_run(console, spec_file, manifest)
    file_handler_id, _log_file, started_at = setup_run_logging(resolved_spec)

    apply_manifest_to_spec(console, manifest, spec, env_name)
    print_spec_summary(console, spec)

    lint_result = run_lint_phase(console, resolved_spec, lint, file_handler_id)

    if do_detect:
        planner = perform_live_detect(console, spec)
    else:
        planner = Planner.from_spec(spec)

    console.print("\n[bold]plan[/bold]")
    migration = planner.run()

    if sync_project:
        inject_project_sync_step(migration, spec, Path.cwd(), console)

    if plan_out:
        planner.save(migration, Path(plan_out))
        console.print(f"  [dim]plan saved → {plan_out}[/dim]")

    print_plan_table(console, migration)

    run_preflight_phase(
        console,
        preflight=preflight,
        resolved_spec=resolved_spec,
        spec=spec,
        migration=migration,
        lint_result=lint_result,
        preflight_schema_out=preflight_schema_out,
        preflight_remote=preflight_remote,
        dry_run=dry_run,
        strict_preflight=strict_preflight,
        file_handler_id=file_handler_id,
    )

    if plan_only:
        if report:
            write_markdown_report(
                console=console,
                migration=migration,
                spec_path=Path(resolved_spec),
                started_at=started_at,
                ok=True,
                executed=False,
                report_file=Path(report_file) if report_file else None,
            )
        console.print("\n[dim]--plan-only: stopping before apply[/dim]")
        logger.remove(file_handler_id)
        return

    load_user_plugins()

    if heal and not dry_run:
        load_dotenv_for_heal()
        from ...heal import HealRunner
        print_heal_banner(console, fix_hint)
        runner = HealRunner(
            migration=migration,
            spec_path=resolved_spec,
            host=migration.host,
            fix_hint=fix_hint or "",
            max_retries=max_heal_retries,
            dry_run=dry_run,
            console=console,
            version=detect_project_version(resolved_spec),
            progress_yaml=progress_yaml,
            resume=resume,
            from_step=from_step,
            state_file=state_file,
            no_state=no_state,
        )
        ok = runner.run()
    else:
        ok = run_apply(
            console, migration, dry_run, output,
            progress_yaml=progress_yaml,
            resume=resume,
            from_step=from_step,
            state_file=state_file,
            no_state=no_state,
            spec_path=str(resolved_spec),
        )

    if report:
        write_markdown_report(
            console=console,
            migration=migration,
            spec_path=Path(resolved_spec),
            started_at=started_at,
            ok=ok,
            executed=True,
            report_file=Path(report_file) if report_file else None,
        )

    if not ok:
        logger.remove(file_handler_id)
        sys.exit(1)
