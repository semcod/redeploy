"""Source-scope hashing for build-skip guards.

Ported into the package from project shell scripts (c2004
``compute-source-hash.sh`` + ``publish-source-hashes.sh`` +
``skip-if-image-current.sh``).

Problem this solves
-------------------
Image builds on a target device are skipped when the image label
``<prefix>.source-hash`` matches the current source hash. Computing the hash
ON the device is unreliable (stale ``.git``, different file sets), so the
OPERATOR machine computes it (git: tracked + untracked-not-ignored — exactly
what rsync ships) and publishes it as files that travel with the sync. The
device build script reads the published file; a stale file (older than
``max_age``) is ignored so the failure mode is always "build", never a wrong
"skip".

Scopes come from a YAML mapping ``{scope_name: [path, ...]}`` (conventionally
``.redeploy-scopes.yaml`` in the project root).
"""
from __future__ import annotations

import hashlib
import subprocess
import time
from pathlib import Path

import yaml

DEFAULT_SCOPES_FILE = ".redeploy-scopes.yaml"
DEFAULT_OUT_DIR = ".redeploy-hashes"
DEFAULT_MAX_AGE_S = 2 * 3600


def load_scopes(root: Path, scopes_file: str | Path | None = None) -> dict[str, list[str]]:
    path = Path(scopes_file) if scopes_file else Path(root) / DEFAULT_SCOPES_FILE
    if not path.is_absolute():
        path = Path(root) / path
    data = yaml.safe_load(path.read_text()) or {}
    scopes = data.get("scopes", data)
    if not isinstance(scopes, dict):
        raise ValueError(f"{path}: expected mapping of scope -> [paths]")
    return {str(k): [str(p) for p in v] for k, v in scopes.items()}


def compute_scope_hash(root: Path, paths: list[str]) -> str:
    """sha256 over (sha256 of each file) — tracked + untracked-not-ignored,
    matching the payload rsync actually ships."""
    root = Path(root).resolve()
    listed = subprocess.check_output(
        ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others",
         "--exclude-standard", "--", *paths],
        text=False,
    ).split(b"\0")
    digest = hashlib.sha256()
    count = 0
    for rel in sorted({p.decode() for p in listed if p}):
        fp = root / rel
        if not fp.is_file():
            continue
        file_digest = hashlib.sha256()
        with fp.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                file_digest.update(chunk)
        digest.update(file_digest.hexdigest().encode())
        digest.update(b"  ")
        digest.update(rel.encode())
        digest.update(b"\n")
        count += 1
    if count == 0:
        raise ValueError(f"empty source hash for paths: {paths}")
    return digest.hexdigest()


def publish_hashes(
    root: Path,
    *,
    scopes_file: str | Path | None = None,
    out_dir: str | Path | None = None,
    only: list[str] | None = None,
) -> dict[str, str]:
    """Compute and write ``<out_dir>/<scope>`` hash files. Returns the hashes."""
    root = Path(root).resolve()
    scopes = load_scopes(root, scopes_file)
    if only:
        scopes = {k: v for k, v in scopes.items() if k in only}
    out = Path(out_dir) if out_dir else root / DEFAULT_OUT_DIR
    if not out.is_absolute():
        out = root / out
    out.mkdir(parents=True, exist_ok=True)
    published: dict[str, str] = {}
    for name, paths in scopes.items():
        value = compute_scope_hash(root, paths)
        (out / name).write_text(value + "\n")
        published[name] = value
    return published


def read_published_hash(
    root: Path,
    scope: str,
    *,
    out_dir: str | Path | None = None,
    max_age_s: int = DEFAULT_MAX_AGE_S,
) -> str | None:
    """Return the published hash for *scope*, or None when missing/stale.

    Staleness forces a build (safe direction) — a stale hash could otherwise
    wrongly skip a needed build.
    """
    out = Path(out_dir) if out_dir else Path(root) / DEFAULT_OUT_DIR
    if not out.is_absolute():
        out = Path(root) / out
    fp = out / scope
    try:
        stat = fp.stat()
    except FileNotFoundError:
        return None
    if max_age_s and (time.time() - stat.st_mtime) > max_age_s:
        return None
    value = fp.read_text().strip().splitlines()
    return value[0] if value else None


def image_label_hash(
    image: str,
    *,
    label: str = "c2004.source-hash",
    engine: str = "podman",
    ssh_host: str | None = None,
) -> str | None:
    """Read ``label`` from a (possibly remote) container image."""
    cmd = [engine, "inspect", image, "--format", f'{{{{ index .Config.Labels "{label}" }}}}']
    if ssh_host:
        quoted = " ".join("'" + c.replace("'", "'\\''") + "'" for c in cmd)
        cmd = ["ssh", ssh_host, quoted]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    value = proc.stdout.strip()
    return value if proc.returncode == 0 and value and value != "<no value>" else None


def image_current(
    root: Path,
    scope: str,
    image: str,
    *,
    label: str = "c2004.source-hash",
    engine: str = "podman",
    ssh_host: str | None = None,
    out_dir: str | Path | None = None,
) -> bool:
    """True when the image label matches the published (fresh) scope hash."""
    published = read_published_hash(root, scope, out_dir=out_dir)
    if not published:
        return False
    return image_label_hash(image, label=label, engine=engine, ssh_host=ssh_host) == published
