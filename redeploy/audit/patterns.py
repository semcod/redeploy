"""Regex heuristics for extracting expectations from shell commands."""
from __future__ import annotations

import re

from ..models import DeployStrategy

STRATEGY_BINARIES: dict[DeployStrategy, tuple[str, ...]] = {
    DeployStrategy.PODMAN_QUADLET: ("podman", "systemctl", "loginctl"),
    DeployStrategy.DOCKER_FULL: ("docker",),
    DeployStrategy.K3S: ("kubectl",),
    DeployStrategy.DOCKER_KIOSK: ("docker",),
}

RE_PODMAN_BUILD_TAG = re.compile(
    r"podman\s+build(?:\s+[-\w]+)*\s+-t\s+([\w\-./:]+)", re.IGNORECASE
)
RE_DOCKER_BUILD_TAG = re.compile(
    r"docker\s+build(?:\s+[-\w]+)*\s+-t\s+([\w\-./:]+)", re.IGNORECASE
)
RE_MKDIR = re.compile(r"\bmkdir\s+(?:-[pmv]+\s+)?([^\s&|;><]+)")
RE_SYSTEMCTL_USER_UNIT = re.compile(r"systemctl\s+--user\s+\w+\s+([\w@\-.]+)")
RE_PORT_URL = re.compile(r"https?://[^/\s:]+(?::(\d+))?")
RE_APT_INSTALL = re.compile(
    r"apt(?:-get)?\s+install\s+(?:-[\w-]+\s+)*([\w\-+.\s]+?)(?:[;&|]|$)",
    re.IGNORECASE,
)
RE_COMMAND_V = re.compile(r"command\s+-v\s+([\w\-]+)")
