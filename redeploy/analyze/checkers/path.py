"""Path existence checkers for migration specs."""
from __future__ import annotations

import re
from pathlib import Path

from ..ignore import IgnoreList
from ..models import AnalysisResult, IssueSeverity
from .base import Checker


def resolve_local_path(val: str, base_dir: Path) -> Path | None:
    val = val.strip().rstrip("/")
    if val.startswith("~/"):
        return Path.home() / val[2:]
    if val.startswith("/"):
        return Path(val)
    return base_dir / val


def is_inside(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


class PathChecker(Checker):
    """Validate local file paths referenced by steps."""

    def check(self, spec, document, base_dir, result):
        ign = IgnoreList(base_dir)
        for step in spec.extra_steps:
            self._check_field(step, "src", base_dir, result, ign)
            self._check_field(step, "dst", base_dir, result, ign)
            self._check_field(step, "config_file", base_dir, result, ign)

    def _check_field(
        self, step: dict, field_name: str, base_dir: Path,
        result: AnalysisResult, ign: IgnoreList,
    ) -> None:
        val = step.get(field_name)
        if not val:
            return
        if re.search(r"^[\w.-]+@", str(val)):
            return
        if field_name == "dst" and str(val).startswith("~/"):
            return
        path = resolve_local_path(str(val), base_dir)
        if path and not path.exists():
            try:
                rel = path.resolve().relative_to(base_dir.resolve())
                if ign.is_ignored(rel):
                    return
            except ValueError:
                pass
            result.add(
                IssueSeverity.ERROR, "paths",
                f"Step '{step.get('id')}' references missing {field_name}: {val}",
                step.get("id"),
                suggestion=f"Create file/dir or correct path: {path}",
            )


class CommandPathChecker(Checker):
    """Scan command strings for hardcoded absolute paths outside the project."""

    EXTERNAL_RE = re.compile(r"(?:^|\s)(/home/\w+/[^\s'\"]+|~/[^\s'\"]+)")

    def check(self, spec, document, base_dir, result):
        for step in spec.extra_steps:
            cmd = step.get("command") or ""
            for match in self.EXTERNAL_RE.finditer(cmd):
                path_str = match.group(1)
                if path_str.startswith("~/"):
                    continue
                resolved = resolve_local_path(path_str, base_dir)
                if resolved and is_inside(resolved, base_dir):
                    continue
                if resolved and not resolved.exists():
                    result.add(
                        IssueSeverity.ERROR, "commands",
                        f"Step '{step.get('id')}' command references missing external path: {path_str}",
                        step.get("id"),
                        suggestion="Add rsync/scp step to sync this dependency, or correct the path.",
                    )
                else:
                    result.add(
                        IssueSeverity.WARNING, "commands",
                        f"Step '{step.get('id')}' command references external path: {path_str}",
                        step.get("id"),
                        suggestion="Consider adding an explicit sync step for this dependency.",
                    )
