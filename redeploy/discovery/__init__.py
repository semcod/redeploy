"""Device discovery — find SSH-accessible nodes in the local network."""
from __future__ import annotations

from .auto_probe import auto_probe
from .helpers import is_ip as _is_ip
from .helpers import is_raspberry_pi_mac as _is_raspberry_pi_mac
from .helpers import run_shell as _run
from .probe_parse import infer_strategy as _infer_strategy
from .probe_parse import parse_probe_output as _parse_probe_output
from .registry import update_registry
from .scanners import (
    discover,
    merge_hosts as _merge,
    scan_known_hosts as _scan_known_hosts,
)
from .types import DiscoveredHost, ProbeResult

__all__ = [
    "DiscoveredHost",
    "ProbeResult",
    "discover",
    "update_registry",
    "auto_probe",
    "_is_ip",
    "_merge",
    "_scan_known_hosts",
    "_run",
    "_parse_probe_output",
    "_infer_strategy",
    "_is_raspberry_pi_mac",
]
