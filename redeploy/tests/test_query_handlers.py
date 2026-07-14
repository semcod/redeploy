"""Tests for query-language post-deploy test handlers: testql / oql / aql."""
from __future__ import annotations

import pytest

from redeploy.apply.exceptions import StepError
from redeploy.apply.handlers import (
    _parse_oql_verdict,
    run_aql,
    run_oql,
    run_testql,
)
from redeploy.models import MigrationStep, StepAction, StepStatus


def _step(action: StepAction, **kw) -> MigrationStep:
    return MigrationStep(id="t", action=action, description="d", **kw)


# ── _parse_oql_verdict ────────────────────────────────────────────────────────

def test_oql_verdict_ok_json():
    ok, detail = _parse_oql_verdict('{"ok": true, "errors": []}', 0)
    assert ok is True and "ok=true" in detail


def test_oql_verdict_fail_json():
    ok, detail = _parse_oql_verdict('{"ok": false, "errors": ["boom"]}', 1)
    assert ok is False and "boom" in detail


def test_oql_verdict_json_on_last_line():
    ok, _ = _parse_oql_verdict('noise line\n{"ok": true, "errors": []}', 0)
    assert ok is True


def test_oql_verdict_no_json_falls_back_to_exit_code():
    assert _parse_oql_verdict("garbage", 0)[0] is True
    assert _parse_oql_verdict("garbage", 1)[0] is False


# ── run_testql ────────────────────────────────────────────────────────────────

def test_testql_pass_via_command_override():
    s = _step(StepAction.TESTQL, query_source="s.testql", url="http://h:8100", command="true")
    run_testql(s, None)
    assert s.status == StepStatus.DONE


def test_testql_fail_raises():
    s = _step(StepAction.TESTQL, query_source="s.testql", command="false")
    with pytest.raises(StepError):
        run_testql(s, None)


def test_testql_expect_not_found_fails():
    s = _step(StepAction.TESTQL, query_source="s.testql", expect="ALLGOOD", command="echo nope")
    with pytest.raises(StepError):
        run_testql(s, None)


def test_testql_requires_source_or_command():
    with pytest.raises(StepError):
        run_testql(_step(StepAction.TESTQL), None)


def test_placeholder_substitution_not_str_format():
    # {url}/{source} are replaced; literal braces in output must survive.
    s = _step(StepAction.TESTQL, url="http://H:9", query_source="SRC",
              command="echo url={url} src={source} lit={not_a_ph}")
    run_testql(s, None)
    assert s.status == StepStatus.DONE  # {not_a_ph} left as-is, echo still exits 0


# ── run_oql ───────────────────────────────────────────────────────────────────

def test_oql_pass_from_ok_json():
    s = _step(StepAction.OQL, query_source="s.oql", url="http://h:8202",
              command="printf %s '{\"ok\": true, \"errors\": []}'")
    run_oql(s, None)
    assert s.status == StepStatus.DONE


def test_oql_fail_from_ok_false():
    s = _step(StepAction.OQL, query_source="s.oql",
              command="printf %s '{\"ok\": false, \"errors\": [\"x\"]}'")
    with pytest.raises(StepError):
        run_oql(s, None)


# ── run_aql ───────────────────────────────────────────────────────────────────

def test_aql_pass_with_expected_variant():
    s = _step(StepAction.AQL, query_source="m.aql", expect="technical_deep",
              command="echo variant technical_deep")
    run_aql(s, None)
    assert s.status == StepStatus.DONE


def test_aql_fail_when_variant_missing():
    s = _step(StepAction.AQL, query_source="m.aql", expect="technical_deep",
              command="echo variant default")
    with pytest.raises(StepError):
        run_aql(s, None)


def test_runner_not_found_raises_steperror():
    s = _step(StepAction.TESTQL, query_source="s.testql", query_runner="definitely-not-a-binary-xyz")
    with pytest.raises(StepError):
        run_testql(s, None)
