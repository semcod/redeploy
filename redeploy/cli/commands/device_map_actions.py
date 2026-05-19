"""Non-Click logic for `redeploy device-map`."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from rich import box
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from ...models import DeviceMap


def print_saved_maps(console: Console) -> None:
    from ...models import DeviceMap

    maps = DeviceMap.list_saved()
    if not maps:
        console.print("[dim]No saved device maps. Run:[/dim]  redeploy device-map HOST --save")
        return

    table = Table(show_header=True, box=box.SIMPLE, padding=(0, 2))
    table.add_column("File", style="bold")
    table.add_column("Host", style="cyan")
    table.add_column("Board")
    table.add_column("Display")
    table.add_column("Issues")
    table.add_column("Scanned", style="dim")

    for path in maps:
        try:
            dm = DeviceMap.load(path)
            board = dm.hardware.board if dm.hardware else "?"
            errors = sum(1 for i in dm.issues if i.get("severity") in ("error", "critical"))
            warn = sum(1 for i in dm.issues if i.get("severity") == "warning")
            issues_str = (
                (f"[red]{errors}E[/red] " if errors else "")
                + (f"[yellow]{warn}W[/yellow]" if warn else "")
                or "[green]OK[/green]"
            )
            table.add_row(
                path.name,
                dm.host,
                board or "?",
                dm.display_summary,
                issues_str,
                dm.scanned_at.strftime("%Y-%m-%d %H:%M"),
            )
        except Exception as exc:
            table.add_row(path.name, "[red]parse error[/red]", str(exc)[:40], "", "", "")

    console.print(table)


def print_device_map_diff(console: Console, path_a: Path, path_b: Path) -> None:
    from ...models import DeviceMap

    map_a = DeviceMap.load(path_a)
    map_b = DeviceMap.load(path_b)
    console.print(
        f"\n[bold]diff[/bold]  [cyan]{map_a.id}[/cyan] ({map_a.scanned_at.strftime('%m-%d %H:%M')})"
        f"  →  [cyan]{map_b.id}[/cyan] ({map_b.scanned_at.strftime('%m-%d %H:%M')})\n"
    )

    def flatten(obj, prefix: str = "") -> dict:
        out: dict = {}
        if isinstance(obj, dict):
            for key, value in obj.items():
                out.update(flatten(value, f"{prefix}.{key}" if prefix else key))
        elif isinstance(obj, list):
            out[prefix] = str(obj)
        else:
            out[prefix] = str(obj)
        return out

    flat_a = flatten(map_a.model_dump(mode="json"))
    flat_b = flatten(map_b.model_dump(mode="json"))
    all_keys = sorted(set(flat_a) | set(flat_b))
    changed = [(k, flat_a.get(k), flat_b.get(k)) for k in all_keys if flat_a.get(k) != flat_b.get(k)]
    changed = [(k, old, new) for k, old, new in changed if not any(s in k for s in ("scanned_at", "id"))]

    if not changed:
        console.print("[green]✓ No differences[/green]")
        return

    table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    table.add_column("Key")
    table.add_column(f"A: {map_a.id[:20]}", style="red")
    table.add_column(f"B: {map_b.id[:20]}", style="green")
    for key, old, new in changed[:50]:
        table.add_row(key, str(old or "—")[:60], str(new or "—")[:60])
    console.print(table)
    if len(changed) > 50:
        console.print(f"[dim]... and {len(changed) - 50} more differences[/dim]")


def probe_device_map(
    console: Console,
    host: str,
    *,
    name: str,
    tags: tuple[str, ...],
    ssh_key: str | None,
    no_infra: bool,
):
    from ...detect import Detector
    from ...detect.hardware import probe_hardware
    from ...detect.remote import RemoteProbe
    from ...models import DeviceMap

    probe = RemoteProbe(host, ssh_key=ssh_key) if ssh_key else RemoteProbe(host)

    with console.status(f"[cyan]Probing hardware on {host}…[/cyan]"):
        try:
            hw_info = probe_hardware(probe)
        except ConnectionError as exc:
            console.print(f"[red]✗ {exc}[/red]")
            sys.exit(2)

    infra_state = None
    if not no_infra:
        with console.status(f"[cyan]Probing infra on {host}…[/cyan]"):
            try:
                infra_state = Detector(host).run()
            except Exception as exc:
                console.print(f"[yellow]⚠ infra probe failed (continuing): {exc}[/yellow]")

    issues: list[dict] = []
    if hw_info:
        for diag in hw_info.diagnostics:
            issues.append({
                "source": "hardware",
                "component": diag.component,
                "severity": diag.severity,
                "message": diag.message,
                "fix": diag.fix,
            })
    if infra_state:
        for conflict in infra_state.conflicts:
            issues.append({
                "source": "infra",
                "component": "service",
                "severity": conflict.severity.value,
                "message": f"{conflict.type}: {conflict.description}",
                "fix": conflict.fix_hint,
            })

    return DeviceMap(
        id=host,
        host=host,
        name=name,
        tags=list(tags),
        scanned_at=datetime.now(timezone.utc),
        hardware=hw_info,
        infra=infra_state,
        issues=issues,
    )


def execute_query_device_map(console: Console, dm: "DeviceMap", query_expr: str, output_fmt: str) -> None:
    from ...cli.query import execute_query
    execute_query(dm, query_expr, output_fmt, echo=console.print)


def emit_device_map(dm: "DeviceMap", output_fmt: str) -> None:
    import click
    if output_fmt == "json":
        import json as json_mod
        click.echo(json_mod.dumps(dm.model_dump(mode="json"), indent=2))
    else:
        click.echo(dm.to_yaml())
