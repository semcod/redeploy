"""Base class for static spec checkers."""
from __future__ import annotations

from pathlib import Path

from ..models import AnalysisResult
from ...markpact.models import MarkpactDocument
from ...models.spec import MigrationSpec


class Checker:
    def check(
        self,
        spec: MigrationSpec,
        document: MarkpactDocument | None,
        base_dir: Path,
        result: AnalysisResult,
    ) -> None:
        raise NotImplementedError
