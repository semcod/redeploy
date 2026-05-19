"""Markdown execution reports and post-deploy checksum verification."""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from ...observe import AuditEntry, DeployAuditLog


def default_report_path(spec_path: Path) -> Path:
    return spec_path.parent / f".{spec_path.stem}.md"


def resolve_audit_entry(migration, started_at: datetime, ok: bool) -> AuditEntry:
    log = DeployAuditLog()
    entries = log.filter(host=migration.host, app=migration.app, since=started_at)
    if entries:
        return entries[-1]

    done_count = sum(1 for s in migration.steps if str(s.status).endswith("DONE"))
    failed_count = sum(1 for s in migration.steps if str(s.status).endswith("FAILED"))
    if ok and done_count == 0 and failed_count == 0:
        done_count = len(migration.steps)

    data = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "host": migration.host,
        "app": migration.app,
        "from_strategy": migration.from_strategy.value,
        "to_strategy": migration.to_strategy.value,
        "ok": ok,
        "dry_run": False,
        "elapsed_s": 0.0,
        "steps_total": len(migration.steps),
        "steps_ok": done_count,
        "steps_failed": failed_count,
        "steps": [
            {
                "id": s.id,
                "action": s.action.value,
                "status": str(s.status).split(".")[-1].lower(),
                "result": s.result,
                "error": s.error,
            }
            for s in migration.steps
        ],
    }
    return AuditEntry(data)


def step_command_block(step) -> str:
    if step.command:
        return step.command.strip()
    if step.command_ref:
        return f"command_ref: {step.command_ref}"
    if step.action.value == "rsync":
        parts = [f"rsync {step.src or ''} -> {step.dst or ''}"]
        if step.excludes:
            parts.append("excludes:")
            parts.extend(f"- {x}" for x in step.excludes)
        return "\n".join(parts)
    if step.action.value == "scp":
        return f"scp {step.src or ''} -> {step.dst or ''}"
    if step.action.value in {"http_check", "version_check"}:
        return f"url: {step.url or ''}\nexpect: {step.expect or ''}".strip()
    return f"action: {step.action.value}"


def _skipped_checksum(
    *,
    reason: str,
    host: str,
    local_root: Path,
    remote_root: str,
) -> dict:
    return {
        "status": "skipped",
        "reason": reason,
        "host": host,
        "local_root": str(local_root),
        "remote_root": remote_root,
        "command": "(not executed)",
        "changed_paths": [],
        "changed_count": 0,
    }


def build_checksum_verification(migration, executed: bool) -> dict | None:
    """Build post-deploy sync verification with checksum-aware rsync dry-run."""
    sync_step = next((s for s in migration.steps if s.id == "sync_project_tree"), None)
    if not sync_step:
        return None

    src = (sync_step.src or "").strip()
    dst = (sync_step.dst or "").strip()
    host = (migration.host or "").strip()

    local_root = Path(src.rstrip("/")).expanduser() if src else Path.cwd()
    remote_root = dst.rstrip("/") if dst else ""

    if not executed:
        return _skipped_checksum(
            reason="plan-only run (apply not executed)",
            host=host,
            local_root=local_root,
            remote_root=remote_root,
        )

    if not host or host.lower() in {"local", "localhost", "127.0.0.1"}:
        return _skipped_checksum(
            reason="remote checksum verification requires SSH host",
            host=host,
            local_root=local_root,
            remote_root=remote_root,
        )

    if not local_root.exists() or not remote_root:
        return {
            "status": "error",
            "reason": "sync scope is incomplete (missing local or remote root)",
            "host": host,
            "local_root": str(local_root),
            "remote_root": remote_root,
            "command": "(not executed)",
            "changed_paths": [],
            "changed_count": 0,
        }

    return _run_rsync_checksum(sync_step, host, local_root, remote_root)


def _run_rsync_checksum(sync_step, host: str, local_root: Path, remote_root: str) -> dict:
    cmd = ["rsync", "-a", "-z", "--delete", "--checksum", "--dry-run", "--itemize-changes"]
    if (local_root / ".gitignore").exists():
        cmd += ["--filter=:- .gitignore"]
    if (local_root / ".redeployignore").exists():
        cmd += ["--filter=:- .redeployignore"]
    for ex in sync_step.excludes or []:
        cmd += ["--exclude", ex]
    cmd += [f"{local_root.as_posix().rstrip('/')}/", f"{host}:{remote_root.rstrip('/')}/"]

    command_preview = " ".join(cmd)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    except Exception as exc:  # pragma: no cover
        return {
            "status": "error",
            "reason": str(exc),
            "host": host,
            "local_root": str(local_root),
            "remote_root": remote_root,
            "command": command_preview,
            "changed_paths": [],
            "changed_count": 0,
        }

    return _parse_rsync_output(result, host, local_root, remote_root, command_preview)


