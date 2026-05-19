"""Small helpers shared by discovery scanners."""
from __future__ import annotations

import re
import subprocess

RPI_MAC_PREFIXES = (
    "b8:27:eb",
    "dc:a6:32",
    "e4:5f:01",
    "28:cd:c1",
)


def is_raspberry_pi_mac(mac: str) -> bool:
    if not mac:
        return False
    return mac[:8].lower() in RPI_MAC_PREFIXES


def run_shell(cmd: str, timeout: int = 10) -> str:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout,
        )
        return result.stdout
    except Exception:
        return ""


def is_ip(value: str) -> bool:
    return bool(re.match(r"^\d+\.\d+\.\d+\.\d+$", value))
