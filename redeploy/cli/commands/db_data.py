"""db command group — postgres table hashes, diff and selective sync."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table


def _endpoint(target: str | None, container: str, user: str, engine: str | None):
    from ...pg_sync import PgEndpoint

    return PgEndpoint(container=container, user=user, ssh_host=target or None, engine=engine)


_common = [
    click.option("--container", default="c2004-postgres", show_default=True),
    click.option("--user", "pguser", default="c2004", show_default=True),
    click.option("--db-like", default="%", show_default=True,
                 help="SQL LIKE filter for database names."),
    click.option("--db-exclude", multiple=True, help="Database names to skip."),
]


def _apply(options):
    def wrap(fn):
        for opt in reversed(options):
            fn = opt(fn)
        return fn
    return wrap


@click.group("db")
def db_cmd():
    """Postgres data tools: hash, diff and selectively sync tables."""


@db_cmd.command("hash")
@click.option("--target", help="ssh host for a remote postgres (default: local).")
@click.option("--engine", help="docker|podman (default: docker local, podman remote).")
@_apply(_common)
def db_hash(target, engine, container, pguser, db_like, db_exclude):
    """Print ``db.table  rows  content-hash`` for every table."""
    from ...pg_sync import table_hashes

    ep = _endpoint(target, container, pguser, engine)
    for key, (rows, digest) in sorted(table_hashes(
        ep, db_like=db_like, db_exclude=tuple(db_exclude)
    ).items()):
        click.echo(f"{key}\t{rows}\t{digest}")


@db_cmd.command("diff")
@click.argument("target")
@click.option("--engine-local", default=None)
@click.option("--engine-remote", default=None)
@click.option("--verbose", is_flag=True, help="Also list identical tables.")
@_apply(_common)
def db_diff(target, engine_local, engine_remote, verbose, container, pguser, db_like, db_exclude):
    """Compare local vs TARGET table hashes. Exit 1 when data differs.

    \b
    Example:
        redeploy db diff pi@192.168.188.109 --db-like 'c2004%' --db-exclude c2004_logs
    """
    from concurrent.futures import ThreadPoolExecutor

    from ...pg_sync import diff_hashes, table_hashes

    console = Console()
    left_ep = _endpoint(None, container, pguser, engine_local)
    right_ep = _endpoint(target, container, pguser, engine_remote)
    kwargs = dict(db_like=db_like, db_exclude=tuple(db_exclude))
    with ThreadPoolExecutor(max_workers=2) as pool:
        left_f = pool.submit(table_hashes, left_ep, **kwargs)
        right_f = pool.submit(table_hashes, right_ep, **kwargs)
        left, right = left_f.result(), right_f.result()

    diff = diff_hashes(left, right)
    table = Table("table", "local", "remote", "status")
    for key in diff.differs:
        table.add_row(key, f"{left[key][0]}/{left[key][1][:8]}",
                      f"{right[key][0]}/{right[key][1][:8]}", "[red]DIFFERS[/red]")
    for key in diff.only_left:
        table.add_row(key, str(left[key][0]), "-", "[yellow]ONLY-LOCAL[/yellow]")
    for key in diff.only_right:
        table.add_row(key, "-", str(right[key][0]), "[yellow]ONLY-REMOTE[/yellow]")
    if verbose:
        for key in diff.same:
            table.add_row(key, f"{left[key][0]}", f"{right[key][0]}", "[green]ok[/green]")
    console.print(table)
    console.print(
        f"same={len(diff.same)} differs={len(diff.differs)} "
        f"only-local={len(diff.only_left)} only-remote={len(diff.only_right)}"
    )
    if not diff.clean:
        raise SystemExit(1)


@db_cmd.command("sync")
@click.argument("target")
@click.option("--tables", help="Comma-separated db.table list (default: auto-detect differing).")
@click.option("--allow-re", default=None,
              help="Whitelist regex — auto-detected tables outside it are skipped.")
@click.option("--block-re", default=r"\.(logs|events|protocols|devices|auth_users)",
              show_default=True, help="Operational tables refused without --force.")
@click.option("--force", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--engine-local", default=None)
@click.option("--engine-remote", default=None)
@_apply(_common)
def db_sync(target, tables, allow_re, block_re, force, dry_run,
            engine_local, engine_remote, container, pguser, db_like, db_exclude):
    """Copy ONLY differing tables local → TARGET (TRUNCATE+INSERT, transactional).

    \b
    Examples:
        redeploy db sync pi@host --dry-run
        redeploy db sync pi@host --tables app_scn.hardware_mapping_store
        redeploy db sync pi@host --tables app.protocols --force
    """
    import re

    from ...pg_sync import diff_hashes, sync_tables, table_hashes

    console = Console()
    left_ep = _endpoint(None, container, pguser, engine_local)
    right_ep = _endpoint(target, container, pguser, engine_remote)

    if tables:
        selected = [t.strip() for t in tables.split(",") if t.strip()]
    else:
        console.print("[dim]auto-detecting differing tables…[/dim]")
        kwargs = dict(db_like=db_like, db_exclude=tuple(db_exclude))
        diff = diff_hashes(table_hashes(left_ep, **kwargs), table_hashes(right_ep, **kwargs))
        selected = diff.differs
        if allow_re:
            pat = re.compile(allow_re)
            skipped = [t for t in selected if not pat.search(t)]
            selected = [t for t in selected if pat.search(t)]
            if skipped:
                console.print(f"[dim]outside allow-re, skipped: {', '.join(skipped)}[/dim]")

    if not selected:
        console.print("[green]nothing to sync[/green]")
        return

    console.print(f"tables ({len(selected)}): {', '.join(selected)}")
    try:
        inserted = sync_tables(left_ep, right_ep, selected,
                               block_re=block_re, force=force, dry_run=dry_run)
    except PermissionError as exc:
        console.print(f"[red]REFUSED:[/red] {exc}")
        raise SystemExit(3) from exc
    if dry_run:
        console.print("[yellow]dry-run — no transfer[/yellow]")
        return
    for db, rows in inserted.items():
        console.print(f"[green]PASS[/green] {db}: {rows} row(s)")
