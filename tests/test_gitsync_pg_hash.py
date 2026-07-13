"""Tests for gitsync / pg_sync / source_hash / fleet_ops (no network)."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

from redeploy.fleet_ops import ProbeResult
from redeploy.gitsync import (
    Delta,
    GitSyncError,
    _remote_rel,
    collect_delta,
    collect_frozen_delta,
    frozen_rsync_src,
    frozen_sync,
    record_deploy_commit,
)
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


class TestFrozenSync:
    """frozen_sync — delta i treść WYŁĄCZNIE z HEAD (working tree nie jedzie)."""

    @staticmethod
    def _git(root: Path, *args):
        subprocess.run(["git", "-C", str(root), *args], check=True,
                       capture_output=True)

    @staticmethod
    def _head(root: Path) -> str:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()

    @pytest.fixture()
    def local_remote(self, git_repo: Path, monkeypatch):
        """Lokalny katalog jako „remote": ssh/tar i rm podmienione monkeypatchem.

        _head_archive zostaje PRODUKCYJNE (git archive HEAD) — test weryfikuje,
        że treść naprawdę pochodzi z HEAD, nie z working tree.
        """
        import io
        import tarfile

        import redeploy.gitsync as gitsync

        remote = git_repo / "_remote"
        remote.mkdir()

        def fake_extract(host, remote_dir, payload):
            assert host == "pi@test"
            with tarfile.open(fileobj=io.BytesIO(payload)) as tar:
                tar.extractall(remote_dir, filter="data")

        def fake_deletes(host, remote_dir, paths):
            for rel in paths:
                (Path(remote_dir) / rel).unlink(missing_ok=True)

        monkeypatch.setattr(gitsync, "_remote_extract", fake_extract)
        monkeypatch.setattr(gitsync, "_apply_deletes", fake_deletes)
        return remote

    def test_ships_head_content_not_working_tree(self, git_repo: Path, local_remote: Path):
        base = self._head(git_repo)

        # Commit: app.py → v2-head, nowy shipped.txt, delete gone.txt.
        (git_repo / "app.py").write_text("v2-head\n")
        (git_repo / "shipped.txt").write_text("shipped\n")
        (git_repo / "gone.txt").unlink()
        self._git(git_repo, "add", "-A")
        self._git(git_repo, "commit", "-qm", "head")

        # Równoległe edycje PO commicie (symulacja incydentu 2026-07-10):
        (git_repo / "app.py").write_text("wip-overwrite\n")   # nadpisany w WT
        (git_repo / "keep.txt").write_text("wip-only\n")      # zmiana tylko w WT
        (git_repo / "untracked.txt").write_text("wip\n")      # untracked

        (local_remote / "gone.txt").write_text("stale\n")     # do usunięcia

        delta = frozen_sync(git_repo, "pi@test", str(local_remote), base_commit=base)

        # Delta liczona z base..HEAD — bez working tree i untracked.
        assert set(delta.sync) == {"app.py", "shipped.txt"}
        assert delta.delete == ["gone.txt"]

        # Treść jedzie z HEAD, mimo że working tree ma inną wersję.
        assert (local_remote / "app.py").read_text() == "v2-head\n"
        assert (local_remote / "shipped.txt").read_text() == "shipped\n"

        # WIP/untracked NIE dojechały; delete zastosowany zdalnie.
        assert not (local_remote / "keep.txt").exists()
        assert not (local_remote / "untracked.txt").exists()
        assert not (local_remote / "gone.txt").exists()

    def test_collect_frozen_delta_ignores_working_tree(self, git_repo: Path):
        base = self._head(git_repo)
        (git_repo / "app.py").write_text("only-wip\n")        # bez commita
        (git_repo / "untracked.txt").write_text("wip\n")
        assert collect_frozen_delta(git_repo, base).empty
        # Dla porównania: klasyczna delta working tree te pliki widzi.
        wt = collect_delta(git_repo, base)
        assert "app.py" in wt.sync and "untracked.txt" in wt.sync

    def test_unknown_base_raises(self, git_repo: Path, local_remote: Path):
        with pytest.raises(GitSyncError, match="unknown base commit"):
            frozen_sync(git_repo, "pi@test", str(local_remote),
                        base_commit="deadbeef" * 5)

    def test_missing_deploy_commit_raises(self, git_repo: Path, local_remote: Path,
                                          monkeypatch):
        import redeploy.gitsync as gitsync

        monkeypatch.setattr(gitsync, "read_deploy_commit", lambda *a, **k: None)
        with pytest.raises(GitSyncError, match=r"no \.deploy-commit"):
            frozen_sync(git_repo, "pi@test", str(local_remote))

    def test_record_deploy_commit_explicit_commit(self, git_repo: Path, monkeypatch):
        """--record po frozen deployu stempluje commit ZAMROŻONY, nie HEAD."""
        import redeploy.gitsync as gitsync

        frozen = self._head(git_repo)
        (git_repo / "app.py").write_text("later\n")
        self._git(git_repo, "add", "-A")
        self._git(git_repo, "commit", "-qm", "made-during-deploy")
        assert self._head(git_repo) != frozen

        sent: dict = {}

        def fake_run(cmd, **kwargs):
            sent["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0)

        monkeypatch.setattr(gitsync.subprocess, "run", fake_run)
        stamped = record_deploy_commit(git_repo, "pi@test", "~/c2004", commit=frozen)
        assert stamped == frozen
        assert frozen in " ".join(sent["cmd"])


class TestFrozenRsyncSrc:
    """Kroki `action: rsync` spec-a w trybie frozen — źródło z git archive.

    Incydent 2026-07-12: sync_connect_scenario rsyncował working tree i
    przemycił WIP innej sesji mimo zamrożonego syncu projektu.
    """

    def _head(self, root: Path) -> str:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()

    def test_tracked_dir_ships_commit_content_not_wip(self, git_repo: Path, tmp_path: Path):
        sub = git_repo / "module"
        sub.mkdir()
        (sub / "code.py").write_text("committed\n")
        subprocess.run(["git", "-C", str(git_repo), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(git_repo), "commit", "-qm", "module"], check=True)
        head = self._head(git_repo)
        (sub / "code.py").write_text("WIP-other-session\n")   # bez commita

        export = tmp_path / "export"
        src, note = frozen_rsync_src(git_repo, head, "module/", export)
        assert src.endswith("/"), "trailing slash rsync musi przetrwać"
        assert head[:12] in note
        assert (Path(src) / "code.py").read_text() == "committed\n"

    def test_untracked_src_falls_back_to_live_tree(self, git_repo: Path, tmp_path: Path):
        # np. operator-publikowane .redeploy-hashes/ — generowane, poza gitem.
        hashes = git_repo / ".redeploy-hashes"
        hashes.mkdir()
        (hashes / "scope").write_text("abc\n")
        src, note = frozen_rsync_src(
            git_repo, self._head(git_repo), ".redeploy-hashes/", tmp_path / "e2"
        )
        assert src == ".redeploy-hashes/"
        assert "nietrackowany" in note

    def test_absolute_src_falls_back_to_live_tree(self, git_repo: Path, tmp_path: Path):
        src, note = frozen_rsync_src(
            git_repo, self._head(git_repo), "/home/tom/github/oqlos/oqlos/", tmp_path / "e3"
        )
        assert src == "/home/tom/github/oqlos/oqlos/"
        assert "poza repo" in note

    def test_tracked_file_src(self, git_repo: Path, tmp_path: Path):
        head = self._head(git_repo)
        (git_repo / "app.py").write_text("WIP\n")
        src, note = frozen_rsync_src(git_repo, head, "app.py", tmp_path / "e4")
        assert not src.endswith("/")
        assert Path(src).read_text() == "v1\n"
        assert head[:12] in note


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


class TestDeployWatch:
    def test_history_estimate_and_eta(self, tmp_path):
        from redeploy.deploy_watch import StepHistory

        h = StepHistory(path=tmp_path / "h.json")
        for v in (10.0, 12.0, 200.0):
            h.record("build", v)
        h.record("sync", 2.0)
        assert h.estimate("build") == 12.0          # median, odporna na outlier
        eta = h.eta_for(["build", "sync", "unknown"])
        # unknown = mediana znanych median (sorted [2,12] → indeks 1 → 12)
        assert eta == 12.0 + 2.0 + 12.0
        h.record_total(300.0)
        h.save()
        h2 = StepHistory.load("x", tmp_path)        # inny klucz → puste
        assert h2.steps == {}

    def test_yaml_doc_stream_parser(self):
        from redeploy.deploy_watch import _iter_yaml_docs

        stream = iter([
            "---\n", "event: start\n", "total_steps: 2\n",
            "---\n", "event: step_done\n", "n: 1\n",
        ])
        docs = list(_iter_yaml_docs(stream))
        assert [d["event"] for d in docs] == ["start", "step_done"]

    def test_manifest_reports_wip(self, git_repo):
        from redeploy.deploy_watch import build_manifest

        (git_repo / "app.py").write_text("changed\n")
        m = build_manifest(git_repo)
        assert "app.py" in m.wip_files
        assert m.head and m.head != "?"

    def test_durations_come_from_engine_elapsed(self, tmp_path, monkeypatch):
        # step_start/step_done docelowo docierają potokiem niemal jednocześnie
        # (separator '---' domyka dokument dopiero przy następnym zdarzeniu) —
        # czas kroku MUSI pochodzić z elapsed_s silnika, nie z zegara odbioru.
        import redeploy.deploy_watch as dw

        class FakeProc:
            returncode = 0
            stdout = iter([
                "---\n", "event: start\n", "total_steps: 1\n",
                "steps:\n", "- {n: 1, id: build}\n",
                "---\n", "event: step_start\n", "n: 1\n", "id: build\n",
                "elapsed_s: 1.0\n",
                "---\n", "event: step_done\n", "n: 1\n", "id: build\n",
                "elapsed_s: 61.5\n",
                "---\n", "event: done\n", "steps_completed: 1\n",
            ])
            def wait(self):
                return 0

        monkeypatch.setattr(dw.subprocess, "Popen", lambda *a, **k: FakeProc())
        report = dw.run_with_progress("spec.md", tmp_path, log_dir=tmp_path)
        assert report.returncode == 0
        assert report.durations["build"] == pytest.approx(60.5)


class TestProjectHashPublisher:
    """Kokpit publikuje hashe przed silnikiem — stale hashe = fałszywy SKIP."""

    def test_found_when_project_ships_script(self, tmp_path: Path):
        from redeploy.source_hash import project_hash_publisher

        script = tmp_path / "scripts" / "redeploy" / "publish-source-hashes.sh"
        script.parent.mkdir(parents=True)
        script.write_text("#!/bin/bash\necho PASS\n")
        assert project_hash_publisher(tmp_path) == script

    def test_none_without_script(self, tmp_path: Path):
        from redeploy.source_hash import project_hash_publisher

        assert project_hash_publisher(tmp_path) is None


class TestModuleShadowCollisions:
    """Bramka wykrywa `x.py` + pakiet `x/` w commicie (incydent 2026-07-13)."""

    def test_detects_collision_in_head(self, git_repo: Path):
        from redeploy.gitsync import module_shadow_collisions

        pkg = git_repo / "shared" / "event_store"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (git_repo / "shared" / "event_store.py").write_text("class EventStore: ...\n")
        subprocess.run(["git", "-C", str(git_repo), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(git_repo), "commit", "-qm", "collision"], check=True)
        assert module_shadow_collisions(git_repo) == ["shared/event_store.py vs shared/event_store/"]

    def test_clean_tree_no_collisions(self, git_repo: Path):
        from redeploy.gitsync import module_shadow_collisions

        assert module_shadow_collisions(git_repo) == []
