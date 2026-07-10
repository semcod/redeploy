"""Live fleet operations — runtime status probes and parallel spec runs.

Complements :mod:`redeploy.fleet` (static inventory/stages) with the runtime
side ported from project shell scripts (c2004 ``fleet-status.sh`` +
``deploy-fleet.sh``): reachability, failing systemd units, HTTP health,
deploy drift (local HEAD vs the target's ``.deploy-commit``) — collected in
parallel — and running several migration specs concurrently with prefixed
output.
"""
from __future__ import annotations

import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from .gitsync import DEPLOY_COMMIT_FILE, _remote_rel, _sq


# ── status model ──────────────────────────────────────────────────────────────

@dataclass
class HttpCheck:
    name: str
    url: str
    timeout: int = 6


@dataclass
class DriftCheck:
    """Compare a local repo's HEAD with ``<remote_dir>/.deploy-commit``."""

    repo: Path
    remote_dir: str
    name: str = ""


@dataclass
class FleetProbe:
    """One device to probe: ssh target + optional http/drift checks."""

    name: str
    ssh_host: str | None = None          # e.g. pi@192.168.188.109; None → http-only
    ping_host: str | None = None         # defaults to ssh host's address
    unit_glob: str | None = None         # e.g. "c2004-*" (systemd --user)
    http: list[HttpCheck] = field(default_factory=list)
    drift: list[DriftCheck] = field(default_factory=list)


@dataclass
class ProbeResult:
    name: str
    online: bool = False
    fields: dict[str, str] = field(default_factory=dict)

    @property
    def healthy(self) -> bool:
        if not self.online:
            return False
        for key, value in self.fields.items():
            if value == "FAIL" or (key == "failed_units" and value not in ("", "none")):
                return False
        return True


def _ping(host: str, timeout: int = 2) -> bool:
    return subprocess.run(
        ["ping", "-c", "1", "-W", str(timeout), host], capture_output=True
    ).returncode == 0


def _http_ok(url: str, timeout: int) -> bool:
    try:
        import urllib.request

        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return 200 <= resp.status < 400
    except Exception:  # noqa: BLE001
        return False


def _failed_units(ssh_host: str, glob: str) -> str:
    proc = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=5", ssh_host,
         f"systemctl --user list-units {_sq(glob)} --state=failed --no-legend --plain"
         " 2>/dev/null | awk '{print $1}'"],
        capture_output=True, text=True,
    )
    names = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    return ",".join(names) if names else "none"


def _drift(check: DriftCheck, ssh_host: str) -> str:
    rel = _remote_rel(check.remote_dir)
    proc = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=5", ssh_host,
         f"cat {_sq(rel)}/{DEPLOY_COMMIT_FILE} 2>/dev/null"],
        capture_output=True, text=True,
    )
    last = proc.stdout.strip()
    if not last:
        return "no-deploy-commit"
    try:
        head = subprocess.check_output(
            ["git", "-C", str(check.repo), "rev-parse", "HEAD"], text=True
        ).strip()
    except subprocess.CalledProcessError:
        return "?"
    if last == head:
        dirty = subprocess.run(
            ["git", "-C", str(check.repo), "status", "--porcelain"],
            capture_output=True, text=True,
        ).stdout.strip()
        return "current+wip" if dirty else "current"
    behind = subprocess.run(
        ["git", "-C", str(check.repo), "rev-list", "--count", f"{last}..HEAD"],
        capture_output=True, text=True,
    ).stdout.strip() or "?"
    return f"behind:{behind}"


def probe_device(probe: FleetProbe) -> ProbeResult:
    result = ProbeResult(name=probe.name)
    ping_target = probe.ping_host or (probe.ssh_host.split("@")[-1] if probe.ssh_host else None)
    if ping_target and not _ping(ping_target):
        result.fields["net"] = "OFFLINE"
        return result
    result.online = True
    result.fields["net"] = "up"

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {}
        for chk in probe.http:
            futures[pool.submit(_http_ok, chk.url, chk.timeout)] = ("http", chk.name)
        if probe.ssh_host and probe.unit_glob:
            futures[pool.submit(_failed_units, probe.ssh_host, probe.unit_glob)] = ("units", "failed_units")
        if probe.ssh_host:
            for drift in probe.drift:
                label = drift.name or f"drift_{Path(drift.repo).name}"
                futures[pool.submit(_drift, drift, probe.ssh_host)] = ("drift", label)
        for fut, (kind, label) in futures.items():
            try:
                value = fut.result()
            except Exception:  # noqa: BLE001
                value = "FAIL"
            if kind == "http":
                result.fields[label] = "ok" if value else "FAIL"
            else:
                result.fields[label] = str(value)
    return result


def fleet_status(probes: list[FleetProbe]) -> list[ProbeResult]:
    """Probe all devices in parallel."""
    with ThreadPoolExecutor(max_workers=max(1, len(probes))) as pool:
        return list(pool.map(probe_device, probes))


# ── parallel spec runs ────────────────────────────────────────────────────────

@dataclass
class FleetJob:
    """One deploy job: run ``redeploy run <spec>`` inside *cwd*."""

    name: str
    cwd: Path
    spec: str
    extra_args: list[str] = field(default_factory=list)


@dataclass
class JobResult:
    name: str
    returncode: int
    duration_s: float
    log_path: Path


def run_jobs(
    jobs: list[FleetJob],
    *,
    parallel: bool = True,
    log_dir: Path | None = None,
    line_callback=None,
) -> list[JobResult]:
    """Run every job (``redeploy run`` subprocess), optionally in parallel.

    ``line_callback(name, line)`` receives live output lines prefixed per job
    (the CLI uses it to interleave progress from all devices).
    """
    log_dir = log_dir or Path("/tmp")
    stamp = time.strftime("%H%M%S")

    def _one(job: FleetJob) -> JobResult:
        log_path = log_dir / f"fleet-{job.name}-{stamp}.log"
        start = time.time()
        with log_path.open("w") as log:
            proc = subprocess.Popen(
                ["redeploy", "run", job.spec, *job.extra_args],
                cwd=str(job.cwd), text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                log.write(line)
                if line_callback:
                    line_callback(job.name, line.rstrip("\n"))
            proc.wait()
        return JobResult(job.name, proc.returncode, time.time() - start, log_path)

    if parallel and len(jobs) > 1:
        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            return list(pool.map(_one, jobs))
    return [_one(job) for job in jobs]
