"""Tests for plan_apply_report helpers."""
from __future__ import annotations

from unittest.mock import MagicMock

from redeploy.cli.commands.plan_apply_report import (
    build_checksum_verification,
    render_markdown_report,
    step_command_block,
)
from redeploy.models import DeployStrategy, InfraSpec, MigrationPlan, MigrationStep, StepAction


def _migration_with_sync(*, host: str = "pi@10.0.0.1", executed: bool = True):
    step = MigrationStep(
        id="sync_project_tree",
        action=StepAction.RSYNC,
        description="sync",
        src="/tmp/project/",
        dst="~/app/",
        excludes=[".git/"],
    )
    target = InfraSpec(strategy=DeployStrategy.DOCKER_FULL, host=host, app="t", version="1")
    source = InfraSpec(strategy=DeployStrategy.DOCKER_FULL, host=host)
    plan = MigrationPlan(
        name="t",
        source=source,
        target=target,
        from_strategy=DeployStrategy.DOCKER_FULL,
        to_strategy=DeployStrategy.DOCKER_FULL,
        host=host,
        app="t",
        steps=[step],
    )
    return plan, executed


class TestBuildChecksumVerification:
    def test_skipped_when_no_sync_step(self):
        target = InfraSpec(strategy=DeployStrategy.DOCKER_FULL, host="h", app="t", version="1")
        source = InfraSpec(strategy=DeployStrategy.DOCKER_FULL, host="h")
        plan = MigrationPlan(
            name="t",
            source=source,
            target=target,
            from_strategy=DeployStrategy.DOCKER_FULL,
            to_strategy=DeployStrategy.DOCKER_FULL,
            host="h",
            app="t",
            steps=[],
        )
        assert build_checksum_verification(plan, executed=True) is None

    def test_skipped_plan_only(self):
        plan, _ = _migration_with_sync()
        result = build_checksum_verification(plan, executed=False)
        assert result is not None
        assert result["status"] == "skipped"
        assert "plan-only" in result["reason"]


class TestRenderMarkdownReport:
    def test_includes_step_logs(self):
        plan, _ = _migration_with_sync()
        entry = MagicMock()
        entry.ts = "2026-01-01T00:00:00Z"
        entry.host = plan.host
        entry.app = plan.app
        entry.from_strategy = "docker_full"
        entry.to_strategy = "docker_full"
        entry.ok = True
        entry.steps_ok = 1
        entry.steps_total = 1
        entry.elapsed_s = 1.0
        entry.steps = [{"id": "sync_project_tree", "action": "rsync", "status": "done", "result": "ok", "error": ""}]

        md = render_markdown_report(entry, plan, __import__("pathlib").Path("migration.yaml"))
        assert "sync_project_tree" in md
        assert "Step Logs" in md


class TestStepCommandBlock:
    def test_rsync(self):
        step = MigrationStep(
            id="s",
            action=StepAction.RSYNC,
            description="d",
            src="./",
            dst="~/x",
        )
        assert "rsync" in step_command_block(step)
