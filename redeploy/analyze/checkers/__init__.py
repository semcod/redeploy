"""Built-in static checkers for redeploy specs."""
from .base import Checker
from .binary import BinaryChecker, extract_binaries
from .command_ref import CommandRefChecker
from .compose import ComposeChecker, scan_compose_file
from .docker_build import DockerBuildChecker, collect_sync_mappings, parse_docker_build
from .env import EnvFileChecker
from .path import CommandPathChecker, PathChecker, is_inside, resolve_local_path
from .reference import ReferenceChecker

# Backward-compatible private aliases used in tests.
_Checker = Checker
_PathChecker = PathChecker
_CommandPathChecker = CommandPathChecker
_ReferenceChecker = ReferenceChecker
_ComposeChecker = ComposeChecker
_DockerBuildChecker = DockerBuildChecker
_CommandRefChecker = CommandRefChecker
_EnvFileChecker = EnvFileChecker
_BinaryChecker = BinaryChecker

__all__ = [
    "Checker",
    "PathChecker",
    "CommandPathChecker",
    "ReferenceChecker",
    "ComposeChecker",
    "DockerBuildChecker",
    "CommandRefChecker",
    "EnvFileChecker",
    "BinaryChecker",
    "scan_compose_file",
    "collect_sync_mappings",
    "parse_docker_build",
    "extract_binaries",
    "resolve_local_path",
    "is_inside",
    "_Checker",
    "_PathChecker",
    "_CommandPathChecker",
    "_ReferenceChecker",
    "_ComposeChecker",
    "_DockerBuildChecker",
    "_CommandRefChecker",
    "_EnvFileChecker",
    "_BinaryChecker",
]
