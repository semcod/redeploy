"""Console output helpers for `redeploy probe`."""
from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from ...discovery import ProbeResult, discover
from ...models import DeviceRegistry


def collect_probe_hosts(
    hosts: tuple[str, ...],
    subnet: str | None,
    console: Console,
) -> list[str]:
    all_ips = list(hosts)
    if not subnet:
        return all_ips

    console.print(f"[bold]scan[/bold]  {subnet}  (ARP+ping sweep)...")
    found = discover(subnet=subnet, ping=True, mdns=False, probe_ssh=False, timeout=3)
    new_ips = [h.ip for h in found if h.ip not in all_ips]
    if new_ips:
        console.print(
            f"  found {len(new_ips)} host(s) on {subnet}: "
            + ", ".join(new_ips[:6]) + ("…" if len(new_ips) > 6 else "")
        )
        all_ips.extend(new_ips)
    return all_ips


def print_probe_line(console: Console, ip: str, result: ProbeResult) -> None:
    label = ip if "@" in ip else f"[dim]{ip}[/dim]"
    console.print(f"  → {label}", end="  ")
    if not result.reachable:
        console.print(f"[red]✗[/red]  {result.error}")
        return
    key_label = Path(result.ssh_key).name if result.ssh_key else "agent"
    console.print(
        f"[green]✓[/green] {result.ssh_user}  "
        f"[dim]{key_label}[/dim]  "
        f"[cyan]{result.strategy}[/cyan]"
        + (f"  app={result.app}" if result.app else "")
        + (f"  arch={result.arch}" if result.arch else "")
    )


def print_reachable_devices_table(console: Console, results: list[ProbeResult]) -> None:
    ok = [r for r in results if r.reachable]
    if not ok:
        return

    console.print(
        f"  [dim]registry updated → {Path.home() / '.config/redeploy/devices.yaml'}[/dim]"
    )
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("ID", style="bold")
    table.add_column("Strategy", style="cyan")
    table.add_column("App")
    table.add_column("Arch", style="dim")
    table.add_column("OS", style="dim")
    table.add_column("Key", style="dim")
    for result in ok:
        key_label = Path(result.ssh_key).name if result.ssh_key else "agent"
        table.add_row(
            result.host,
            result.strategy,
            result.app or "—",
            result.arch or "—",
            result.os_info[:30] if result.os_info else "—",
            key_label,
        )
    console.print()
    console.print(table)
    console.print(f"\n  Use [bold]redeploy target {ok[0].host}[/bold] to deploy.")
