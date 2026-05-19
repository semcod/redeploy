"""Static analysis engine for migration specs."""
from __future__ import annotations

from pathlib import Path

from ..markpact.models import MarkpactDocument
from ..models.spec import MigrationSpec
from .checkers import (
    BinaryChecker,
    CommandPathChecker,
    CommandRefChecker,
    ComposeChecker,
    DockerBuildChecker,
    EnvFileChecker,
    PathChecker,
    ReferenceChecker,
)
from .ignore import IgnoreList as _IgnoreList, ensure_redeployignore
from .models import AnalysisResult, Issue, IssueSeverity

# Re-export for backward compatibility (tests and external imports).
from .checkers import (  # noqa: F401
    _BinaryChecker,
    _CommandPathChecker,
    _CommandRefChecker,
    _ComposeChecker,
    _DockerBuildChecker,
    _EnvFileChecker,
    _PathChecker,
    _ReferenceChecker,
)


class SpecAnalyzer:
    """Run static checks against a compiled MigrationSpec (and optional raw MarkpactDocument)."""

    DEFAULT_CHECKERS = [
        PathChecker(),
        CommandPathChecker(),
        DockerBuildChecker(),
        CommandRefChecker(),
        ReferenceChecker(),
        ComposeChecker(),
        EnvFileChecker(),
        BinaryChecker(),
    ]

    def __init__(
        self,
        base_dir: Path | None = None,
        checkers=None,
        auto_create_redeployignore: bool = True,
    ):
        self.base_dir = base_dir or Path.cwd()
        self.checkers = checkers or list(self.DEFAULT_CHECKERS)
        self.auto_create_redeployignore = auto_create_redeployignore

    def analyze(
        self,
        spec: MigrationSpec,
        document: MarkpactDocument | None = None,
    ) -> AnalysisResult:
        result = AnalysisResult()
        for checker in self.checkers:
            checker.check(spec, document, self.base_dir, result)
        return result

    def analyze_file(self, spec_path: Path) -> tuple[MigrationSpec | None, AnalysisResult]:
        """Load spec from file (YAML or markpact) and analyze."""
        from ..markpact.parser import parse_markpact_file
        from ..markpact.compiler import compile_markpact_document, MarkpactCompileError
        from ..models.spec import MigrationSpec as MS

        if self.auto_create_redeployignore:
            ensure_redeployignore(self.base_dir)

        document = None
        spec = None
        result = AnalysisResult()

        if spec_path.suffix == ".md":
            try:
                document = parse_markpact_file(spec_path)
                spec = compile_markpact_document(document)
            except MarkpactCompileError as exc:
                result.add(IssueSeverity.ERROR, "compile", str(exc))
                return None, result
            except Exception as exc:
                result.add(IssueSeverity.ERROR, "compile", f"Failed to parse markpact: {exc}")
                return None, result
        else:
            try:
                spec = MS.from_file(spec_path)
            except Exception as exc:
                result.add(IssueSeverity.ERROR, "load", f"Failed to load spec: {exc}")
                return None, result

        if spec:
            result = self.analyze(spec, document)
        return spec, result


__all__ = [
    "SpecAnalyzer",
    "AnalysisResult",
    "Issue",
    "IssueSeverity",
    "ensure_redeployignore",
    "_IgnoreList",
    "_PathChecker",
    "_CommandPathChecker",
    "_ReferenceChecker",
    "_ComposeChecker",
    "_DockerBuildChecker",
    "_CommandRefChecker",
    "_EnvFileChecker",
    "_BinaryChecker",
]
