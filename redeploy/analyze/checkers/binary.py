"""Local binary availability checks for shell commands."""
from __future__ import annotations

import re
import shlex
import shutil

from ..models import AnalysisResult, IssueSeverity
from .base import Checker

_WRAPPERS = frozenset({"sudo", "env", "command", "nohup", "time", "exec"})
_KEYWORDS = frozenset({
    "if", "then", "else", "fi", "for", "do", "done", "while", "case", "esac",
    "function", "in", "until", "select", "echo", "true", "false", "test", "[", "[[",
})
_SEPARATORS = frozenset({"&&", "||", "|", ";", "(", ")", "{", "}"})


def extract_binaries(cmd: str) -> list[str]:
    try:
        tokens = shlex.split(cmd, posix=True)
    except ValueError:
        tokens = cmd.split()

    out: list[str] = []
    expect_cmd = True
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in _SEPARATORS:
            expect_cmd = True
            i += 1
            continue
        if expect_cmd:
            if tok in _KEYWORDS or tok.startswith("$"):
                if tok == "for":
                    i += 1
                i += 1
                expect_cmd = False
                continue
            if "=" in tok and not tok.startswith("--") and "/" not in tok:
                i += 1
                continue
            if tok in _WRAPPERS:
                i += 1
                continue
            if re.match(r"^[a-zA-Z_][a-zA-Z0-9_.-]*$", tok) and len(tok) > 1:
                out.append(tok)
            expect_cmd = False
        i += 1
    return out


class BinaryChecker(Checker):
    """Warn if commands reference binaries not available locally (best-effort)."""

    def check(self, spec, document, base_dir, result):
        for step in spec.extra_steps:
            action = str(step.get("action") or "")
            if action in {"ensure_kanshi_profile"}:
                continue
            cmd = step.get("command") or ""
            for binary in extract_binaries(cmd):
                if shutil.which(binary) is None:
                    result.add(
                        IssueSeverity.WARNING,
                        "binaries",
                        f"Step '{step.get('id')}' command uses binary not found locally: '{binary}'",
                        step.get("id"),
                        suggestion=(
                            f"Install '{binary}' locally for lint parity, or ignore if it "
                            "exists only on remote host."
                        ),
                    )
