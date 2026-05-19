"""Rich table rendering for `redeploy devices`."""
from __future__ import annotations

from rich.console import Console
from rich.table import Table

from ...models import DeviceRegistry, KnownDevice


def filter_devices(
    devices: list[KnownDevice],
    *,
    tag: str | None,
    strategy: str | None,
    rpi: bool,
    reachable: bool,
) -> list[KnownDevice]:
    result = devices
    if tag:
        result = [d for d in result if tag in d.tags]
    if strategy:
        result = [d for d in result if d.strategy == strategy]
    if rpi:
        result = [d for d in result if "raspberry-pi" in d.tags]
    if reachable:
        result = [d for d in result if d.is_reachable]
    return result


def render_devices_table(console: Console, devices: list[KnownDevice]) -> None:
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("ID", style="bold")
    table.add_column("Host")
    table.add_column("Strategy", style="cyan")
    table.add_column("App")
    table.add_column("Tags", style="dim")
    table.add_column("Last seen", style="dim")
    table.add_column("SSH", style="dim")

    for device in devices:
        seen = device.last_seen.strftime("%m-%d %H:%M") if device.last_seen else "never"
        ssh = "[green]✓[/green]" if device.last_ssh_ok else "[red]✗[/red]"
        tags_str = ",".join(device.tags) or "—"
        if "raspberry-pi" in device.tags:
            tags_str = tags_str.replace(
                "raspberry-pi", "[bold magenta]raspberry-pi[/bold magenta]",
            )
        table.add_row(
            device.id,
            device.host,
            device.strategy,
            device.app or "—",
            tags_str,
            seen,
            ssh,
        )

    console.print(table)
    console.print(
        f"\n  [dim]{len(devices)} device(s)  •  registry: {DeviceRegistry.default_path()}[/dim]"
    )
