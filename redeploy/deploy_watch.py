"""Host-side deploy cockpit — change gate, live progress, timing history.

Gives the operator control over three things before and during an update:

* **changes** — a pre-deploy manifest: HEAD, uncommitted WIP, the exact file
  delta that will reach the target (vs its ``.deploy-commit``);
* **time** — per-step durations recorded to ``~/.config/redeploy/step-times/``
  and used to predict the next run (ETA, Δ vs previous run);
* **progress** — a live ``step N/M`` display fed by the engine's
  ``--progress-yaml`` event stream.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

HISTORY_DIR = Path.home() / ".config" / "redeploy" / "step-times"
HISTORY_KEEP = 5


# ── timing history ────────────────────────────────────────────────────────────

def _history_key(spec: str, cwd: Path) -> str:
    raw = f"{Path(cwd).resolve()}::{spec}"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("_")[-120:]


@dataclass
class StepHistory:
    path: Path
    steps: dict[str, list[float]] = field(default_factory=dict)
    totals: list[float] = field(default_factory=list)

    @classmethod
    def load(cls, spec: str, cwd: Path) -> "StepHistory":
        path = HISTORY_DIR / f"{_history_key(spec, cwd)}.json"
        steps: dict[str, list[float]] = {}
        totals: list[float] = []
        if path.exists():
            try:
                data = json.loads(path.read_text())
                steps = {k: list(map(float, v)) for k, v in data.get("steps", {}).items()}
                totals = list(map(float, data.get("totals", [])))
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        return cls(path=path, steps=steps, totals=totals)

    def estimate(self, step_id: str) -> float | None:
        values = self.steps.get(step_id)
        if not values:
            return None
        ordered = sorted(values)
        return ordered[len(ordered) // 2]  # median

    def eta_for(self, remaining_ids: list[str]) -> float | None:
        known = [self.estimate(sid) for sid in remaining_ids]
        known = [v for v in known if v is not None]
        if not known:
            return None
        # Steps without history count as the median of the known ones.
        fill = sorted(known)[len(known) // 2]
        return sum(known) + fill * (len(remaining_ids) - len(known))

    def record(self, step_id: str, duration: float) -> None:
        self.steps.setdefault(step_id, []).append(round(duration, 1))
        self.steps[step_id] = self.steps[step_id][-HISTORY_KEEP:]

    def record_total(self, duration: float) -> None:
        self.totals.append(round(duration, 1))
        self.totals = self.totals[-HISTORY_KEEP:]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"steps": self.steps, "totals": self.totals}))


# ── change manifest (gate) ────────────────────────────────────────────────────

@dataclass
class ChangeManifest:
    head: str = "?"
    describe: str = ""
    wip_files: list[str] = field(default_factory=list)
    delta_sync: list[str] = field(default_factory=list)
    delta_delete: list[str] = field(default_factory=list)
    delta_error: str = ""
    eta_s: float | None = None
    last_total_s: float | None = None


def build_manifest(
    repo: Path,
    *,
    remote: str | None = None,
    history: StepHistory | None = None,
) -> ChangeManifest:
    manifest = ChangeManifest()
    repo = Path(repo).resolve()
    try:
        manifest.head = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "--short=12", "HEAD"], text=True
        ).strip()
        manifest.describe = subprocess.run(
            ["git", "-C", str(repo), "describe", "--tags", "--always"],
            capture_output=True, text=True,
        ).stdout.strip()
        manifest.wip_files = [
            ln[3:] for ln in subprocess.check_output(
                ["git", "-C", str(repo), "status", "--porcelain"], text=True
            ).splitlines() if ln.strip()
        ]
    except subprocess.CalledProcessError:
        pass

    if remote:
        from .gitsync import GitSyncError, collect_delta, read_deploy_commit

        host, _, remote_dir = remote.partition(":")
        try:
            base = read_deploy_commit(host, remote_dir)
            if not base:
                raise GitSyncError("no .deploy-commit on target (first deploy = full sync)")
            delta = collect_delta(repo, base)
            manifest.delta_sync = delta.sync
            manifest.delta_delete = delta.delete
        except (GitSyncError, subprocess.CalledProcessError) as exc:
            manifest.delta_error = str(exc)

    if history:
        if history.totals:
            manifest.last_total_s = history.totals[-1]
        all_ids = list(history.steps)
        manifest.eta_s = history.eta_for(all_ids) if all_ids else None
    return manifest


# ── progress-yaml consumer ────────────────────────────────────────────────────

@dataclass
class RunReport:
    returncode: int
    total_steps: int = 0
    completed: int = 0
    failed_step: str = ""
    error: str = ""
    durations: dict[str, float] = field(default_factory=dict)
    total_s: float = 0.0
    log_path: Path | None = None


def _iter_yaml_docs(stream):
    """Incrementally parse a '---'-separated YAML doc stream."""
    buf: list[str] = []
    for line in stream:
        if line.strip() == "---":
            if buf:
                try:
                    doc = yaml.safe_load("".join(buf))
                    if isinstance(doc, dict):
                        yield doc
                except yaml.YAMLError:
                    pass
            buf = []
        else:
            buf.append(line)
    if buf:
        try:
            doc = yaml.safe_load("".join(buf))
            if isinstance(doc, dict):
                yield doc
        except yaml.YAMLError:
            pass


def run_with_progress(
    spec: str,
    cwd: Path,
    *,
    extra_args: list[str] | None = None,
    history: StepHistory | None = None,
    on_event=None,
    log_dir: Path | None = None,
) -> RunReport:
    """Run ``redeploy run SPEC --progress-yaml`` and consume its event stream.

    ``on_event(kind, payload)`` fires for: ``start``, ``step_start``,
    ``step_done`` (payload gains ``duration_s`` / ``expected_s`` / ``eta_s``),
    ``step_fail``, ``done``, ``failed``. Engine logs (stderr) go to a file.
    """
    extra_args = extra_args or []
    log_dir = log_dir or Path("/tmp")
    log_path = log_dir / f"redeploy-deploy-{time.strftime('%H%M%S')}.log"
    report = RunReport(returncode=-1, log_path=log_path)

    t0 = time.time()
    step_started: dict[str, float] = {}
    plan_ids: list[str] = []

    with log_path.open("w") as log:
        proc = subprocess.Popen(
            ["redeploy", "run", spec, "--progress-yaml", *extra_args],
            cwd=str(cwd), text=True,
            stdout=subprocess.PIPE, stderr=log,
        )
        assert proc.stdout is not None
        for event in _iter_yaml_docs(proc.stdout):
            kind = event.get("event", "")
            if kind == "start":
                report.total_steps = int(event.get("total_steps") or 0)
                plan_ids = [s.get("id", "") for s in event.get("steps", [])]
            elif kind == "step_start":
                step_started[event.get("id", "")] = time.time()
                if history:
                    done_n = int(event.get("n") or 0)
                    remaining = plan_ids[done_n - 1:]
                    eta = history.eta_for(remaining)
                    event["eta_s"] = eta
                    event["expected_s"] = history.estimate(event.get("id", ""))
            elif kind == "step_done":
                sid = event.get("id", "")
                started = step_started.pop(sid, None)
                if started is not None:
                    duration = time.time() - started
                    event["duration_s"] = round(duration, 1)
                    report.durations[sid] = duration
                    if history:
                        history.record(sid, duration)
                report.completed = int(event.get("n") or report.completed)
            elif kind == "step_fail":
                report.failed_step = event.get("id", "")
                report.error = str(event.get("error", ""))
            elif kind == "failed":
                report.error = report.error or str(event.get("error", ""))
            if on_event:
                on_event(kind, event)
        proc.wait()
        report.returncode = proc.returncode

    report.total_s = time.time() - t0
    if history:
        if report.returncode == 0:
            history.record_total(report.total_s)
        history.save()
    return report
