"""Tests for gitsync / pg_sync / source_hash / fleet_ops (no network)."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

from redeploy.fleet_ops import ProbeResult
from redeploy.gitsync import Delta, _remote_rel, collect_delta
from redeploy.pg_sync import PgEndpoint, _hash_query, diff_hashes, sync_tables
from redeploy.source_hash import (
    compute_scope_hash,
    publish_hashes,
    read_published_hash,
)


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True,
                       capture_output=True)

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (tmp_path / "app.py").write_text("v1\n")
    (tmp_path / "keep.txt").write_text("keep\n")
    (tmp_path / "gone.txt").write_text("bye\n")
    (tmp_path / ".gitignore").write_text("*.log\n")
    git("add", "-A")
    git("commit", "-qm", "base")
    return tmp_path


class TestCollectDelta:
    def test_modified_untracked_ignored_deleted(self, git_repo: Path):
        base = subprocess.check_output(
            ["git", "-C", str(git_repo), "rev-parse", "HEAD"], text=True
        ).strip()
        (git_repo / "app.py").write_text("v2\n")          # modified
        (git_repo / "new.txt").write_text("new\n")        # untracked
        (git_repo / "noise.log").write_text("x\n")        # ignored
        (git_repo / "gone.txt").unlink()                   # deleted

        delta = collect_delta(git_repo, base)
        assert "app.py" in delta.sync
        assert "new.txt" in delta.sync
        assert "noise.log" not in delta.sync
        assert delta.delete == ["gone.txt"]
        assert "keep.txt" not in delta.sync

    def test_clean_tree_is_empty(self, git_repo: Path):
        base = subprocess.check_output(
            ["git", "-C", str(git_repo), "rev-parse", "HEAD"], text=True
        ).strip()
        assert collect_delta(git_repo, base).empty


class TestRemoteRel:
    def test_tilde_normalised(self):
        # quoting '~' literally created a directory named '~' on targets —
        # the path must become $HOME-relative instead.
        assert _remote_rel("~/c2004") == "c2004"
        assert _remote_rel("/opt/app") == "/opt/app"


class TestPgSync:
    def test_hash_query_shape(self):
        sql = _hash_query("dbx", ["t1", "t2"])
        assert sql.count("UNION ALL") == 1
        assert "'dbx.t1'" in sql and '"t2"' in sql
        assert sql.endswith(";")

    def test_diff_hashes_buckets(self):
        left = {"a.t": (1, "h1"), "a.u": (2, "h2"), "a.only": (3, "x")}
        right = {"a.t": (1, "h1"), "a.u": (2, "DIFF"), "a.new": (1, "y")}
        diff = diff_hashes(left, right)
        assert diff.same == ["a.t"]
        assert diff.differs == ["a.u"]
        assert diff.only_left == ["a.only"]
        assert diff.only_right == ["a.new"]
        assert not diff.clean

    def test_sync_tables_blocks_operational_without_force(self):
        ep = PgEndpoint(container="c", user="u")
        with pytest.raises(PermissionError, match="app.protocols"):
            sync_tables(ep, ep, ["app.protocols"],
                        block_re=r"\.protocols", force=False)

    def test_sync_tables_dry_run_no_processes(self):
        ep = PgEndpoint(container="c", user="u")
        out = sync_tables(ep, ep, ["app.cfg"], block_re=None, dry_run=True)
        assert out == {"app": 0}


class TestSourceHash:
    def test_publish_read_roundtrip(self, git_repo: Path):
        (git_repo / ".redeploy-scopes.yaml").write_text(
            "scopes:\n  app:\n    - app.py\n"
        )
        published = publish_hashes(git_repo)
        assert set(published) == {"app"}
        assert read_published_hash(git_repo, "app") == published["app"]

    def test_hash_covers_untracked_not_ignored(self, git_repo: Path):
        before = compute_scope_hash(git_repo, ["."])
        (git_repo / "wip.txt").write_text("wip\n")   # untracked → counted
        assert compute_scope_hash(git_repo, ["."]) != before
        (git_repo / "x.log").write_text("noise\n")   # ignored → not counted
        after = compute_scope_hash(git_repo, ["."])
        (git_repo / "x.log").unlink()
        assert compute_scope_hash(git_repo, ["."]) == after

    def test_stale_published_hash_ignored(self, git_repo: Path, monkeypatch):
        (git_repo / ".redeploy-scopes.yaml").write_text("scopes:\n  app: [app.py]\n")
        publish_hashes(git_repo)
        fp = git_repo / ".redeploy-hashes" / "app"
        import os
        old = time.time() - 3 * 3600
        os.utime(fp, (old, old))
        assert read_published_hash(git_repo, "app") is None


class TestProbeResult:
    def test_healthy_logic(self):
        assert not ProbeResult("x").healthy
        ok = ProbeResult("x", online=True, fields={"net": "up", "api": "ok",
                                                   "failed_units": "none"})
        assert ok.healthy
        bad_unit = ProbeResult("x", online=True,
                               fields={"failed_units": "c2004-log-cleanup.service"})
        assert not bad_unit.healthy
        bad_http = ProbeResult("x", online=True, fields={"api": "FAIL"})
        assert not bad_http.healthy
