"""Orchestration helpers for the `redeploy run` command."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger
from rich.console import Console


def setup_run_logging(resolved_spec: str) -> tuple[int, Path, datetime]:
    """Attach file logging; return (handler_id, log_file, started_at)."""
    started_at = datetime.now(timezone.utc)
    log_dir = Path.cwd() / ".redeploy" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"redeploy-{started_at.strftime('%Y%m%d_%H%M%S')}.log"
    handler_id = logger.add(
        log_file,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} | {message}",
        enqueue=True,
    )
    logger.info("redeploy run started — spec={}", resolved_spec)
    return handler_id, log_file, started_at


def run_lint_phase(console: Console, resolved_spec: str, lint: bool, file_handler_id: int) -> object | None:
    """Run static lint when enabled; exit process on hard failures."""
    if not lint:
        return None

    from ...analyze import SpecAnalyzer, IssueSeverity

    analyzer = SpecAnalyzer(base_dir=Path.cwd())
    _, lint_result = analyzer.analyze_file(Path(resolved_spec))
    if not lint_result.issues:
        console.print("[green]  ✓ lint passed[/green]")
        return lint_result

    console.print("\n[bold]lint[/bold]")
    for issue in lint_result.issues:
        color = "red" if issue.severity == IssueSeverity.ERROR else "yellow"
        prefix = f"[{color}]{issue.severity.value}[/{color}]"
        step = f" ({issue.step_id})" if issue.step_id else ""
        console.print(f"  {prefix}{step} {issue.category}: {issue.message}")
        if issue.suggestion:
            console.print(f"      [dim]→ {issue.suggestion}[/dim]")

    if not lint_result.passed:
        console.print("\n[red]✗ lint failed — fix errors above or use --no-lint to skip.[/red]")
        logger.remove(file_handler_id)
        sys.exit(1)

    console.print(f"[yellow]⚠ lint passed with {len(lint_result.warnings())} warning(s)[/yellow]")
    return lint_result


def run_preflight_phase(
    console: Console,
    *,
    preflight: bool,
    resolved_spec: str,
    spec,
    migration,
    lint_result,
    preflight_schema_out: str,
    preflight_remote: bool,
    dry_run: bool,
    strict_preflight: bool,
    file_handler_id: int,
) -> None:
    """Generate preflight schema and optionally abort on blockers."""
    if not preflight:
        return

    from ...analyze import generate_preflight_schema, save_preflight_schema

    preflight_result = generate_preflight_schema(
        spec_path=Path(resolved_spec),
        spec=spec,
        migration=migration,
        lint_result=lint_result,
        base_dir=Path.cwd(),
        remote_check=bool(preflight_remote and not dry_run),
    )
    save_preflight_schema(preflight_result.schema, Path(preflight_schema_out))

    blockers = len(preflight_result.blockers)
    console.print(f"\n[bold]preflight[/bold]  [dim]schema saved → {preflight_schema_out}[/dim]")
    if not blockers:
        console.print("[green]  ✓ preflight passed (no blockers)[/green]")
        return

    console.print(f"[yellow]⚠ preflight blockers: {blockers}[/yellow]")
    for blocker in preflight_result.blockers[:10]:
        sid = f" ({blocker.get('step_id')})" if blocker.get("step_id") else ""
        console.print(f"  [yellow]- {blocker.get('type')}{sid}: {blocker.get('message')}[/yellow]")
    if blockers > 10:
        console.print(f"  [dim]... and {blockers - 10} more blockers in schema file[/dim]")
    if strict_preflight:
        console.print("\n[red]✗ strict preflight failed — aborting before apply[/red]")
        logger.remove(file_handler_id)
        sys.exit(1)
