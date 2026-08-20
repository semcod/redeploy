"""Tests for bounded redeploy run logs."""
from __future__ import annotations

from redeploy.cli.commands.plan_apply_run import _prune_run_logs


def test_prune_run_logs_keeps_newest(tmp_path, monkeypatch):
    monkeypatch.setenv("REDEPLOY_LOG_RETENTION", "2")
    for index in range(4):
        path = tmp_path / f"redeploy-20260724_00000{index}.log"
        path.write_text(str(index))
        path.touch()

    _prune_run_logs(tmp_path)

    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "redeploy-20260724_000002.log",
        "redeploy-20260724_000003.log",
    ]


def test_prune_run_logs_uses_safe_default_for_invalid_env(tmp_path, monkeypatch):
    monkeypatch.setenv("REDEPLOY_LOG_RETENTION", "invalid")
    for index in range(22):
        (tmp_path / f"redeploy-{index:02d}.log").write_text("")

    _prune_run_logs(tmp_path)

    assert len(list(tmp_path.glob("redeploy-*.log"))) == 20
