"""Path and URL helpers for audit expectation extraction."""
from __future__ import annotations

from typing import Optional

from .patterns import RE_PORT_URL


def extract_port(url: str) -> Optional[int]:
    m = RE_PORT_URL.match(url.strip())
    if not m:
        return None
    raw = m.group(1)
    if raw:
        return int(raw)
    if url.startswith("https://"):
        return 443
    if url.startswith("http://"):
        return 80
    return None


def normalize_path(path: str) -> str:
    p = path.strip().strip("'\"")
    if p.endswith("/") and len(p) > 1:
        p = p.rstrip("/")
    return p


def strip_remote_dir(path: str) -> str:
    if ":" in path and not path.startswith("/"):
        if path.count(":") == 1 and "/" in path.split(":", 1)[1]:
            return path.split(":", 1)[1]
    return path
