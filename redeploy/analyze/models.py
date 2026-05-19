"""Static analysis result types."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class IssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Issue:
    severity: IssueSeverity
    category: str
    step_id: str | None
    message: str
    suggestion: str | None = None
    line: int | None = None


@dataclass
class AnalysisResult:
    issues: list[Issue] = field(default_factory=list)
    passed: bool = True

    def add(
        self,
        severity: IssueSeverity,
        category: str,
        message: str,
        step_id: str | None = None,
        suggestion: str | None = None,
        line: int | None = None,
    ) -> None:
        self.issues.append(
            Issue(severity, category, step_id, message, suggestion, line)
        )
        if severity == IssueSeverity.ERROR:
            self.passed = False

    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == IssueSeverity.ERROR]

    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == IssueSeverity.WARNING]
