"""Walk a MigrationSpec and emit audit expectations."""
from __future__ import annotations

import re
from typing import Iterable

from ..models import MigrationSpec
from .models import Expect
from .paths import extract_port, normalize_path, strip_remote_dir
from .patterns import (
    RE_APT_INSTALL,
    RE_COMMAND_V,
    RE_DOCKER_BUILD_TAG,
    RE_MKDIR,
    RE_PODMAN_BUILD_TAG,
    RE_SYSTEMCTL_USER_UNIT,
    STRATEGY_BINARIES,
)


class Extractor:
    """Walk a MigrationSpec and emit Expect tuples."""

    def __init__(self, spec: MigrationSpec):
        self.spec = spec
        self._seen: set[tuple[str, str]] = set()

    def collect(self) -> list[Expect]:
        out: list[Expect] = []
        out.extend(self._from_target())
        for raw in self.spec.extra_steps:
            out.extend(self._from_step(raw))
        unique: list[Expect] = []
        for exp in out:
            key = (exp.category, exp.name)
            if key in self._seen:
                continue
            self._seen.add(key)
            unique.append(exp)
        return unique

    def _from_target(self) -> Iterable[Expect]:
        target = self.spec.target
        for binary in STRATEGY_BINARIES.get(target.strategy, ()):
            yield Expect(
                category="binary",
                name=binary,
                source_step="target.strategy",
                fix_hint=f"install {binary} on target host",
            )

        if target.remote_dir:
            yield Expect(
                category="directory",
                name=normalize_path(target.remote_dir),
                source_step="target.remote_dir",
                fix_hint=f"mkdir -p {target.remote_dir}",
            )

        if target.env_file:
            yield Expect(
                category="local_file",
                name=target.env_file,
                source_step="target.env_file",
                fix_hint="provide env_file on the controller before running",
            )

        if target.verify_url:
            port = extract_port(target.verify_url)
            if port:
                yield Expect(
                    category="port_listening",
                    name=str(port),
                    source_step="target.verify_url",
                    fix_hint=f"start the service exposing port {port}",
                    extra=(("url", target.verify_url),),
                )

        for unit in target.stop_services + target.disable_services:
            yield Expect(
                category="systemd_unit",
                name=unit,
                source_step="target.stop_services",
                fix_hint=f"unit {unit} should exist or step will be a no-op",
            )

    def _from_step(self, raw: dict) -> Iterable[Expect]:
        sid = str(raw.get("id", "<extra_step>"))
        action = str(raw.get("action", ""))

        if action in {"rsync", "scp"}:
            dst = raw.get("dst")
            if dst:
                yield Expect(
                    category="directory",
                    name=normalize_path(strip_remote_dir(str(dst))),
                    source_step=sid,
                    fix_hint=f"mkdir -p {dst} on target",
                )
            src = raw.get("src")
            if src and action == "scp":
                yield Expect(
                    category="local_file",
                    name=str(src),
                    source_step=sid,
                    fix_hint=f"controller-side file {src} must exist",
                )

        if action.startswith("systemctl_"):
            svc = raw.get("service")
            if svc:
                yield Expect(
                    category="systemd_unit",
                    name=str(svc),
                    source_step=sid,
                )

        if action in {"http_check", "version_check"}:
            url = raw.get("url")
            if url:
                port = extract_port(str(url))
                if port:
                    yield Expect(
                        category="port_listening",
                        name=str(port),
                        source_step=sid,
                        fix_hint=f"port {port} must be open on target",
                        extra=(("url", str(url)),),
                    )

        cmd = str(raw.get("command") or "")
        if cmd:
            yield from self._from_command(cmd, sid)

    def _from_command(self, cmd: str, sid: str) -> Iterable[Expect]:
        for match in RE_PODMAN_BUILD_TAG.finditer(cmd):
            yield Expect(
                category="container_image",
                name=match.group(1),
                source_step=sid,
                fix_hint=f"image {match.group(1)} not present (will be built by step)",
            )
        for match in RE_DOCKER_BUILD_TAG.finditer(cmd):
            yield Expect(
                category="container_image",
                name=match.group(1),
                source_step=sid,
            )
        for match in RE_MKDIR.finditer(cmd):
            path = match.group(1).strip("'\"")
            if not path or path.startswith("$"):
                continue
            yield Expect(
                category="directory",
                name=normalize_path(path),
                source_step=sid,
                fix_hint=f"mkdir -p {path}",
            )
        for match in RE_SYSTEMCTL_USER_UNIT.finditer(cmd):
            yield Expect(
                category="systemd_user_unit",
                name=match.group(1),
                source_step=sid,
            )
        for match in RE_COMMAND_V.finditer(cmd):
            yield Expect(
                category="binary",
                name=match.group(1),
                source_step=sid,
            )
        for match in RE_APT_INSTALL.finditer(cmd):
            for pkg in match.group(1).split():
                pkg = pkg.strip()
                if not pkg or pkg.startswith("-"):
                    continue
                if re.fullmatch(r"[\w.+\-]+", pkg) and "." not in pkg:
                    yield Expect(
                        category="apt_package",
                        name=pkg,
                        source_step=sid,
                        fix_hint=f"sudo apt-get install -y {pkg}",
                    )
