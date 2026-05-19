"""probe command — Autonomous device discovery + registry."""
from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from .probe_display import (
    collect_probe_hosts,
    print_probe_line,
    print_reachable_devices_table,
)


@click.command()
@click.argument("hosts", nargs=-1, required=False)
@click.option(
    "--subnet", default=None,
    help="Scan subnet for new devices first (e.g. 192.168.1.0/24)"
)
@click.option(
    "--user", "users", multiple=True,
    help="SSH user(s) to try (in addition to defaults)"
)
@click.option("--port", "ssh_port", default=22, show_default=True)
@click.option("--app", "app_hint", default="", help="App name hint (stored in registry)")
@click.option(
    "--timeout", default=6, show_default=True,
    help="SSH timeout per attempt (seconds)"
)
@click.option("--no-save", is_flag=True, help="Do not persist results to registry")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def probe(hosts, subnet, users, ssh_port, app_hint, timeout, no_save, as_json):
    """Autonomously probe one or more hosts — detect SSH credentials, strategy, app.

    Tries all available SSH keys (~/.ssh/) and common usernames.
    Detects deployment strategy (docker_full / systemd / podman_quadlet / native_kiosk).
    Saves results to ~/.config/redeploy/devices.yaml automatically.

    \b
    Examples:
        redeploy probe 192.168.188.108
        redeploy probe pi@192.168.188.108
        redeploy probe 192.168.1.10 192.168.1.11
        redeploy probe --subnet 192.168.1.0/24
        redeploy probe --subnet 192.168.188.0/24 && redeploy devices
    """
    import json as _json

    from ...discovery import auto_probe

    console = Console()
    all_ips = collect_probe_hosts(hosts, subnet, console)

    if not all_ips:
        console.print(
            "[yellow]No hosts specified. Use: redeploy probe IP [IP...] or --subnet CIDR[/yellow]"
        )
        return

    extra_users = list(users) if users else []
    results: list = []

    console.print(
        f"[bold]probe[/bold]  {len(all_ips)} host(s)  "
        f"(keys: {Path.home() / '.ssh'}  timeout: {timeout}s)"
    )

    for ip in all_ips:
        result = auto_probe(
            ip,
            users=extra_users or None,
            port=ssh_port,
            timeout=timeout,
            app_hint=app_hint,
            save=not no_save,
        )
        print_probe_line(console, ip, result)
        results.append(result)

    ok = [r for r in results if r.reachable]
    console.print(f"\n  {len(ok)}/{len(results)} reachable")

    if as_json:
        import dataclasses
        print(_json.dumps([dataclasses.asdict(r) for r in results], indent=2, default=str))
        return

    if ok and not no_save:
        print_reachable_devices_table(console, results)
