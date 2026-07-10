"""Incremental git-diff sync — ship only files changed since the last deploy.

Ported into the package from project shell scripts (c2004
``scripts/redeploy/sync-git-diff-repo.sh`` + ``git-diff-deploy-files.py`` +
``record-deploy-commit.sh``).

Flow
----
1. The target keeps a ``.deploy-commit`` file (git HEAD recorded after the
   last successful deploy) inside the remote project dir.
2. :func:`collect_delta` lists deployable changes since that commit:
   tracked modifications + untracked-but-not-ignored files, and deletions.
3. :func:`incremental_sync` rsyncs the delta with ``--files-from`` split into
   N parallel streams, and applies deletions in a single ssh call.
4. :func:`record_deploy_commit` stamps the new HEAD after a successful deploy.

All helpers are project-agnostic: any git repo, any ``host:dir`` target.
"""
from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

DEPLOY_COMMIT_FILE = ".deploy-commit"


class GitSyncError(RuntimeError):
    """Incremental sync cannot proceed (caller should fall back to full sync)."""


# ── remote path handling ──────────────────────────────────────────────────────

def _remote_rel(remote_dir: str) -> str:
    """Normalise ``~/x`` → ``x`` (relative to $HOME on the remote).

    Quoting a tilde (``printf %q`` / ``shlex.quote``) makes the remote shell
    treat it literally and create a directory named ``~`` — a real production
    bug this port fixes by never quoting a tilde.
    """
    if remote_dir.startswith("~/"):
        return remote_dir[2:]
    return remote_dir


def _sq(text: str) -> str:
    """POSIX single-quote (safe for ssh command strings)."""
    return "'" + text.replace("'", "'\\''") + "'"


# ── git delta ─────────────────────────────────────────────────────────────────

def _git_lines(root: Path, *args: str) -> list[str]:
    out = subprocess.check_output(["git", "-C", str(root), *args], text=True)
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def _ignored_subset(root: Path, paths: list[str]) -> set[str]:
    """Batch ``git check-ignore --stdin`` (one process for all paths)."""
    if not paths:
        return set()
    proc = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--stdin"],
        input="\n".join(paths), capture_output=True, text=True,
    )
    return {ln.strip() for ln in proc.stdout.splitlines() if ln.strip()}


@dataclass
class Delta:
    sync: list[str] = field(default_factory=list)
    delete: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not self.sync and not self.delete


def collect_delta(root: Path, base_commit: str) -> Delta:
    """Deployable delta since *base_commit* (paths relative to repo root)."""
    root = root.resolve()
    changed = _git_lines(root, "diff", "--name-only", base_commit)
    deleted = _git_lines(root, "diff", "--name-only", "--diff-filter=D", base_commit)
    untracked = _git_lines(root, "ls-files", "--others", "--exclude-standard")

    candidates = [p for p in dict.fromkeys(changed + untracked) if p not in set(deleted)]
    ignored = _ignored_subset(root, candidates + deleted)

    delta = Delta()
    for rel in candidates:
        if rel in ignored or not (root / rel).is_file():
            continue
        delta.sync.append(rel)
    for rel in dict.fromkeys(deleted):
        if rel not in ignored:
            delta.delete.append(rel)
    return delta


# ── remote deploy-commit ──────────────────────────────────────────────────────

def read_deploy_commit(host: str, remote_dir: str, *, timeout: int = 8) -> str | None:
    rel = _remote_rel(remote_dir)
    proc = subprocess.run(
        ["ssh", "-o", f"ConnectTimeout={timeout}", host,
         f"cat {_sq(rel)}/{DEPLOY_COMMIT_FILE} 2>/dev/null"],
        capture_output=True, text=True,
    )
    value = proc.stdout.strip()
    return value or None


def record_deploy_commit(root: Path, host: str, remote_dir: str, *, timeout: int = 8) -> str:
    """Stamp current HEAD into ``<remote_dir>/.deploy-commit``. Returns the sha."""
    head = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    rel = _remote_rel(remote_dir)
    subprocess.run(
        ["ssh", "-o", f"ConnectTimeout={timeout}", host,
         f"mkdir -p {_sq(rel)} && printf '%s\\n' {_sq(head)} > {_sq(rel)}/{DEPLOY_COMMIT_FILE}"],
        check=True,
    )
    return head


# ── sync ──────────────────────────────────────────────────────────────────────

def _rsync_stream(root: Path, host: str, remote_dir: str, files: list[str]) -> None:
    proc = subprocess.run(
        ["rsync", "-az", "--files-from=-", f"{root}/", f"{host}:{remote_dir}/"],
        input="\n".join(files) + "\n", text=True,
    )
    if proc.returncode != 0:
        raise GitSyncError(f"rsync stream failed (exit {proc.returncode})")


def _apply_deletes(host: str, remote_dir: str, paths: list[str]) -> None:
    """All deletions in ONE ssh call (was one ssh per file in the shell version)."""
    rel = _remote_rel(remote_dir)
    script = "\n".join(f"rm -f -- {_sq(p)}" for p in paths)
    subprocess.run(
        ["ssh", host, f"cd {_sq(rel)} && sh -s"],
        input=script + "\n", text=True, check=True,
    )


def incremental_sync(
    root: Path,
    host: str,
    remote_dir: str,
    *,
    parallel: int = 4,
    dry_run: bool = False,
    base_commit: str | None = None,
) -> Delta:
    """Sync the delta since the target's ``.deploy-commit`` to ``host:remote_dir``.

    Raises :class:`GitSyncError` when the incremental path is unavailable
    (no ``.deploy-commit`` on the target, unknown base commit) — the caller
    should fall back to a full sync.
    """
    root = Path(root).resolve()
    base = base_commit or read_deploy_commit(host, remote_dir)
    if not base:
        raise GitSyncError(f"no {DEPLOY_COMMIT_FILE} on {host}:{remote_dir} — full sync required")
    probe = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{base}^{{commit}}"],
        capture_output=True,
    )
    if probe.returncode != 0:
        raise GitSyncError(f"unknown base commit {base[:12]} — full sync required")

    delta = collect_delta(root, base)
    if dry_run or delta.empty:
        return delta

    if delta.sync:
        streams = max(1, min(parallel, len(delta.sync)))
        chunks = [delta.sync[i::streams] for i in range(streams)]
        with ThreadPoolExecutor(max_workers=streams) as pool:
            futures = [
                pool.submit(_rsync_stream, root, host, remote_dir, chunk)
                for chunk in chunks if chunk
            ]
            for fut in futures:
                fut.result()

    if delta.delete:
        _apply_deletes(host, remote_dir, delta.delete)

    return delta


def multi_repo_sync(
    repos: list[tuple[Path, str, str]],
    *,
    parallel_streams: int = 4,
    dry_run: bool = False,
) -> dict[str, Delta | Exception]:
    """Sync many ``(root, host, remote_dir)`` repos CONCURRENTLY.

    Returns per-repo Delta or the raised exception (callers decide which
    repos are required vs best-effort).
    """
    results: dict[str, Delta | Exception] = {}

    def _one(entry: tuple[Path, str, str]):
        root, host, remote_dir = entry
        label = f"{Path(root).name}->{host}:{remote_dir}"
        try:
            results[label] = incremental_sync(
                Path(root), host, remote_dir,
                parallel=parallel_streams, dry_run=dry_run,
            )
        except Exception as exc:  # noqa: BLE001 — collected for the caller
            results[label] = exc

    with ThreadPoolExecutor(max_workers=max(1, len(repos))) as pool:
        list(pool.map(_one, repos))
    return results
