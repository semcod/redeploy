"""hash command group — source-scope hashes for build-skip guards."""
from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console


@click.group("hash")
def hash_cmd():
    """Publish and check source-scope hashes (image build-skip guards)."""


@hash_cmd.command("publish")
@click.option("--root", type=click.Path(exists=True), default=".", show_default=True)
@click.option("--scopes-file", type=click.Path(), default=None,
              help="YAML {scope: [paths]} (default: .redeploy-scopes.yaml).")
@click.option("--out-dir", type=click.Path(), default=None,
              help="Output dir (default: .redeploy-hashes/).")
@click.option("--scope", "only", multiple=True, help="Publish only these scopes.")
def hash_publish(root, scopes_file, out_dir, only):
    """Compute operator-side hashes (git tracked + untracked-not-ignored) and
    write them to files that travel with the project sync."""
    from ...source_hash import publish_hashes

    console = Console()
    published = publish_hashes(Path(root), scopes_file=scopes_file,
                               out_dir=out_dir, only=list(only) or None)
    for name, value in published.items():
        console.print(f"[green]PASS[/green] {name} {value[:12]}")


@hash_cmd.command("check")
@click.argument("scope")
@click.argument("image")
@click.option("--root", type=click.Path(exists=True), default=".", show_default=True)
@click.option("--label", default="c2004.source-hash", show_default=True)
@click.option("--engine", default="podman", show_default=True)
@click.option("--ssh", "ssh_host", default=None, help="Inspect the image on a remote host.")
@click.option("--out-dir", type=click.Path(), default=None)
def hash_check(scope, image, root, label, engine, ssh_host, out_dir):
    """Exit 0 when IMAGE's label matches the published SCOPE hash (skip build).

    A missing or stale (>2 h) published hash exits 1 — the safe direction is
    always "build".
    """
    from ...source_hash import image_current, image_label_hash, read_published_hash

    console = Console()
    published = read_published_hash(Path(root), scope, out_dir=out_dir)
    if not published:
        console.print(f"[yellow]BUILD[/yellow] {image}: no fresh published hash for '{scope}'")
        raise SystemExit(1)
    if image_current(Path(root), scope, image, label=label, engine=engine,
                     ssh_host=ssh_host, out_dir=out_dir):
        console.print(f"[green]SKIP[/green] {image} current ({published[:12]})")
        return
    have = image_label_hash(image, label=label, engine=engine, ssh_host=ssh_host)
    console.print(f"[yellow]BUILD[/yellow] {image}: label={str(have)[:12]} current={published[:12]}")
    raise SystemExit(1)
