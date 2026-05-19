"""Audit a target host against a migration spec.

Given a `MigrationSpec` (loaded from YAML or markpact MD), derive the set of
expectations the spec implies for the target host (binaries, files, ports,
disk space, container images, systemd units, env files, …) and probe the
target via SSH to report what is **missing** or out of spec.

This is non-destructive: it never executes any spec command — only read-only
inspection commands.

Public entrypoints:
    - ``Auditor`` — the analyzer class
    - ``audit_spec(path, host=None)`` — convenience wrapper
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..spec_loader import load_migration_spec
from .auditor import Auditor
from .extractor import Extractor
from .models import AuditCheck, AuditReport
from .paths import extract_port

# Backward-compatible private aliases used in tests and internal callers.
_Extractor = Extractor
_extract_port = extract_port


def audit_spec(
    spec_path: str | Path,
    *,
    host: Optional[str] = None,
    ssh_key: Optional[str] = None,
) -> AuditReport:
    """Convenience: load spec from file and run an audit."""
    spec = load_migration_spec(spec_path)
    return Auditor(spec, spec_path=spec_path, host=host, ssh_key=ssh_key).run()


__all__ = [
    "AuditCheck",
    "AuditReport",
    "Auditor",
    "Extractor",
    "audit_spec",
    "extract_port",
    "_Extractor",
    "_extract_port",
]
