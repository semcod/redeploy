"""Tests for parallel_group execution in the Executor.

Consecutive steps sharing the same non-empty ``parallel_group`` run
concurrently (bounded by ``parallel_jobs``); everything else keeps the
strictly sequential semantics.
"""
from __future__ import annotations

import base64
import re
import threading
import time
from unittest.mock import MagicMock

import redeploy.apply.executor as executor_mod
from redeploy.apply.executor import Executor
from redeploy.apply.state import ResumeState
from redeploy.models import (
    ConflictSeverity,
    DeployStrategy,
    MigrationPlan,
    MigrationStep,
    StepAction,
    StepStatus,
)

SLEEP = 0.3

# run_inline_script ships the script over SSH base64-encoded:
#   tmpfile=$(mktemp) && echo '<b64>' | base64 -d > "$tmpfile" && ...
_B64_RE = re.compile(r"echo '([A-Za-z0-9+/=]+)' \| base64 -d")


# ── helpers ───────────────────────────────────────────────────────────────────


def _step(sid: str, script: str | None = None, group: str | None = None) -> MigrationStep:
    return MigrationStep(
        id=sid,
        action=StepAction.INLINE_SCRIPT,
        description=f"step {sid}",
        command=script if script is not None else f"sleep {SLEEP} # {sid}",
        parallel_group=group,
    )


def _plan(steps: list[MigrationStep]) -> MigrationPlan:
    return MigrationPlan(
        host="local",
        app="testapp",
        from_strategy=DeployStrategy.DOCKER_FULL,
        to_strategy=DeployStrategy.DOCKER_FULL,
        risk=ConflictSeverity.LOW,
        steps=steps,
        notes=[],
    )


def _fake_probe():
    """Probe whose run() decodes the inline script and simulates it:

    - script containing ``sleep`` really sleeps SLEEP seconds;
    - script containing ``FAIL`` returns exit 1.
    """
    probe = MagicMock()
    calls: list[str] = []
    lock = threading.Lock()

    def fake_run(cmd, timeout=300):
        m = _B64_RE.search(cmd)
        script = base64.b64decode(m.group(1)).decode() if m else cmd
        with lock:
            calls.append(script)
        if "sleep" in script:
            time.sleep(SLEEP)
        r = MagicMock()
        if "FAIL" in script:
            r.ok, r.exit_code, r.out, r.stderr = False, 1, "", "boom"
        else:
            r.ok, r.exit_code, r.out, r.stderr = True, 0, "ok", ""
        return r

    probe.run.side_effect = fake_run
    probe.is_local = True
    probe.calls = calls
    return probe


def _executor(plan: MigrationPlan, tmp_path, **kwargs) -> Executor:
    exc = Executor(
        plan,
        audit_log=False,
        state_path=tmp_path / "state.yaml",
        spec_path="spec.yaml",
        **kwargs,
    )
    exc.probe = _fake_probe()
    return exc


# ── (a) concurrency proof ─────────────────────────────────────────────────────


def test_parallel_batch_runs_concurrently(tmp_path):
    steps = [_step(f"b{i}", group="builds") for i in range(3)]
    plan = _plan(steps)
    exc = _executor(plan, tmp_path)

    t0 = time.monotonic()
    assert exc.run() is True
    elapsed = time.monotonic() - t0

    # 3 × 0.3 s sequentially would be ≥ 0.9 s; concurrent must fit under 0.7 s.
    assert elapsed < 0.7, f"batch not concurrent: {elapsed:.2f}s"
    assert all(s.status == StepStatus.DONE for s in steps)
    assert {s.id for s in exc.completed_steps} == {"b0", "b1", "b2"}


# ── (b) no group → sequential ─────────────────────────────────────────────────


def test_ungrouped_steps_run_sequentially(tmp_path):
    steps = [_step(f"s{i}") for i in range(3)]
    plan = _plan(steps)
    exc = _executor(plan, tmp_path)

    t0 = time.monotonic()
    assert exc.run() is True
    elapsed = time.monotonic() - t0

    assert elapsed >= 3 * SLEEP, f"ungrouped steps overlapped: {elapsed:.2f}s"
    assert all(s.status == StepStatus.DONE for s in steps)


# ── (c) failure inside a batch ────────────────────────────────────────────────


