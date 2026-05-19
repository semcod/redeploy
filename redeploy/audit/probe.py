"""SSH read-only probes used during host audit."""
from __future__ import annotations

import shlex
from typing import Optional

from ..ssh import SshClient


class Probe:
    """Thin wrapper around SshClient with sensible audit timeouts."""

    def __init__(self, client: SshClient):
        self.client = client

    def has_binary(self, name: str) -> tuple[bool, str]:
        r = self.client.run(
            f"command -v {shlex.quote(name)} 2>/dev/null", timeout=10
        )
        return r.ok and bool(r.out), r.out or r.stderr

    def has_path(self, path: str, *, kind: str = "any") -> tuple[bool, str]:
        flag = {"file": "-f", "dir": "-d", "any": "-e"}.get(kind, "-e")
        cmd = f"test {flag} {shlex.quote(path)} && echo OK || echo MISSING"
        if path.startswith("~"):
            cmd = f"test {flag} {path} && echo OK || echo MISSING"
        r = self.client.run(cmd, timeout=10)
        out = r.out
        return out == "OK", out or r.stderr

    def port_listening(self, port: int) -> tuple[bool, str]:
        r = self.client.run(
            f"ss -tlnH 2>/dev/null | awk '{{print $4}}' | "
            f"grep -E ':{port}$' | head -1",
            timeout=10,
        )
        if r.ok and r.out:
            return True, r.out
        r2 = self.client.run(
            f"awk 'NR>1{{split($2,a,\":\"); printf \"%d\\n\",strtonum(\"0x\"a[2])}}' "
            f"/proc/net/tcp /proc/net/tcp6 2>/dev/null | sort -u | grep -E '^{port}$' | head -1",
            timeout=10,
        )
        return (r2.ok and bool(r2.out)), r2.out

    def has_image(self, ref: str) -> tuple[bool, str]:
        for engine in ("podman", "docker"):
            r = self.client.run(
                f"{engine} image inspect {shlex.quote(ref)} "
                f"--format '{{{{.Id}}}}' 2>/dev/null", timeout=15,
            )
            if r.ok and r.out:
                return True, f"{engine}:{r.out[:12]}"
        return False, "image not found via podman/docker"

    def has_systemd_unit(self, unit: str, *, user: bool = False) -> tuple[bool, str]:
        scope = "--user " if user else ""
        r = self.client.run(
            f"systemctl {scope}list-unit-files --no-legend "
            f"{shlex.quote(unit)} 2>/dev/null | head -1",
            timeout=10,
        )
        return (r.ok and bool(r.out)), r.out or r.stderr

    def apt_package(self, name: str) -> tuple[bool, str]:
        r = self.client.run(
            f"dpkg-query -W -f='${{Status}}' {shlex.quote(name)} 2>/dev/null",
            timeout=10,
        )
        return (r.ok and "install ok installed" in r.out), r.out or r.stderr

    def disk_free_gib(self, path: str = "~") -> Optional[float]:
        r = self.client.run(
            f"df -P {path} 2>/dev/null | awk 'NR==2{{print $4}}'", timeout=10,
        )
        if not (r.ok and r.out.isdigit()):
            return None
        return int(r.out) / (1024 * 1024)
