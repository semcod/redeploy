"""Executor — runs MigrationPlan steps, handles rollback on failure."""
from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import IO, Any, Optional

import yaml
from loguru import logger

from ..detect.remote import RemoteProbe
from ..models import Hook, MigrationPlan, MigrationStep, StepAction, StepStatus
from .exceptions import StepError
from .handlers import (
    run_ssh, run_scp, run_rsync, run_docker_build, run_podman_build,
    run_docker_health_wait, run_container_log_tail, run_http_check,
    run_version_check, run_plugin, run_wait, run_inline_script,
    run_ensure_config_line, run_raspi_config,
    run_ensure_kanshi_profile, run_ensure_autostart_entry, run_ensure_browser_kiosk_script,
    run_testql, run_oql, run_aql,
)
from .progress import ProgressEmitter
from .rollback import rollback_steps
from .state import ResumeState, default_state_path


class Executor:
    """Execute MigrationPlan steps on a remote host."""

    def __init__(self, plan: MigrationPlan, dry_run: bool = False,
                 ssh_key: Optional[str] = None,
                 progress_yaml: bool = False,
                 progress_stream: IO[str] = None,
                 audit_log: bool = True,
                 audit_path: Optional["Path"] = None,
                 resume: bool = False,
                 from_step: Optional[str] = None,
                 state_path: Optional["Path"] = None,
                 spec_path: Optional[str] = None,
                 parallel_jobs: Optional[int] = None):
        self.plan = plan
        self.dry_run = dry_run
        self.probe = RemoteProbe(plan.host)
        if ssh_key:
            self.probe.key = ssh_key
        self._completed: list[MigrationStep] = []
        self._emitter: Optional[ProgressEmitter] = (
            ProgressEmitter(progress_stream) if progress_yaml else None
        )
        self._audit_log = audit_log
        self._audit_path = audit_path
        self._t0: float = 0.0

        # ── parallel_group execution ─────────────────────────────────────────
        # Concurrency cap for a parallel_group batch. Default 3: builds on the
        # Pi compete for SD-card I/O, more workers only thrash the card.
        if parallel_jobs is None:
            env_jobs = os.environ.get("REDEPLOY_PARALLEL_JOBS", "").strip()
            try:
                parallel_jobs = int(env_jobs) if env_jobs else 3
            except ValueError:
                parallel_jobs = 3
        self._parallel_jobs = max(1, parallel_jobs)
        # Emitter events, _completed and _state.mark_done are not thread-safe —
        # one lock guards the whole "step finished" bookkeeping transaction.
        self._batch_lock = threading.Lock()

        # ── spec path for command_ref resolution ─────────────────────────────
        if spec_path and not plan.spec_path:
            plan.spec_path = spec_path

        # ── resume / checkpoint ──────────────────────────────────────────────
        self._resume = resume
        self._from_step = from_step
        spec_id = spec_path or plan.spec_path or plan.target_file or plan.infra_file or plan.app
        if state_path is None and not dry_run:
            state_path = default_state_path(spec_id, plan.host)
        self._state_path: Optional[Path] = (
            Path(state_path) if state_path is not None else None
        )
        self._state: Optional[ResumeState] = None
        if self._state_path is not None and not dry_run:
            self._state = ResumeState.load_or_new(
                self._state_path,
                spec_path=str(spec_id),
                host=plan.host,
                total_steps=len(plan.steps),
            )
            # Keep total_steps in sync if the spec changed between runs.
            self._state.total_steps = len(plan.steps)

    @property
    def completed_steps(self) -> list[MigrationStep]:
        return list(self._completed)

    @property
    def state(self) -> Optional[ResumeState]:
        """Current ResumeState (None when dry_run or disabled)."""
        return self._state

    @property
    def state_path(self) -> Optional[Path]:
        return self._state_path

    def run(self) -> bool:
        """Execute all steps. Returns True if all passed."""
        self._t0 = time.monotonic()
        prefix = "[DRY RUN] " if self.dry_run else ""
        logger.info(f"{prefix}Applying plan: {len(self.plan.steps)} steps "
                    f"({self.plan.from_strategy.value} → {self.plan.to_strategy.value})")
        if self._emitter:
            self._emitter.start(self.plan)

        skip_ids = self._compute_skip_set()
        if skip_ids:
            logger.info(f"resume: skipping {len(skip_ids)} already-completed step(s): "
                        f"{', '.join(sorted(skip_ids))}")

        self._fire_hooks("before_apply")
        ok = self._execute_steps_loop(skip_ids)
        elapsed = time.monotonic() - self._t0

        self._handle_completion(ok, elapsed)
        self._write_audit(ok=ok, elapsed_s=elapsed)
        self._fire_hooks("always", ok=ok, elapsed_s=elapsed)
        return ok

    def _execute_steps_loop(self, skip_ids: set[str]) -> bool:
        """Execute steps, handling skips and errors. Returns True if all passed.

        Consecutive steps sharing the same non-empty ``parallel_group`` form a
        batch and run concurrently (bounded by ``parallel_jobs``). Everything
        else — including 1-element batches and ``--parallel-jobs 1`` — takes
        the exact same sequential path as before.
        """
        steps = self.plan.steps
        total = len(steps)
        idx = 0
        while idx < total:
            group = steps[idx].parallel_group
            end = idx + 1
            if group:
                while end < total and steps[end].parallel_group == group:
                    end += 1

            # Steps already completed (resume / --from-step): skip like today.
            runnable: list[tuple[int, MigrationStep]] = []
            for j in range(idx, end):
                if steps[j].id in skip_ids:
                    self._skip_step(j + 1, steps[j])
                else:
                    runnable.append((j + 1, steps[j]))
            idx = end
            if not runnable:
                continue

            if (group and len(runnable) > 1
                    and self._parallel_jobs > 1 and not self.dry_run):
                if not self._run_parallel_batch(group, runnable):
                    return False
            else:
                for n, step in runnable:
                    if not self._run_single_step(n, step):
                        return False
        return True

    def _run_single_step(self, i: int, step: MigrationStep) -> bool:
        """Execute one step sequentially (pre-parallel_group semantics)."""
        try:
            if self._emitter:
                self._emitter.step_start(i, step)
            self._fire_hooks("before_step", step=step)
            t0 = time.monotonic()
            self._execute_step(step)
            self._completed.append(step)
            if self._state is not None:
                self._state.mark_done(step.id)
            if self._emitter:
                self._emitter.step_done(i, step,
                                        duration_s=round(time.monotonic() - t0, 1))
            self._fire_hooks("after_step", step=step)
            return True
        except StepError as e:
            self._fire_hooks("on_step_failure", step=step, error=str(e))
            self._handle_step_failure(i, step, e)
            return False

    def _run_parallel_batch(self, group: str,
                            items: list[tuple[int, MigrationStep]]) -> bool:
        """Run a parallel_group batch concurrently. Returns True if all passed.

        Semantics:
        - ``step_start`` (+ before_step hooks) fire sequentially up-front, in
          plan order, for readable progress output;
        - ``step_done`` / ``step_fail`` fire as each step actually finishes
          (with per-step ``duration_s``), under ``_batch_lock``;
        - on failure NOTHING is interrupted mid-flight (podman builds do not
          survive SIGKILL cleanly) — the pool drains, successful steps are
          counted into ``_completed`` / ``mark_done``, then the FIRST failure
          (plan order) goes through the standard ``_handle_step_failure`` path
          so rollback covers everything completed so far;
        - after_step hooks fire from the main thread, in plan order, only for
          successful steps (hooks are not assumed thread-safe).
        """
        jobs = min(self._parallel_jobs, len(items))
        logger.info(f"parallel_group '{group}': {len(items)} step(s), "
                    f"{jobs} concurrent job(s)")
        for n, step in items:
            if self._emitter:
                self._emitter.step_start(n, step)
            self._fire_hooks("before_step", step=step)

        succeeded: list[tuple[int, MigrationStep]] = []
        failures: list[tuple[int, MigrationStep, StepError]] = []

        def _worker(n: int, step: MigrationStep) -> None:
            t0 = time.monotonic()
            try:
                self._execute_step(step)
            except StepError as e:
                duration = round(time.monotonic() - t0, 1)
                with self._batch_lock:
                    step.status = StepStatus.FAILED
                    step.error = str(e)
                    failures.append((n, step, e))
                    if self._emitter:
                        self._emitter.step_fail(n, step, str(e),
                                                duration_s=duration)
                return
            duration = round(time.monotonic() - t0, 1)
            with self._batch_lock:
                self._completed.append(step)
                if self._state is not None:
                    self._state.mark_done(step.id)
                succeeded.append((n, step))
                if self._emitter:
                    self._emitter.step_done(n, step, duration_s=duration)

        with ThreadPoolExecutor(max_workers=jobs,
                                thread_name_prefix=f"pg-{group}") as pool:
            # list() drains the iterator so a non-StepError exception from any
            # worker propagates (mirrors the sequential path); the context
            # manager still waits for every in-flight step to finish first.
            list(pool.map(lambda it: _worker(*it), items))

        for n, step in sorted(succeeded):
            self._fire_hooks("after_step", step=step)

        if not failures:
            return True
        failures.sort(key=lambda f: f[0])
        n, step, error = failures[0]
        self._fire_hooks("on_step_failure", step=step, error=str(error))
        self._handle_step_failure(n, step, error, step_fail_emitted=True)
        return False

    def _skip_step(self, i: int, step: MigrationStep) -> None:
        """Handle a skipped step due to resume."""
        step.status = StepStatus.SKIPPED
        step.result = "resumed: previously completed"
        if self._emitter:
            self._emitter.step_done(i, step)

    def _handle_step_failure(self, i: int, step: MigrationStep, error: StepError,
                             *, step_fail_emitted: bool = False) -> None:
        """Handle a step failure.

        ``step_fail_emitted`` — parallel batches emit step_fail the moment the
        step finishes; skip the duplicate emission here.
        """
        logger.error(f"Step failed: {error}")
        step.status = StepStatus.FAILED
        step.error = str(error)
        if self._state is not None:
            self._state.mark_failed(step.id, str(error))
        if self._emitter:
            if not step_fail_emitted:
                self._emitter.step_fail(i, step, str(error))
            self._emitter.failed(len(self._completed), len(self.plan.steps), str(error))
        if not self.dry_run:
            self._rollback()

    def _handle_completion(self, ok: bool, elapsed: float) -> None:
        """Handle plan completion or failure."""
        if ok:
            logger.info(f"{'[DRY RUN] ' if self.dry_run else ''}All {len(self.plan.steps)} steps completed")
            if self._emitter:
                self._emitter.done(len(self.plan.steps))
            # Plan finished cleanly — drop the checkpoint.
            if self._state is not None:
                self._state.remove()
            self._fire_hooks("after_apply", elapsed_s=elapsed)
        else:
            if self._state is not None and self._state_path is not None:
                logger.info(f"resume: checkpoint saved → {self._state_path} "
                            f"({self._state.completed_count}/{self._state.total_steps} done)")
            self._fire_hooks("on_failure", elapsed_s=elapsed)

    # ── Pipeline hooks (generic) ─────────────────────────────────────────────

    def _fire_hooks(self, phase: str, **context: Any) -> None:
        """Fire all hooks registered for a given phase. Honors ``when`` + ``on_failure``."""
        hooks = [h for h in getattr(self.plan, "hooks", []) if h.phase == phase]
        if not hooks:
            return
        for hook in hooks:
            if hook.when and not self._eval_hook_condition(hook.when, context):
                continue
            try:
                self._execute_hook(hook, context)
            except Exception as exc:  # noqa: BLE001
                self._handle_hook_failure(hook, exc)

    def _eval_hook_condition(self, expr: str, context: dict) -> bool:
        """Evaluate a simple hook condition against the context.

        Supports only ``step.id == 'foo'`` / ``step.id != 'foo'`` for now to avoid
        executing arbitrary expressions. Extend with jmespath when needed.
        """
        step = context.get("step")
        step_id = getattr(step, "id", None)
        expr = expr.strip()
        for op in ("==", "!="):
            if op in expr:
                left, right = [p.strip() for p in expr.split(op, 1)]
                right = right.strip("'\"")
                if left == "step.id":
                    return (step_id == right) if op == "==" else (step_id != right)
        logger.warning(f"hook: unsupported when expression: {expr!r}")
        return True

    def _execute_hook(self, hook: "Hook", context: dict) -> None:
        """Execute a hook. Built-in actions handled inline; rest delegated to step runners."""
        action = hook.action
        extra = hook.model_dump(exclude={"id", "phase", "action", "description", "when", "on_failure"})
        logger.info(f"hook[{hook.phase}] {hook.id}: {action}")
        if self.dry_run:
            return

        # Built-in: local_cmd — run a command on the controller machine (opens browser, clears local cache, etc.)
        if action == "local_cmd":
            import subprocess
            cmd = extra.get("command") or ""
            if not cmd:
                raise ValueError(f"hook {hook.id}: local_cmd requires 'command'")
            subprocess.run(cmd, shell=True, check=True)
            return

        # Built-in: open_url — open a URL in the default browser (controller machine)
        if action == "open_url":
            import webbrowser
            url = extra.get("url") or extra.get("command") or ""
            if not url:
                raise ValueError(f"hook {hook.id}: open_url requires 'url'")
            webbrowser.open(url)
            return

        # Fallback: treat hook like a MigrationStep and let existing runners handle it.
        step = MigrationStep(
            id=hook.id,
            action=action,  # pydantic will validate against StepAction enum
            description=hook.description or f"hook:{hook.phase}:{hook.id}",
            **extra,
        )
        self._execute_step(step)

    def _handle_hook_failure(self, hook: "Hook", exc: Exception) -> None:
        policy = hook.on_failure
        msg = f"hook {hook.id} ({hook.phase}) failed: {exc}"
        if policy == "abort":
            logger.error(msg)
            raise exc
        if policy == "warn":
            logger.warning(msg)
        else:  # continue
            logger.debug(msg)

    def _compute_skip_set(self) -> set[str]:
        """Determine which step ids should be skipped this run.

        Sources (in priority order):
          1. ``--from-step <id>``: skip every step BEFORE that id.
          2. ``--resume`` + persisted state: skip every previously completed id.
        """
        skip: set[str] = set()
        ids = [s.id for s in self.plan.steps]

        if self._from_step:
            if self._from_step not in ids:
                logger.warning(
                    f"--from-step '{self._from_step}' not found in plan; running full plan"
                )
            else:
                idx = ids.index(self._from_step)
                skip.update(ids[:idx])

        if self._resume and self._state is not None:
            skip.update(self._state.completed_step_ids)

        return skip

    def _write_audit(self, *, ok: bool, elapsed_s: float) -> None:
        if not self._audit_log:
            return
        try:
            from ..observe import DeployAuditLog
            log = DeployAuditLog(path=self._audit_path)
            log.record(self.plan, self._completed, ok=ok,
                       elapsed_s=elapsed_s, dry_run=self.dry_run)
        except Exception as exc:  # never crash the executor
            logger.debug(f"audit_log write failed (non-fatal): {exc}")

    # ── step dispatcher ───────────────────────────────────────────────────────

    def _execute_step(self, step: MigrationStep) -> None:
        logger.info(f"  {'[DRY]' if self.dry_run else '→'} [{step.id}] {step.description}")
        step.status = StepStatus.RUNNING

        if self.dry_run:
            step.status = StepStatus.DONE
            step.result = "dry-run"
            return

        dispatch = {
            StepAction.SYSTEMCTL_STOP:      lambda s: run_ssh(s, self.probe),
            StepAction.SYSTEMCTL_DISABLE:   lambda s: run_ssh(s, self.probe),
            StepAction.SYSTEMCTL_START:     lambda s: run_ssh(s, self.probe),
            StepAction.KUBECTL_DELETE:      lambda s: run_ssh(s, self.probe),
            StepAction.DOCKER_COMPOSE_UP:   lambda s: run_ssh(s, self.probe),
            StepAction.DOCKER_COMPOSE_DOWN: lambda s: run_ssh(s, self.probe),
            StepAction.DOCKER_BUILD:        lambda s: run_docker_build(s, self.probe, self._emitter),
            StepAction.DOCKER_HEALTH_WAIT:  lambda s: run_docker_health_wait(s, self.probe),
            StepAction.CONTAINER_LOG_TAIL:  lambda s: run_container_log_tail(s, self.probe),
            StepAction.PODMAN_BUILD:        lambda s: run_podman_build(s, self.probe, self._emitter),
            StepAction.SSH_CMD:             lambda s: run_ssh(s, self.probe),
            StepAction.SCP:                 lambda s: run_scp(s, self.probe, self.plan),
            StepAction.RSYNC:               lambda s: run_rsync(s, self.probe, self.plan),
            StepAction.HTTP_CHECK:          lambda s: run_http_check(s, self.probe),
            StepAction.TESTQL:              lambda s: run_testql(s, self.probe),
            StepAction.OQL:                 lambda s: run_oql(s, self.probe),
            StepAction.AQL:                 lambda s: run_aql(s, self.probe),
            StepAction.VERSION_CHECK:       lambda s: run_version_check(s, self.probe),
            StepAction.WAIT:                lambda s: run_wait(s),
            StepAction.PLUGIN:              lambda s: run_plugin(s, self.probe, self.plan, self._emitter, self.dry_run),
            StepAction.INLINE_SCRIPT:       lambda s: run_inline_script(s, self.probe, self.plan),
            StepAction.ENSURE_CONFIG_LINE:  lambda s: run_ensure_config_line(s, self.probe),
            StepAction.RASPI_CONFIG:        lambda s: run_raspi_config(s, self.probe),
            StepAction.ENSURE_KANSHI_PROFILE:      lambda s: run_ensure_kanshi_profile(s, self.probe),
            StepAction.ENSURE_AUTOSTART_ENTRY:     lambda s: run_ensure_autostart_entry(s, self.probe),
            StepAction.ENSURE_BROWSER_KIOSK_SCRIPT: lambda s: run_ensure_browser_kiosk_script(s, self.probe),
        }

        handler = dispatch.get(step.action)
        if not handler:
            raise StepError(step, f"No handler for action {step.action}")
        handler(step)

    # ── rollback ──────────────────────────────────────────────────────────────

    def _rollback(self) -> None:
        rollback_steps(self._completed, self.probe, self._state)

    # ── summary ───────────────────────────────────────────────────────────────

    def summary(self) -> str:
        total = len(self.plan.steps)
        done = sum(1 for s in self.plan.steps if s.status == StepStatus.DONE)
        failed = sum(1 for s in self.plan.steps if s.status == StepStatus.FAILED)
        icon = "✅" if failed == 0 else "❌"
        return f"{icon} {done}/{total} steps completed" + (f", {failed} failed" if failed else "")

    @staticmethod
    def from_file(plan_path: Path) -> "Executor":
        with plan_path.open() as f:
            raw = yaml.safe_load(f)
        plan = MigrationPlan(**raw)
        return Executor(plan)

    def save_results(self, output: Path) -> None:
        data = self.plan.model_dump(mode="json")
        output.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))
        logger.info(f"Results saved to {output}")
