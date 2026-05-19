"""Docker Compose static validation."""
from __future__ import annotations

from pathlib import Path

import yaml

from ..ignore import IgnoreList
from ..models import AnalysisResult, IssueSeverity
from .base import Checker


def _is_ignored(check_path: Path, base_dir: Path, ign: IgnoreList) -> bool:
    try:
        rel = check_path.resolve().relative_to(base_dir.resolve())
        return ign.is_ignored(rel)
    except ValueError:
        return False


def _check_build_section(
    svc_name: str,
    svc: dict,
    base_dir: Path,
    result: AnalysisResult,
    ign: IgnoreList,
) -> None:
    build = svc.get("build")
    if not isinstance(build, dict):
        return
    ctx = build.get("context", ".")
    ctx_path = base_dir / ctx if not str(ctx).startswith("/") else Path(ctx)
    if not ctx_path.exists():
        result.add(
            IssueSeverity.ERROR, "compose",
            f"Service '{svc_name}' build.context missing: {ctx}",
            suggestion=f"Create directory {ctx_path} or fix context.",
        )
    dockerfile = build.get("dockerfile")
    if not dockerfile:
        return
    df_path = ctx_path / dockerfile
    if not df_path.exists() and not _is_ignored(df_path, base_dir, ign):
        result.add(
            IssueSeverity.ERROR, "compose",
            f"Service '{svc_name}' Dockerfile missing: {df_path}",
            suggestion=f"Create {df_path} or correct dockerfile path.",
        )


def _check_env_files(
    svc_name: str,
    svc: dict,
    base_dir: Path,
    result: AnalysisResult,
    ign: IgnoreList,
) -> None:
    env_files = svc.get("env_file", [])
    if isinstance(env_files, str):
        env_files = [env_files]
    for ef in env_files:
        ef_path = base_dir / ef if not str(ef).startswith("/") else Path(ef)
        if not ef_path.exists() and not _is_ignored(ef_path, base_dir, ign):
            result.add(
                IssueSeverity.WARNING, "compose",
                f"Service '{svc_name}' env_file missing: {ef}",
                suggestion=f"Create {ef_path} or remove env_file entry.",
            )


def _check_volumes(
    svc_name: str,
    svc: dict,
    base_dir: Path,
    result: AnalysisResult,
    ign: IgnoreList,
) -> None:
    for vol in svc.get("volumes", []):
        if not isinstance(vol, str) or ":" not in vol:
            continue
        host_part = vol.split(":", 1)[0]
        if host_part.startswith("/"):
            if not Path(host_part).exists() and not _is_ignored(Path(host_part), base_dir, ign):
                result.add(
                    IssueSeverity.WARNING, "compose",
                    f"Service '{svc_name}' volume host path missing: {host_part}",
                    suggestion="Ensure host path exists before deployment.",
                )
        elif host_part != "." and "/" in host_part:
            hp = base_dir / host_part
            if not hp.exists() and not _is_ignored(hp, base_dir, ign):
                result.add(
                    IssueSeverity.WARNING, "compose",
                    f"Service '{svc_name}' relative volume path missing: {hp}",
                    suggestion=f"Create {hp} or mount as named volume.",
                )


def scan_compose_file(
    path: Path,
    base_dir: Path,
    result: AnalysisResult,
    ign: IgnoreList,
) -> None:
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except Exception as exc:
        result.add(IssueSeverity.ERROR, "compose", f"Cannot parse {path}: {exc}")
        return

    for svc_name, svc in (data.get("services") or {}).items():
        if not isinstance(svc, dict):
            continue
        _check_build_section(svc_name, svc, base_dir, result, ign)
        _check_env_files(svc_name, svc, base_dir, result, ign)
        _check_volumes(svc_name, svc, base_dir, result, ign)


class ComposeChecker(Checker):
    """Validate docker-compose files declared in spec or found in project."""

    def check(self, spec, document, base_dir, result):
        ign = IgnoreList(base_dir)
        compose_files = list(spec.target.compose_files or [])
        if not compose_files:
            for candidate in (
                "docker-compose.yml", "docker-compose.yaml",
                "compose.yml", "compose.yaml",
            ):
                if (base_dir / candidate).exists():
                    compose_files.append(candidate)
                    break

        for cf in compose_files:
            path = base_dir / cf
            if not path.exists():
                result.add(
                    IssueSeverity.ERROR, "compose",
                    f"Declared compose file not found: {cf}",
                    suggestion=f"Create {path} or remove from target.compose_files.",
                )
                continue
            scan_compose_file(path, base_dir, result, ign)
