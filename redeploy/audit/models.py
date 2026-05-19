"""Audit result types and internal expectation records."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AuditCheck:
    """Outcome of a single audit probe."""
    category: str
    name: str
    status: str
    detail: str = ""
    fix_hint: str = ""
    source_step: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "pass"


@dataclass
class AuditReport:
    spec_path: str
    host: str
    target_strategy: str
    checks: list[AuditCheck] = field(default_factory=list)

    def add(self, check: AuditCheck) -> None:
        self.checks.append(check)

    @property
    def passed(self) -> list[AuditCheck]:
        return [c for c in self.checks if c.status == "pass"]

    @property
    def failed(self) -> list[AuditCheck]:
        return [c for c in self.checks if c.status == "fail"]

    @property
    def warned(self) -> list[AuditCheck]:
        return [c for c in self.checks if c.status == "warn"]

    @property
    def skipped(self) -> list[AuditCheck]:
        return [c for c in self.checks if c.status == "skip"]

    @property
    def ok(self) -> bool:
        return not self.failed

    def summary(self) -> str:
        return (
            f"Audit: {len(self.passed)}/{len(self.checks)} passed, "
            f"{len(self.failed)} missing, {len(self.warned)} warnings, "
            f"{len(self.skipped)} skipped"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec": self.spec_path,
            "host": self.host,
            "target_strategy": self.target_strategy,
            "ok": self.ok,
            "summary": self.summary(),
            "checks": [c.__dict__ for c in self.checks],
        }


@dataclass(frozen=True)
class Expect:
    category: str
    name: str
    source_step: str = ""
    fix_hint: str = ""
    extra: tuple[tuple[str, str], ...] = ()

    @property
    def extras(self) -> dict[str, str]:
        return dict(self.extra)
