"""device-map command — Generate a full standardized device snapshot."""
from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from .device_map_actions import (
    emit_device_map,
    execute_query_device_map,
    print_device_map_diff,
    print_saved_maps,
    probe_device_map,
)


@click.command("device-map")
@click.argument("host", required=False, default=None)
@click.option("--name", default="", help="Human-friendly device label")
@click.option("--tag", "tags", multiple=True, help="Tag(s) to attach (repeatable)")
@click.option("--save", is_flag=True, help="Persist map to ~/.config/redeploy/device-maps/")
@click.option("--out", "out_path", default=None, type=click.Path(), help="Save to specific file")
@click.option("--format", "output_fmt", default="yaml", type=click.Choice(["yaml", "json"]))
@click.option("--no-infra", is_flag=True, help="Skip infra probe (faster — hardware only)")
@click.option("--list", "list_saved", is_flag=True, help="List saved device maps")
@click.option("--show", "show_file", default=None, type=click.Path(exists=True), help="Load and display a saved device-map file")
@click.option("--diff", "diff_files", nargs=2, type=click.Path(exists=True), help="Diff two saved device-map files")
@click.option("--apply-config", "apply_config", default=None, type=click.Path(exists=True, dir_okay=False))
@click.option("--query", "query_expr", default=None, metavar="EXPR", help="JMESPath query on the device map")
@click.option("--ssh-key", default=None, type=click.Path(), help="SSH private key path")
def device_map_cmd(
    host, name, tags, save, out_path, output_fmt,
    no_infra, list_saved, show_file, diff_files, ssh_key, apply_config, query_expr,
):
    """Generate a full standardized device snapshot (hardware + infra + diagnostics)."""
    from ...models import DeviceMap

    console = Console()

    if list_saved:
        print_saved_maps(console)
        return

    if show_file:
        click.echo(DeviceMap.load(Path(show_file)).to_yaml())
        return

    if diff_files:
        print_device_map_diff(console, Path(diff_files[0]), Path(diff_files[1]))
        return

    if not host:
        console.print("[red]✗ HOST required (or use --list / --show / --diff)[/red]")
        sys.exit(1)

    if apply_config:
        from ...config_apply import apply_config_file
        apply_config_file(apply_config, ssh_key=ssh_key, console=console)
        return

    device_map = probe_device_map(
        console, host, name=name, tags=tags, ssh_key=ssh_key, no_infra=no_infra,
    )

    if query_expr:
        execute_query_device_map(console, device_map, query_expr, output_fmt)
        return

    emit_device_map(device_map, output_fmt)

    if save or out_path:
        saved_path = device_map.save(Path(out_path) if out_path else None)
        console.print(f"\n[green]✓ saved:[/green] {saved_path}")

    if device_map.has_errors:
        sys.exit(1)