def test_batch_failure_finishes_others_then_rolls_back(tmp_path, monkeypatch):
    steps = [
        _step("okA", group="builds"),                      # sleeps 0.3 s
        _step("bad", script="FAIL # bad", group="builds"),  # fails ~instantly
        _step("okB", group="builds"),                      # sleeps 0.3 s
        _step("never"),                                     # after the batch
    ]
    plan = _plan(steps)
    exc = _executor(plan, tmp_path)

    rollback_calls = {}

    def fake_rollback(completed, probe, state=None):
        rollback_calls["completed"] = list(completed)

    monkeypatch.setattr(executor_mod, "rollback_steps", fake_rollback)

    t0 = time.monotonic()
    assert exc.run() is False
    elapsed = time.monotonic() - t0

    # The fast failure must NOT interrupt the sleeping steps mid-flight.
    assert elapsed >= SLEEP, "batch did not wait for in-flight steps"
    assert steps[0].status == StepStatus.DONE
    assert steps[1].status == StepStatus.FAILED
    assert steps[2].status == StepStatus.DONE
    assert steps[3].status == StepStatus.PENDING  # never started

    # Successful batch members count as completed → rollback covers them.
    assert {s.id for s in exc.completed_steps} == {"okA", "okB"}
    assert {s.id for s in rollback_calls["completed"]} == {"okA", "okB"}

    # Checkpoint records the failure and the successes.
    assert exc.state.failed_step_id == "bad"
    assert set(exc.state.completed_step_ids) == {"okA", "okB"}


# ── (d) --parallel-jobs=1 degrades to sequential ──────────────────────────────


def test_parallel_jobs_one_degrades_to_sequential(tmp_path):
    steps = [_step(f"b{i}", group="builds") for i in range(3)]
    plan = _plan(steps)
    exc = _executor(plan, tmp_path, parallel_jobs=1)

    t0 = time.monotonic()
    assert exc.run() is True
    elapsed = time.monotonic() - t0

    assert elapsed >= 3 * SLEEP, f"jobs=1 still overlapped: {elapsed:.2f}s"
    assert all(s.status == StepStatus.DONE for s in steps)


def test_env_fallback_parallel_jobs(tmp_path, monkeypatch):
    monkeypatch.setenv("REDEPLOY_PARALLEL_JOBS", "1")
    steps = [_step(f"b{i}", group="builds") for i in range(2)]
    plan = _plan(steps)
    exc = _executor(plan, tmp_path)

    t0 = time.monotonic()
    assert exc.run() is True
    elapsed = time.monotonic() - t0

    assert exc._parallel_jobs == 1
    assert elapsed >= 2 * SLEEP


# ── (e) resume: completed batch step is not re-executed ───────────────────────


def test_resume_skips_completed_batch_step(tmp_path):
    steps = [_step(f"b{i}", group="builds") for i in range(3)]
    plan = _plan(steps)

    state_path = tmp_path / "state.yaml"
    st = ResumeState(spec_path="spec.yaml", host="local", total_steps=3,
                     completed_step_ids=["b0"])
    st.save(state_path)

    exc = _executor(plan, tmp_path, resume=True)
    t0 = time.monotonic()
    assert exc.run() is True
    elapsed = time.monotonic() - t0

    assert steps[0].status == StepStatus.SKIPPED
    assert steps[1].status == StepStatus.DONE
    assert steps[2].status == StepStatus.DONE

    executed = "\n".join(exc.probe.calls)
    assert "# b0" not in executed, "resumed step was re-executed"
    assert "# b1" in executed and "# b2" in executed
    # The two remaining steps still run as a (smaller) parallel batch.
    assert elapsed < 2 * SLEEP


# ── mixed plan: batch boundaries ──────────────────────────────────────────────


def test_group_batches_only_when_consecutive(tmp_path):
    """Same group name separated by an ungrouped step forms two batches."""
    steps = [
        _step("g1", group="builds"),
        _step("mid"),
        _step("g2", group="builds"),
    ]
    plan = _plan(steps)
    exc = _executor(plan, tmp_path)

    t0 = time.monotonic()
    assert exc.run() is True
    elapsed = time.monotonic() - t0

    # No two steps may overlap → strictly sequential timing.
    assert elapsed >= 3 * SLEEP
    assert all(s.status == StepStatus.DONE for s in steps)
