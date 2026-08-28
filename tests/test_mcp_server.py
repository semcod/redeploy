from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("mcp")

_SERVER_PATH = Path(__file__).resolve().parents[1] / "redeploy" / "mcp_server.py"
_SPEC = importlib.util.spec_from_file_location("redeploy_mcp_server_local", _SERVER_PATH)
assert _SPEC and _SPEC.loader
mcp_server = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mcp_server)


def test_run_spec_defaults_to_dry_run(monkeypatch):
    calls = []
    monkeypatch.setattr(
        mcp_server,
        "_run",
        lambda *args, **kwargs: calls.append((args, kwargs)) or {"success": True},
    )

    result = mcp_server.run_spec("migration.md")

    assert result["success"] is True
    assert "--dry-run" in calls[0][0]
    assert "--no-heal" in calls[0][0]


def test_run_spec_apply_requires_exact_approval(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        mcp_server,
        "_run",
        lambda *args, **kwargs: calls.append((args, kwargs)) or {"success": True},
    )
    payload = {
        "spec": "migration.md",
        "cwd": str(tmp_path.resolve()),
        "force": True,
        "heal": False,
        "fix_hint": "",
        "actor": "tom",
    }

    blocked = mcp_server.run_spec(
        "migration.md", force=True, dry_run=False, cwd=str(tmp_path), actor="tom"
    )
    assert blocked["requires_approval"] is True
    assert calls == []

    approval = mcp_server._approval_hash("redeploy_run_spec", payload)
    still_blocked = mcp_server.run_spec(
        "migration.md",
        force=True,
        dry_run=False,
        cwd=str(tmp_path),
        actor="tom",
        approval_hash=approval,
    )
    assert still_blocked["requires_approval"] is True
    assert still_blocked["required_env"] == "REDEPLOY_MCP_ALLOW_APPLY"
    assert calls == []

    monkeypatch.setenv("REDEPLOY_MCP_ALLOW_APPLY", "1")
    applied = mcp_server.run_spec(
        "migration.md",
        force=True,
        dry_run=False,
        cwd=str(tmp_path),
        actor="tom",
        approval_hash=approval,
    )
    assert applied["success"] is True
    assert "--dry-run" not in calls[0][0]
    assert "--force" in calls[0][0]


def test_exec_ssh_is_plan_only_without_approval(monkeypatch):
    monkeypatch.setattr(
        mcp_server.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("SSH must not run without approval"),
    )

    result = mcp_server.exec_ssh("user@example.com", "uptime")

    assert result["requires_approval"] is True
    assert result["executed"] is False


def test_bounded_output_marks_truncation():
    value, truncated = mcp_server._bounded_output("abcdef", limit=3)
    assert value == "abc"
    assert truncated is True
