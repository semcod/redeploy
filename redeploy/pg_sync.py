"""PostgreSQL table-level data sync — hash, diff and selectively transfer.

Ported into the package from project shell scripts (c2004
``scripts/redeploy/db-table-hashes.sh`` + ``sync-db-tables.sh``).

Answers, at the shell level, "which tables differ between two hosts and is a
data migration needed?", then moves ONLY the differing tables instead of a
full dump+restore.

Design
------
* Per-table content hash = md5 over per-row ``md5(row::text)`` aggregated
  ``ORDER BY`` the row-md5 — independent of physical row order, needs no
  primary-key knowledge.
* One ``UNION ALL`` query per database (not per table) — a full fleet diff of
  ~200 tables over ssh completes in seconds.
* Transfers are whitelist-guarded: configuration-like tables flow freely,
  operational/telemetry tables require ``force``.
"""
from __future__ import annotations

import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

DEFAULT_EXCLUDE_TABLES = r"^alembic_version$"


@dataclass(frozen=True)
class PgEndpoint:
    """Where a postgres lives: local container or a remote one behind ssh."""

    container: str
    user: str
    ssh_host: str | None = None       # None → local
    engine: str | None = None         # docker|podman; default: docker local, podman remote

    @property
    def runtime(self) -> str:
        return self.engine or ("podman" if self.ssh_host else "docker")

    def psql(self, database: str, sql: str, *, timeout: int = 120) -> str:
        cmd = [self.runtime, "exec", self.container,
               "psql", "-U", self.user, "-d", database, "-tA", "-c", sql]
        if self.ssh_host:
            remote = " ".join(_sq(c) for c in cmd)
            cmd = ["ssh", self.ssh_host, remote]
        return subprocess.check_output(cmd, text=True, timeout=timeout)

    def psql_stdin(self, database: str, script: str, *, timeout: int = 600) -> None:
        cmd = [self.runtime, "exec", "-i", self.container,
               "psql", "-U", self.user, "-d", database, "-v", "ON_ERROR_STOP=1", "-q"]
        if self.ssh_host:
            remote = " ".join(_sq(c) for c in cmd)
            cmd = ["ssh", self.ssh_host, remote]
        subprocess.run(cmd, input=script, text=True, timeout=timeout, check=True)


def _sq(text: str) -> str:
    return "'" + text.replace("'", "'\\''") + "'"


# ── hashing ───────────────────────────────────────────────────────────────────

def list_databases(ep: PgEndpoint, *, like: str = "%", exclude: tuple[str, ...] = ()) -> list[str]:
    rows = ep.psql(
        "postgres",
        f"SELECT datname FROM pg_database WHERE datname LIKE '{like}' ORDER BY 1;",
    ).splitlines()
    return [r for r in rows if r and r not in exclude]


def list_tables(ep: PgEndpoint, database: str, *, exclude_re: str = DEFAULT_EXCLUDE_TABLES) -> list[str]:
    rows = ep.psql(
        database,
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1;",
    ).splitlines()
    pat = re.compile(exclude_re)
    return [r for r in rows if r and not pat.search(r)]


def _hash_query(database: str, tables: list[str]) -> str:
    parts = [
        (
            f"SELECT '{database}.{tab}' || E'\\t' || count(*) || E'\\t' || "
            f"coalesce(md5(string_agg(h, '' ORDER BY h)), 'empty') "
            f"FROM (SELECT md5(t::text) AS h FROM \"{tab}\" t) s"
        )
        for tab in tables
    ]
    return " UNION ALL ".join(parts) + ";"


def table_hashes(
    ep: PgEndpoint,
    *,
    db_like: str = "%",
    db_exclude: tuple[str, ...] = (),
    table_exclude_re: str = DEFAULT_EXCLUDE_TABLES,
) -> dict[str, tuple[int, str]]:
    """``{"db.table": (row_count, content_hash)}`` for every matching table."""
    result: dict[str, tuple[int, str]] = {}
    for db in list_databases(ep, like=db_like, exclude=db_exclude):
        tables = list_tables(ep, db, exclude_re=table_exclude_re)
        if not tables:
            continue
        for line in ep.psql(db, _hash_query(db, tables)).splitlines():
            if not line.strip():
                continue
            key, rows, digest = line.split("\t")
            result[key] = (int(rows), digest)
    return result


@dataclass
class TableDiff:
    differs: list[str]
    only_left: list[str]
    only_right: list[str]
    same: list[str]

    @property
    def clean(self) -> bool:
        return not (self.differs or self.only_left or self.only_right)


def diff_hashes(left: dict[str, tuple[int, str]], right: dict[str, tuple[int, str]]) -> TableDiff:
    keys = sorted(set(left) | set(right))
    d = TableDiff([], [], [], [])
    for key in keys:
        if key not in left:
            d.only_right.append(key)
        elif key not in right:
            d.only_left.append(key)
        elif left[key][1] != right[key][1]:
            d.differs.append(key)
        else:
            d.same.append(key)
    return d


# ── selective transfer ────────────────────────────────────────────────────────

def sync_tables(
    source: PgEndpoint,
    target: PgEndpoint,
    tables: list[str],
    *,
    block_re: str | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    """Copy ``db.table`` entries from *source* to *target* (TRUNCATE+INSERT
    in one transaction per database). Returns inserted row counts per db.

    ``block_re`` marks operational tables that must not be overwritten
    without ``force`` (raises ``PermissionError``).
    """
    if block_re and not force:
        pat = re.compile(block_re)
        blocked = [t for t in tables if pat.search(t)]
        if blocked:
            raise PermissionError(f"operational tables need force=True: {', '.join(blocked)}")

    by_db: dict[str, list[str]] = {}
    for entry in tables:
        db, _, tab = entry.partition(".")
        by_db.setdefault(db, []).append(tab)

    if dry_run:
        return {db: 0 for db in by_db}

    def _dump(db: str) -> tuple[str, str]:
        cmd = [source.runtime, "exec", source.container,
               "pg_dump", "-U", source.user, "-d", db, "--data-only", "--column-inserts"]
        for tab in by_db[db]:
            cmd += ["-t", tab]
        if source.ssh_host:
            cmd = ["ssh", source.ssh_host, " ".join(_sq(c) for c in cmd)]
        return db, subprocess.check_output(cmd, text=True, timeout=900)

    inserted: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=max(1, len(by_db))) as pool:
        dumps = dict(pool.map(_dump, by_db))

    for db, dump in dumps.items():
        body = "\n".join(
            ln for ln in dump.splitlines()
            if ln and not ln.startswith(("SET ", "SELECT pg_catalog", "--"))
        )
        script = "BEGIN;\n"
        for tab in by_db[db]:
            script += f'TRUNCATE "{tab}" CASCADE;\n'
        script += body + "\nCOMMIT;\n"
        target.psql_stdin(db, script)
        inserted[db] = sum(1 for ln in body.splitlines() if ln.startswith("INSERT"))
    return inserted
