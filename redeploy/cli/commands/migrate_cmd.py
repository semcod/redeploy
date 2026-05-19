"""`redeploy migrate` command — detect → plan → apply."""
from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console


@click.command()
@click.option("--host", required=True, help="SSH host (user@ip) or 'local'")
@click.option("--app", default=None, show_default=True, help="Application name (default from redeploy.yaml)")
@click.option("--domain", default=None)
@click.option("--target", default=None, type=click.Path(), help="Target config YAML")
@click.option(
    "--strategy", default="docker_full", show_default=True,
    type=click.Choice(["docker_full", "podman_quadlet", "k3s", "native_kiosk", "systemd"]),
)
@click.option("--version", "target_version", default=None)
@click.option("--compose", multiple=True)
@click.option("--env-file", default=None)
@click.option("--dry-run", is_flag=True)
@click.option("--infra-out", default="infra.yaml", show_default=True, type=click.Path())
@click.option("--plan-out", default="migration-plan.yaml", show_default=True, type=click.Path())
@click.pass_context
def migrate(ctx, host, app, domain, target, strategy, target_version,
            compose, env_file, dry_run, infra_out, plan_out):
    """Full pipeline: detect → plan → apply."""
    from ...apply import Executor
    from ...detect import Detector
    from ...models import DeployStrategy, ProjectManifest
    from ...plan import Planner

    console = Console()
    manifest = ProjectManifest.find_and_load(Path.cwd())
    app = app or (manifest.app if manifest else "c2004")
    domain = domain or (manifest.domain if manifest else None)

    console.print("\n[bold]Step 1/3 — detect[/bold]")
    detector = Detector(host=host, app=app, domain=domain)
    state = detector.run()
    detector.save(state, Path(infra_out))
    console.print(
        f"  Strategy: {state.detected_strategy}  "
        f"  Version: {state.current_version or '?'}  "
        f"  Conflicts: {len(state.conflicts)}"
    )

    console.print("\n[bold]Step 2/3 — plan[/bold]")
    planner = Planner.from_files(Path(infra_out), Path(target) if target else None)
    planner.target.strategy = DeployStrategy(strategy)
    if domain:
        planner.target.domain = domain
    if target_version:
        planner.target.verify_version = target_version
    if compose:
        planner.target.compose_files = list(compose)
    if env_file:
        planner.target.env_file = env_file

    migration = planner.run()
    planner.save(migration, Path(plan_out))
    console.print(
        f"  Steps: {len(migration.steps)}  Risk: {migration.risk.value}  "
        f"Downtime: {migration.estimated_downtime}"
    )

    console.print(f"\n[bold]Step 3/3 — apply{'  (dry-run)' if dry_run else ''}[/bold]")
    executor = Executor(migration, dry_run=dry_run)
    ok = executor.run()
    console.print(f"\n{executor.summary()}")

    if not ok:
        sys.exit(1)
