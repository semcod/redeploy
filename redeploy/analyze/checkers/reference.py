"""Reference integrity checkers for migration specs."""
from __future__ import annotations

from ..models import AnalysisResult, IssueSeverity
from .base import Checker


class ReferenceChecker(Checker):
    """Ensure command_ref and insert_before point to existing things."""

    def check(self, spec, document, base_dir, result):
        from redeploy.steps import StepLibrary

        step_ids = {s.get("id") for s in spec.extra_steps if s.get("id")}
        step_ids |= set(StepLibrary.list())
        ref_ids: set[str] = set()
        if document:
            for block in document.blocks:
                if block.kind == "ref" and block.ref_id:
                    ref_ids.add(block.ref_id)

        for step in spec.extra_steps:
            sid = step.get("id")
            cref = step.get("command_ref")
            if cref and cref not in ref_ids:
                result.add(
                    IssueSeverity.ERROR, "references",
                    f"Step '{sid}' references unknown command_ref '{cref}'",
                    sid,
                    suggestion=f"Define a ```bash markpact:ref {cref} block or remove command_ref.",
                )
            ib = step.get("insert_before")
            if ib and ib not in step_ids:
                result.add(
                    IssueSeverity.WARNING, "references",
                    f"Step '{sid}' insert_before points to unknown step '{ib}'",
                    sid,
                    suggestion="This may be a runtime-generated step; verify the generated plan.",
                )
