"""Environment file checkers."""
from __future__ import annotations

from pathlib import Path

from ..models import AnalysisResult, IssueSeverity
from .base import Checker


class EnvFileChecker(Checker):
    """Check that .env referenced by target.env_file exists."""

    def check(self, spec, document, base_dir, result):
        ef = spec.target.env_file or spec.source.env_file
        if not ef:
            return
        path = base_dir / ef if not ef.startswith("/") else Path(ef)
        if not path.exists():
            result.add(
                IssueSeverity.ERROR, "env",
                f"env_file not found: {ef}",
                suggestion=f"Create {path} or correct env_file path.",
            )
