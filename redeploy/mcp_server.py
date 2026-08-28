"""redeploy MCP server — exposes redeploy operations via Model Context Protocol.

Transports:
  stdio  (default, for IDE/Claude Desktop integration)
  sse    (HTTP Server-Sent Events, for remote access)

Run:
  redeploy-mcp                          # stdio (for MCP clients / Claude Desktop)
  redeploy-mcp --transport sse          # SSE on http://0.0.0.0:8811
  redeploy mcp                          # via main CLI
  redeploy mcp --transport sse --port 8811

Tools exposed:
  schema          -- discover specs & workspace state
  plan_spec       -- dry-run a migration spec, return step list
  run_spec        -- apply a migration spec (with confirm option)
  fix_spec        -- self-healing deploy (bump + apply + LLM retry)
  bump_version    -- bump patch/minor/major version
  diagnose        -- run SSH diagnostics on a host
  status          -- show running containers/units on a host
  exec_ssh        -- run an ad-hoc SSH command on a known target
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "redeploy",
    instructions=(
        "redeploy is an infrastructure migration toolkit. "
        "Use schema() first to discover available specs and targets, "
        "then run plan_spec() to preview steps before applying with run_spec() or fix_spec()."
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAFE_HOST_RE = re.compile(r"^[A-Za-z0-9_.@:-]+$")
_MCP_APPLY_ENV = "REDEPLOY_MCP_ALLOW_APPLY"
_UNSAFE_SSH_TOKENS = (
    "&&",
    "||",
    ";",
    "|",
    "`",
    "$(",
    ">",
    "<",
    "\n",
    "\r",
)


def _approval_hash(action: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        {"action": action, "payload": payload},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _apply_enabled() -> bool:
    return os.getenv(_MCP_APPLY_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def _require_approval(
    action: str,
    payload: dict[str, Any],
    *,
    actor: str,
    approval_hash: str,
) -> dict[str, Any] | None:
    approved_payload = {**payload, "actor": actor.strip()}
    expected = _approval_hash(action, approved_payload)
    if _apply_enabled() and actor.strip() and approval_hash.strip() == expected:
        return None
    return {
        "success": False,
        "executed": False,
        "requires_approval": True,
        "approval_hash": expected,
        "approval_payload": payload,
        "required_env": _MCP_APPLY_ENV,
        "reason": (
            f"Enable {_MCP_APPLY_ENV}=1 and provide a non-empty actor plus the exact "
            "approval_hash for this operation"
        ),
    }


def _bounded_output(value: str, limit: int = 50_000) -> tuple[str, bool]:
    return value[:limit], len(value) > limit

def _redeploy_bin() -> str:
    """Resolve the redeploy binary path (same venv as this process)."""
    import shutil
    if sys.argv and sys.argv[0] and Path(sys.argv[0]).exists():
        return sys.argv[0]
    found = shutil.which("redeploy")
    if found:
        return found
    # fallback: python -m redeploy.cli not needed — just raise
    raise RuntimeError("Cannot locate redeploy binary")


def _run(*args: str, cwd: str | None = None, timeout: int = 120) -> dict:
    """Run a redeploy sub-command, capture stdout+stderr, return result dict."""
    cmd = [_redeploy_bin(), *args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or Path.cwd(),
            timeout=timeout,
        )
        stdout, stdout_truncated = _bounded_output(proc.stdout)
        stderr, stderr_truncated = _bounded_output(proc.stderr)
        return {
            "returncode": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "success": proc.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "Timeout", "success": False}
    except Exception as exc:
        return {"returncode": -1, "stdout": "", "stderr": str(exc), "success": False}


def _validate_exec_ssh_inputs(host: str, command: str) -> str | None:
    """Return validation error message for unsafe exec_ssh inputs, or None."""
    if not _SAFE_HOST_RE.match(host):
        return f"Unsafe host format: {host!r}"

    # Allow opting out explicitly for trusted environments.
    if os.getenv("REDEPLOY_MCP_ALLOW_UNSAFE_SSH", "").lower() in {"1", "true", "yes"}:
        return None

    for token in _UNSAFE_SSH_TOKENS:
        if token in command:
            return (
                "Unsafe command token detected "
                f"({token!r}). Set REDEPLOY_MCP_ALLOW_UNSAFE_SSH=1 to bypass explicitly."
            )
    return None


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def schema(
    directory: Annotated[str, "Workspace root directory. '.' = current working directory."] = ".",
) -> dict:
    """Discover the workspace: find migration specs, read version, git branch.

    Always call this first to know which specs are available before planning or deploying.
    Returns a JSON dict with: cwd, version, git_branch, specs[], commands{}.
    """
    from redeploy.schema import build_schema
    root = Path(directory).expanduser().resolve()
    return build_schema(root)


@mcp.tool()
def plan_spec(
    spec: Annotated[str, "Path to migration.md / migration.yaml (absolute or relative to cwd)."],
    cwd: Annotated[str, "Working directory to resolve relative paths. Default: current dir."] = ".",
) -> dict:
    """Preview a migration spec: show all steps without executing anything.

    Safe read-only operation. Use this before run_spec or fix_spec to understand
    what will happen.
    """
    result = _run("run", spec, "--dry-run", "--no-heal", cwd=cwd, timeout=30)
    return result


@mcp.tool()
def run_spec(
    spec: Annotated[str, "Path to migration.md / migration.yaml."],
    force: Annotated[bool, "Skip interactive confirmation prompt after MCP approval."] = False,
    dry_run: Annotated[bool, "If True, only show plan without applying."] = True,
    heal: Annotated[bool, "Enable LLM self-healing on step failure."] = False,
    fix_hint: Annotated[str, "Optional problem description to guide LLM healing."] = "",
    cwd: Annotated[str, "Working directory."] = ".",
    actor: Annotated[str, "Identity of the human approving an apply operation."] = "",
    approval_hash: Annotated[str, "Hash returned by the matching approval-required response."] = "",
) -> dict:
    """Apply a migration spec.

    Defaults to a dry-run. Applying requires an actor and an approval hash bound
    to the exact spec, workspace and execution options.
    """
    approval_payload = {
        "spec": spec,
        "cwd": str(Path(cwd).expanduser().resolve()),
        "force": force,
        "heal": heal,
        "fix_hint": fix_hint,
    }
    if not dry_run:
        required = _require_approval(
            "redeploy_run_spec",
            approval_payload,
            actor=actor,
            approval_hash=approval_hash,
        )
        if required:
            return required

    args = ["run", spec]
    if force:
        args.append("--force")
    if dry_run:
        args.append("--dry-run")
    if not heal:
        args.append("--no-heal")
    if fix_hint:
        args += ["--fix", fix_hint]
    return _run(*args, cwd=cwd, timeout=600)


@mcp.tool()
def fix_spec(
    spec_or_dir: Annotated[str, "Path to spec file or project directory (e.g. '.' or 'redeploy/pi109/migration.md')."],
    hint: Annotated[str, "Describe the problem to fix, e.g. 'service not starting', 'brak ikon SVG'."] = "",
    bump: Annotated[bool, "Bump version before deploying."] = False,
    retries: Annotated[int, "Max LLM self-healing retries."] = 3,
    dry_run: Annotated[bool, "Plan only, do not apply."] = True,
    cwd: Annotated[str, "Working directory."] = ".",
    actor: Annotated[str, "Identity of the human approving an apply operation."] = "",
    approval_hash: Annotated[str, "Hash returned by the matching approval-required response."] = "",
) -> dict:
    """Self-healing deploy: bump version → apply spec → LLM retry on failure.

    This is the main 'smart deploy' command. It bumps the version, applies the
    migration, and if a step fails, asks an LLM to suggest a fix and retries.
    """
    retry_limit = max(0, min(int(retries), 10))
    approval_payload = {
        "spec_or_dir": spec_or_dir,
        "hint": hint,
        "bump": bump,
        "retries": retry_limit,
        "cwd": str(Path(cwd).expanduser().resolve()),
    }
    if not dry_run:
        required = _require_approval(
            "redeploy_fix_spec",
            approval_payload,
            actor=actor,
            approval_hash=approval_hash,
        )
        if required:
            return required

    args = ["fix", spec_or_dir]
    if hint:
        args += ["--hint", hint]
    if not bump:
        args.append("--no-bump")
    args += ["--retries", str(retry_limit)]
    if dry_run:
        args.append("--dry-run")
    return _run(*args, cwd=cwd, timeout=900)


@mcp.tool()
def bump_version(
    spec_or_dir: Annotated[str, "Path to spec or project directory."] = ".",
    level: Annotated[str, "Version component to bump: 'patch' (default), 'minor', 'major'."] = "patch",
    cwd: Annotated[str, "Working directory."] = ".",
    apply: Annotated[bool, "Apply the version change after approval."] = False,
    actor: Annotated[str, "Identity of the human approving the version change."] = "",
    approval_hash: Annotated[str, "Hash returned by the matching approval-required response."] = "",
) -> dict:
    """Bump the project version and update migration spec header.

    Updates VERSION file and all version references in the migration spec
    (version: field, name: and description: fields containing vX.Y.Z).
    """
    normalized_level = level if level in {"patch", "minor", "major"} else "patch"
    approval_payload = {
        "spec_or_dir": spec_or_dir,
        "level": normalized_level,
        "cwd": str(Path(cwd).expanduser().resolve()),
    }
    if not apply:
        return _require_approval(
            "redeploy_bump_version", approval_payload, actor=actor, approval_hash=""
        ) or {}
    required = _require_approval(
        "redeploy_bump_version",
        approval_payload,
        actor=actor,
        approval_hash=approval_hash,
    )
    if required:
        return required

    args = ["bump", spec_or_dir]
    if normalized_level == "minor":
        args.append("--minor")
    elif normalized_level == "major":
        args.append("--major")
    return _run(*args, cwd=cwd, timeout=10)


@mcp.tool()
def diagnose(
    host: Annotated[str, "SSH target, e.g. 'pi@192.168.188.109'."],
) -> dict:
    """Run SSH diagnostics on a deployment target and return system state.

    Checks: running containers, open ports, systemd unit status, recent logs.
    """
    return _run("diagnose", host, timeout=60)


@mcp.tool()
def list_specs(
    directory: Annotated[str, "Root directory to search for migration specs."] = ".",
    limit: Annotated[int, "Maximum number of specs returned (1-500)."] = 100,
) -> list[dict]:
    """List all migration specs found in a directory.

    Returns a list of {path, name, version, target, description} dicts.
    Use this for a quick overview without the full command catalogue.
    """
    from redeploy.schema import build_schema
    root = Path(directory).expanduser().resolve()
    s = build_schema(root)
    result_limit = max(1, min(int(limit), 500))
    return s.get("specs", [])[:result_limit]


@mcp.tool()
def exec_ssh(
    host: Annotated[str, "SSH target, e.g. 'pi@192.168.188.109'."],
    command: Annotated[str, "Shell command to run on the remote host."],
    execute: Annotated[bool, "Execute after actor-bound approval; false returns an approval plan."] = False,
    actor: Annotated[str, "Identity of the human approving the command."] = "",
    approval_hash: Annotated[str, "Hash returned by the matching approval-required response."] = "",
) -> dict:
    """Run an ad-hoc SSH command on a remote host.

    Returns stdout, stderr and return code.
    CAUTION: this executes arbitrary commands — confirm with user before use.
    """
    validation_error = _validate_exec_ssh_inputs(host, command)
    if validation_error:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": validation_error,
            "success": False,
        }

    approval_payload = {"host": host, "command": command}
    required = _require_approval(
        "redeploy_exec_ssh",
        approval_payload,
        actor=actor,
        approval_hash=approval_hash if execute else "",
    )
    if required:
        return required

    try:
        proc = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", host, command],
            capture_output=True, text=True, timeout=60,
        )
        stdout, stdout_truncated = _bounded_output(proc.stdout)
        stderr, stderr_truncated = _bounded_output(proc.stderr)
        return {
            "returncode": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "success": proc.returncode == 0,
            "approved_by": actor.strip(),
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "SSH timeout", "success": False}
    except Exception as exc:
        return {"returncode": -1, "stdout": "", "stderr": str(exc), "success": False}


@mcp.tool()
def nlp_command(
    instruction: Annotated[str, "Natural language instruction, e.g. 'deploy c2004 to pi109' or 'pokaż plan deployu'."],
    dry_run: Annotated[bool, "Force dry-run on the generated command."] = True,
    cwd: Annotated[str, "Working directory for spec discovery."] = ".",
    actor: Annotated[str, "Identity of the human approving generated-command execution."] = "",
    approval_hash: Annotated[str, "Hash returned by the matching approval-required response."] = "",
) -> dict:
    """Translate a natural-language instruction into a redeploy command and run it.

    Uses an LLM (via redeploy prompt) to map the instruction to a CLI command.
    Set dry_run=True to generate the command without executing it.

    Returns: {command: str, stdout: str, stderr: str, returncode: int}
    """
    approval_payload = {
        "instruction": instruction,
        "cwd": str(Path(cwd).expanduser().resolve()),
    }
    if not dry_run:
        required = _require_approval(
            "redeploy_nlp_command",
            approval_payload,
            actor=actor,
            approval_hash=approval_hash,
        )
        if required:
            return required

    args = ["prompt", instruction]
    if dry_run:
        args += ["--dry-run"]
    args += ["--yes"]  # non-interactive when called from MCP
    result = _run(*args, cwd=cwd, timeout=120)
    return result


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@mcp.resource("redeploy://spec/{path}")
def get_spec_content(path: str) -> str:
    """Read the raw content of a migration spec file.

    URI example: redeploy://spec/redeploy/pi109/migration.md
    """
    root = Path.cwd().resolve()
    candidate = Path(path).expanduser()
    p = (candidate if candidate.is_absolute() else root / candidate).resolve()
    try:
        p.relative_to(root)
    except ValueError:
        return f"# Error\nSpec path escapes workspace: {path}"
    if not p.is_file():
        return f"# Error\nSpec not found: {path}"
    content = p.read_text()
    bounded, truncated = _bounded_output(content)
    return bounded + ("\n\n# Truncated by MCP response limit" if truncated else "")


@mcp.resource("redeploy://workspace")
def get_workspace() -> str:
    """Return the workspace schema as JSON string."""
    import json
    from redeploy.schema import build_schema
    return json.dumps(build_schema(), indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def serve(transport: str = "stdio", host: str = "0.0.0.0", port: int = 8811) -> None:
    """Start the MCP server.

    Parameters
    ----------
    transport : 'stdio' | 'sse' | 'streamable-http'
    host      : bind host for SSE/HTTP transports
    port      : bind port for SSE/HTTP transports
    """
    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "sse":
        import uvicorn
        app = mcp.sse_app()
        uvicorn.run(app, host=host, port=port)
    elif transport in ("http", "streamable-http"):
        import uvicorn
        app = mcp.streamable_http_app()
        uvicorn.run(app, host=host, port=port)
    else:
        raise ValueError(f"Unknown transport: {transport!r}. Choose: stdio | sse | http")


if __name__ == "__main__":
    serve()
