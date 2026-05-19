"""command_ref dependency validation."""
from __future__ import annotations

from pathlib import Path

from ..models import AnalysisResult, IssueSeverity
from .base import Checker
from .path import resolve_local_path


class CommandRefChecker(Checker):
    """Validate command_ref references for nested markdown/script dependencies."""

    def check(self, spec, document, base_dir, result):
        from ...markpact.parser import resolve_script_ref

        in_doc_refs: set[str] = set()
        if document:
            for block in document.blocks:
                if block.kind == "ref" and block.ref_id:
                    in_doc_refs.add(block.ref_id)

        for step in spec.extra_steps:
            sid = step.get("id")
            cref = step.get("command_ref")
            if not cref:
                continue

            if "#" in cref:
                self._check_external_ref(cref, sid, base_dir, document, in_doc_refs, result)
                continue

            if document and cref not in in_doc_refs:
                result.add(
                    IssueSeverity.WARNING,
                    "command_ref",
                    f"Step '{sid}' references unknown command_ref '{cref}'",
                    sid,
                    suggestion="Define a matching markpact:ref block in this spec.",
                )

    def _check_external_ref(
        self,
        cref: str,
        sid: str | None,
        base_dir: Path,
        document,
        in_doc_refs: set[str],
        result: AnalysisResult,
    ) -> None:
        from ...markpact.parser import resolve_script_ref

        file_part, ref_id = cref.split("#", 1)
        if file_part:
            file_path = resolve_local_path(file_part, base_dir)
            if not file_path.exists():
                result.add(
                    IssueSeverity.ERROR,
                    "command_ref",
                    f"Step '{sid}' command_ref file missing: {file_part}",
                    sid,
                    suggestion=f"Create or fix path: {file_path}",
                )
                return
            text = file_path.read_text(encoding="utf-8", errors="replace")
            if resolve_script_ref(text, ref_id, language="bash") is None:
                result.add(
                    IssueSeverity.ERROR,
                    "command_ref",
                    f"Step '{sid}' command_ref '#{ref_id}' not found in {file_part}",
                    sid,
                    suggestion="Add a matching markpact:ref bash block or section heading script.",
                )
            return

        if document and ref_id not in in_doc_refs:
            result.add(
                IssueSeverity.WARNING,
                "command_ref",
                f"Step '{sid}' command_ref '#{ref_id}' not found as markpact:ref in current spec",
                sid,
                suggestion="If this is a heading-based script, keep as-is; otherwise add markpact:ref block.",
            )
