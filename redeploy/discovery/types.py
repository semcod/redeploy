"""Discovery result types."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DiscoveredHost:
    ip: str
    mac: str = ""
    hostname: str = ""
    ssh_ok: bool = False
    ssh_user: str = ""
    source: str = "unknown"
    ports_open: list[int] = field(default_factory=list)
    is_raspberry_pi: bool = False


@dataclass
class ProbeResult:
    """Full autonomous probe result for a single host."""
    ip: str
    host: str = ""
    ssh_user: str = ""
    ssh_key: str = ""
    ssh_port: int = 22
    reachable: bool = False
    strategy: str = "unknown"
    app: str = ""
    version: str = ""
    hostname: str = ""
    arch: str = ""
    os_info: str = ""
    has_docker: bool = False
    has_podman: bool = False
    has_chromium: bool = False
    running_services: list[str] = field(default_factory=list)
    error: str = ""
