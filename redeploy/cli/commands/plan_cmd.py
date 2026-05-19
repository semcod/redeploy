"""`redeploy plan` command."""
from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table


@click.command()
@click.option(
    "--infra", default="infra.yaml", show_default=True,
    type=click.Path(exists=True), help="InfraState file (from detect)"
)
@click.option("--target", default=None, type=click.Path(), help="Target config YAML (desired state)")
@click.option(
    "--strategy", default=None,
    type=click.Choice(["docker_full", "podman_quadlet", "k3s", "native_kiosk", "systemd"]),
    help="Override target strategy",
)
@click.option("--domain", default=None, help="Public domain for verify step")
@click.option("--version", "target_version", default=None, help="Target version to verify")
@click.option("--compose", multiple=True, help="Compose file(s) for docker_full strategy")
@click.option("--env-file", default=None, help="Env file path")
@click.option(
    "-o", "--output", default="migration-plan.yaml", show_default=True,
    type=click.Path(), help="Output migration plan file",
)
@click.pass_context
def plan(ctx, infra, target, strategy, domain, target_version, compose, env_file, output):
    """Generate migration-plan.yaml from infra.yaml + target config."""
    from ...models import DeployStrategy
    from ...plan import Planner

    console = Console()
    out_path = Path(output)
    planner = Planner.from_files(Path(infra), Path(target) if target else None)

    if strategy:
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
    planner.save(migration, out_path)

    console.print(
        f"\n[bold]Migration plan: {migration.from_strategy.value} → {migration.to_strategy.value}[/bold]"
    )
    console.print(f"  Risk:             {migration.risk.value}")
    console.print(f"  Estimated downtime: {migration.estimated_downtime}")
    console.print(f"  Steps:            {len(migration.steps)}")

    if migration.steps:
        console.print("\n[bold]Steps:[/bold]")
        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("#", style="dim", width=3)
        table.add_column("ID")
        table.add_column("Action", style="cyan")
        table.add_column("Description")
        table.add_column("Risk", style="dim")
        for i, step in enumerate(migration.steps, 1):
            table.add_row(str(i), step.id, step.action.value, step.description, step.risk.value)
        console.print(table)

    if migration.notes:
        console.print("\n[bold yellow]Notes:[/bold yellow]")
        for note in migration.notes:
            console.print(f"  • {note}")

    console.print(f"\n[dim]Saved to {out_path}[/dim]")
