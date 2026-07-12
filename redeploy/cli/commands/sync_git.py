"""sync command — incremental git-diff sync to a remote target."""
from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console


@click.command("sync")
@click.argument("remote", metavar="HOST:DIR")
@click.option("--repo", "repos", multiple=True, type=click.Path(exists=True),
              help="Repo root (repeatable; default: cwd). With multiple repos "
                   "use --repo PATH=HOST:DIR entries instead of REMOTE.")
@click.option("--parallel", default=4, show_default=True,
              help="Parallel rsync streams per repo.")
@click.option("--dry-run", is_flag=True, help="List the delta without transferring.")
@click.option("--record", is_flag=True,
              help="After a successful sync stamp the shipped commit as .deploy-commit.")
@click.option("--frozen", is_flag=True,
              help="Frozen mode: delta AND contents come from HEAD only "
                   "(git archive) — working-tree edits/WIP never ship.")
def sync_cmd(remote, repos, parallel, dry_run, record, frozen):
    """Ship only files changed since the target's ``.deploy-commit``.

    Tracked modifications + untracked-not-ignored files rsync in PARALLEL
    streams; deletions apply in one ssh call. Exits 3 when the incremental
    path is unavailable (no/unknown .deploy-commit) so callers can fall back
    to a full sync.

    With ``--frozen`` the delta is ``base..HEAD`` only and file contents ship
    from HEAD via ``git archive`` — parallel edits during the sync cannot
    reach the target.

    \b
    Examples:
        redeploy sync pi@192.168.188.109:~/c2004
        redeploy sync pi@host:~/app --parallel 8 --record
        redeploy sync pi@host:~/app --frozen --record
        redeploy sync pi@host:~/app --dry-run
    """
    import subprocess

    from ...gitsync import (
        GitSyncError,
        frozen_sync,
        incremental_sync,
        record_deploy_commit,
    )

    console = Console()
    host, _, remote_dir = remote.partition(":")
    if not remote_dir:
        raise click.UsageError("REMOTE must be HOST:DIR, e.g. pi@host:~/app")

    roots = [Path(r) for r in repos] or [Path.cwd()]
    failed = False
    for root in roots:
        label = root.resolve().name
        shipped_commit = None
        try:
            if frozen:
                # Capture the shipped commit BEFORE syncing — commits made
                # during the sync must not be stamped as deployed.
                shipped_commit = subprocess.check_output(
                    ["git", "-C", str(root.resolve()), "rev-parse", "HEAD"], text=True
                ).strip()
                console.print(
                    f"[bold]{label}[/bold]: FROZEN — shipping commit "
                    f"[cyan]{shipped_commit[:12]}[/cyan] (working tree ignored)"
                )
                delta = frozen_sync(root, host, remote_dir, dry_run=dry_run)
            else:
                delta = incremental_sync(
                    root, host, remote_dir, parallel=parallel, dry_run=dry_run
                )
        except GitSyncError as exc:
            console.print(f"[yellow]{label}: {exc}[/yellow]")
            failed = True
            continue
        action = "would sync" if dry_run else "synced"
        console.print(
            f"[green]{label}[/green]: {action} {len(delta.sync)} file(s), "
            f"{len(delta.delete)} delete(s)"
        )
        if dry_run and delta.sync:
            for path in delta.sync[:20]:
                console.print(f"  [dim]{path}[/dim]")
        if record and not dry_run:
            head = record_deploy_commit(root, host, remote_dir, commit=shipped_commit)
            console.print(f"  [dim].deploy-commit → {head[:12]}[/dim]")

    if failed:
        raise SystemExit(3)
