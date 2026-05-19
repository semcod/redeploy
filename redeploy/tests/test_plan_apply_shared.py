"""Tests for plan_apply_shared helpers."""
from __future__ import annotations

from redeploy.cli.commands.plan_apply_shared import ensure_redeployignore


class TestEnsureRedeployignore:
    def test_creates_file_when_missing(self, tmp_path):
        from rich.console import Console

        ensure_redeployignore(tmp_path, Console())
        path = tmp_path / ".redeployignore"
        assert path.exists()
        assert ".git/" in path.read_text()

    def test_does_not_overwrite_existing(self, tmp_path):
        from rich.console import Console

        (tmp_path / ".redeployignore").write_text("custom\n")
        ensure_redeployignore(tmp_path, Console())
        assert (tmp_path / ".redeployignore").read_text() == "custom\n"
