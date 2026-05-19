"""Docker build command static validation."""
from __future__ import annotations

import re
from pathlib import Path

from ..models import AnalysisResult, IssueSeverity
from .base import Checker

DOCKER_BUILD_RE = re.compile(r"docker\s+(?:buildx\s+)?build\s+")
FILE_FLAG_RE = re.compile(r"-f\s+(\S+)|--file[=\s]+(\S+)")
STANDARD_DOCKERFILES = frozenset({
    "Dockerfile", "dockerfile", "Dockerfile.prod", "Dockerfile.dev",
})


def collect_sync_mappings(spec) -> tuple[set[str], list[tuple[str, str]]]:
    sync_dests: set[str] = set()
    sync_mappings: list[tuple[str, str]] = []
    for step in spec.extra_steps:
        sid = step.get("id", "")
        if not str(sid).startswith("sync_"):
            continue
        dst = step.get("dst", "")
        src = step.get("src", "")
        if dst:
            sync_dests.add(dst.rstrip("/"))
            if src:
                sync_mappings.append((dst.rstrip("/"), src))
    return sync_dests, sync_mappings


def parse_docker_build(cmd: str) -> tuple[str | None, str]:
    dockerfile = None
    for match in FILE_FLAG_RE.finditer(cmd):
        dockerfile = match.group(1) or match.group(2)
        break

    tokens = cmd.split()
    context = "."
    i = len(tokens) - 1
    while i > 0:
        token = tokens[i]
        if token.startswith("-"):
            i -= 1
            continue
        if i > 0 and tokens[i - 1] in ("-f", "--file"):
            i -= 2
            continue
        if i > 0 and tokens[i - 1].startswith("--file="):
            i -= 1
            continue
        context = token
        break
        i -= 1
    return dockerfile, context


def match_local_src(
    sync_mappings: list[tuple[str, str]], remote_context: str,
) -> str | None:
    for remote_dst, local_src in sync_mappings:
        if not remote_dst.startswith("~/"):
            continue
        dst_clean = remote_dst.rstrip("/")
        if remote_context == dst_clean or remote_context.startswith(dst_clean + "/"):
            return local_src
    return None


def resolve_local_dockerfile(local_src: str, dockerfile: str, base_dir: Path) -> Path | None:
    src_path = Path(local_src.rstrip("/"))
    if not src_path.is_absolute():
        src_path = (base_dir / src_path).resolve()
    if dockerfile.startswith("/"):
        return Path(dockerfile)
    return src_path / dockerfile


class DockerBuildChecker(Checker):
    """Validate docker build commands: Dockerfile exists, context is consistent."""

    def check(self, spec, document, base_dir, result):
        sync_dests, sync_mappings = collect_sync_mappings(spec)

        for step in spec.extra_steps:
            cmd = step.get("command", "")
            if not DOCKER_BUILD_RE.search(cmd):
                continue
            sid = step.get("id", "unknown")
            dockerfile, context = parse_docker_build(cmd)
            self._check_dockerfile(dockerfile, sid, base_dir, result)
            if context.startswith("~/"):
                self._check_remote_context(
                    context, dockerfile, sid, sync_dests, sync_mappings,
                    base_dir, result,
                )

    def _check_dockerfile(
        self, dockerfile: str | None, sid: str, base_dir: Path, result: AnalysisResult,
    ) -> None:
        if not dockerfile or dockerfile.startswith("/") or dockerfile.startswith("~"):
            return
        df_path = base_dir / dockerfile
        if not df_path.exists():
            result.add(
                IssueSeverity.ERROR, "docker_build",
                f"Step '{sid}' docker build references missing Dockerfile: {dockerfile}",
                sid,
                suggestion=f"Create {df_path} or use standard 'Dockerfile' name.",
            )
        elif dockerfile not in STANDARD_DOCKERFILES:
            result.add(
                IssueSeverity.WARNING, "docker_build",
                f"Step '{sid}' uses non-standard Dockerfile name: {dockerfile}",
                sid,
                suggestion="Consider using standard 'Dockerfile' with multi-arch support.",
            )

    def _check_remote_context(
        self,
        context: str,
        dockerfile: str | None,
        sid: str,
        sync_dests: set[str],
        sync_mappings: list[tuple[str, str]],
        base_dir: Path,
        result: AnalysisResult,
    ) -> None:
        context_clean = context.rstrip("/")
        context_remote = context_clean[2:]
        sync_remote_paths = {
            d[2:].rstrip("/") for d in sync_dests if d.startswith("~/")
        }
        matched = any(
            context_remote == sp or context_remote.startswith(sp + "/")
            for sp in sync_remote_paths
        )
        if not matched and sync_dests:
            result.add(
                IssueSeverity.WARNING, "docker_build",
                f"Step '{sid}' docker build uses remote context '{context}' "
                f"that doesn't match any sync destination",
                sid,
                suggestion=f"Sync destinations: {', '.join(sorted(sync_dests))} — verify context path.",
            )
        if not dockerfile or not matched:
            return
        local_src = match_local_src(sync_mappings, context_clean)
        if not local_src:
            return
        local_df = resolve_local_dockerfile(local_src, dockerfile, base_dir)
        if local_df is not None and not local_df.exists():
            result.add(
                IssueSeverity.ERROR,
                "docker_build",
                f"Step '{sid}' Dockerfile '{dockerfile}' not found in synced local source '{local_src}'",
                sid,
                suggestion=f"Ensure {dockerfile} exists under {local_src} before sync/build.",
            )
