"""`redeploy apply` command."""
from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console


@click.command()
@click.option(
    "--plan", "plan_file", default="migration-plan.yaml", show_default=True,
    type=click.Path(exists=True), help="Migration plan file",
)
@click.option("--dry-run", is_flag=True, help="Show steps without executing")
@click.option("--step", default=None, help="Run only a specific step by ID")
@click.option("-o", "--output", default=None, type=click.Path(), help="Save results to file after apply")
@click.pass_context
def apply(ctx, plan_file, dry_run, step, output):
    """Execute a migration plan."""
    from ...apply import Executor

    console = Console()
    executor = Executor.from_file(Path(plan_file))

    if step:
        matched = [s for s in executor.plan.steps if s.id == step]
        if not matched:
            console.print(f"[red]Step '{step}' not found in plan[/red]")
            ids = ", ".join(s.id for s in executor.plan.steps)
            console.print(f"Available: {ids}")
            sys.exit(1)
        executor.plan.steps = matched

    executor.dry_run = dry_run
    prefix = "[DRY RUN] " if dry_run else ""
    console.print(
        f"\n{prefix}[bold]Applying: {executor.plan.from_strategy.value}"
        f" → {executor.plan.to_strategy.value}[/bold]  "
        f"({len(executor.plan.steps)} steps)"
    )

    ok = executor.run()
    console.print(f"\n{executor.summary()}")

    if output:
        executor.save_results(Path(output))

    if not ok:
        sys.exit(1)