def _parse_rsync_output(result, host: str, local_root: Path, remote_root: str, command_preview: str) -> dict:
    raw_lines = [ln.rstrip() for ln in (result.stdout or "").splitlines() if ln.strip()]
    skip_prefixes = ("sent ", "total size is ", "created directory ")
    changed_lines = [
        ln for ln in raw_lines
        if ln != "sending incremental file list"
        and not any(ln.startswith(p) for p in skip_prefixes)
    ]

    status = "match" if result.returncode == 0 and not changed_lines else "mismatch"
    reason = ""
    if result.returncode != 0:
        status = "error"
        reason = (result.stderr or "").strip() or f"rsync exited with {result.returncode}"

    return {
        "status": status,
        "reason": reason,
        "host": host,
        "local_root": str(local_root),
        "remote_root": remote_root,
        "command": command_preview,
        "changed_paths": changed_lines[:200],
        "changed_count": len(changed_lines),
    }


def _render_checksum_section(lines: list[str], checksum: dict) -> None:
    status = (checksum.get("status") or "unknown").upper()
    lines += [
        "## Sync Checksum Verification",
        "",
        "- Method: rsync --checksum --dry-run --itemize-changes",
        f"- Scope: {checksum.get('local_root', '')} -> {checksum.get('host', '')}:{checksum.get('remote_root', '')}",
        f"- Status: {status}",
        f"- Changed Paths: {checksum.get('changed_count', 0)}",
    ]
    reason = (checksum.get("reason") or "").strip()
    if reason:
        lines.append(f"- Note: {reason}")
    lines += [
        "",
        "#### Command",
        "```bash",
        checksum.get("command") or "(not executed)",
        "```",
        "",
    ]
    if checksum.get("changed_paths"):
        lines += [
            "#### Differences",
            "```text",
            "\n".join(checksum.get("changed_paths") or []),
            "```",
            "",
        ]


def render_markdown_report(
    entry: AuditEntry,
    migration,
    spec_path: Path,
    checksum: dict | None = None,
) -> str:
    by_id = {s.id: s for s in migration.steps}
    lines: list[str] = [
        f"# Redeploy Execution Report - {spec_path.name}",
        "",
        f"- Timestamp: {entry.ts}",
        f"- Spec: {spec_path}",
        f"- Host: {entry.host}",
        f"- App: {entry.app}",
        f"- Strategy: {entry.from_strategy} -> {entry.to_strategy}",
        f"- Result: {'SUCCESS' if entry.ok else 'FAILED'}",
        f"- Steps: {entry.steps_ok}/{entry.steps_total} ok",
        f"- Elapsed: {entry.elapsed_s:.1f}s",
        "",
    ]

    if checksum:
        _render_checksum_section(lines, checksum)

    lines += ["## Step Logs", ""]

    for i, step_row in enumerate(entry.steps, 1):
        sid = step_row.get("id", "")
        status = (step_row.get("status") or "").upper()
        action = step_row.get("action", "")
        model_step = by_id.get(sid)
        desc = model_step.description if model_step else ""
        cmd = step_command_block(model_step) if model_step else f"action: {action}"
        result = (step_row.get("result") or "").strip()
        error = (step_row.get("error") or "").strip()
        log_text = error or result or "(no output captured)"

        lines += [
            f"### {i}. {sid} [{status}]",
            "",
            f"- Action: {action}",
            f"- Description: {desc}",
            "",
            "#### Executed",
            "```bash",
            cmd,
            "```",
            "",
            "#### Output",
            "```text",
            log_text,
            "```",
            "",
        ]

    return "\n".join(lines)


def write_markdown_report(
    console: Console,
    migration,
    spec_path: Path,
    started_at: datetime,
    ok: bool,
    executed: bool,
    report_file: Path | None = None,
) -> None:
    entry = resolve_audit_entry(migration, started_at=started_at, ok=ok)
    checksum = build_checksum_verification(migration, executed=executed)
    out_path = report_file or default_report_path(spec_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        render_markdown_report(entry, migration, spec_path, checksum=checksum),
        encoding="utf-8",
    )
    console.print(f"[bold]report[/bold]  [dim]saved → {out_path}[/dim]")
