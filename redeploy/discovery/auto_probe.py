"""Autonomous single-host probe with strategy detection."""
from __future__ import annotations

import subprocess
from datetime import datetime
from typing import Optional

from loguru import logger

from ..models import DeviceRegistry, KnownDevice
from .probe_parse import infer_strategy, parse_probe_output
from .ssh_credentials import collect_ssh_keys, try_ssh_credentials
from .types import ProbeResult

DEFAULT_USERS = ["pi", "ubuntu", "root", "admin", "tom", "debian"]


def parse_probe_input(ip_or_host: str, users: Optional[list[str]]) -> tuple[str, list[str]]:
    if "@" in ip_or_host:
        forced_user, ip = ip_or_host.split("@", 1)
        return ip, [forced_user] + (users or DEFAULT_USERS)
    return ip_or_host, users or DEFAULT_USERS


def build_probe_command() -> str:
    return (
        "echo __arch__=$(uname -m); "
        "echo __os__=$(. /etc/os-release 2>/dev/null && echo $PRETTY_NAME || uname -s); "
        "echo __hostname__=$(hostname); "
        "docker info --format 'ok' 2>/dev/null && echo __docker__=1 || echo __docker__=0; "
        "podman --version 2>/dev/null && echo __podman__=1 || echo __podman__=0; "
        "which chromium chromium-browser 2>/dev/null && echo __chromium__=1 || echo __chromium__=0; "
        "systemctl is-active --quiet docker 2>/dev/null && echo __docker_active__=1 || echo __docker_active__=0; "
        "systemctl list-units --type=service --state=running --no-pager --no-legend 2>/dev/null | awk '{print $1}' | head -30; "
        "echo __end_services__"
    )


def build_ssh_command(
    host: str, port: int, timeout: int, key_opts: list[str], probe_cmd: str,
) -> list[str]:
    return ["ssh"] + [
        "-o", f"ConnectTimeout={timeout}",
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        "-p", str(port),
    ] + key_opts + [host, probe_cmd]


def run_ssh_probe(cmd: list[str], timeout: int) -> str | None:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        if result.returncode != 0:
            return None
        return result.stdout
    except Exception:
        return None


def detect_strategy_remote(
    host: str, key: str, port: int = 22, timeout: int = 10,
) -> dict:
    key_opts = ["-i", key] if key else []
    cmd = build_ssh_command(host, port, timeout, key_opts, build_probe_command())
    out = run_ssh_probe(cmd, timeout)
    if out is None:
        return {}
    info, services = parse_probe_output(out)
    info["running_services"] = services
    info["strategy"] = infer_strategy(info, services)
    return info


def detect_app_from_services(services: list[str], app_hint: str) -> str:
    if app_hint:
        return app_hint
    for svc in services:
        for candidate in ("c2004", "app", "backend", "kiosk", "api"):
            if candidate in svc.lower():
                return candidate
    return ""


def _update_existing_from_probe(
    existing: KnownDevice,
    result: ProbeResult,
    ssh_user: str,
    ssh_key: str,
    ip: str,
    host_str: str,
    port: int,
    now: datetime,
) -> None:
    existing.host = host_str
    existing.ip = ip
    existing.ssh_user = ssh_user
    if ssh_key:
        existing.ssh_key = ssh_key
    existing.ssh_port = port
    existing.strategy = result.strategy
    existing.hostname = result.hostname or existing.hostname
    existing.last_seen = now
    existing.last_ssh_ok = now
    if result.app and not existing.app:
        existing.app = result.app


def _new_device_from_probe(
    result: ProbeResult,
    ssh_user: str,
    ssh_key: str,
    ip: str,
    host_str: str,
    port: int,
    now: datetime,
) -> KnownDevice:
    return KnownDevice(
        id=host_str,
        host=host_str,
        ip=ip,
        mac="",
        hostname=result.hostname,
        ssh_user=ssh_user,
        ssh_key=ssh_key if ssh_key else None,
        ssh_port=port,
        strategy=result.strategy,
        app=result.app,
        last_seen=now,
        last_ssh_ok=now,
        source="probe",
        tags=["discovered"],
    )


def auto_probe(
    ip_or_host: str,
    users: Optional[list[str]] = None,
    port: int = 22,
    timeout: int = 6,
    app_hint: str = "",
    save: bool = True,
) -> ProbeResult:
    ip, users = parse_probe_input(ip_or_host, users)
    result = ProbeResult(ip=ip, ssh_port=port)
    keys = collect_ssh_keys()

    ssh_user, ssh_key, host_str = try_ssh_credentials(ip, users, keys, port, timeout)
    if not host_str:
        result.error = f"No SSH access: tried {len(users)} users × {len(keys)+1} keys"
        logger.warning(f"[probe {ip}] {result.error}")
        return result

    result.reachable = True
    result.ssh_user = ssh_user
    result.ssh_key = ssh_key
    result.host = host_str
    logger.info(
        f"[probe {ip}] SSH OK as {ssh_user}"
        + (f" via {__import__('os').path.basename(ssh_key)}" if ssh_key else " (agent/default)")
    )

    info = detect_strategy_remote(host_str, ssh_key, port, timeout=timeout * 2)
    if info:
        result.strategy = info.get("strategy", "systemd")
        result.hostname = info.get("hostname", "")
        result.arch = info.get("arch", "")
        result.os_info = info.get("os_info", "")
        result.has_docker = bool(info.get("has_docker"))
        result.has_podman = bool(info.get("has_podman"))
        result.has_chromium = bool(info.get("has_chromium"))
        result.running_services = info.get("running_services", [])
        result.app = detect_app_from_services(result.running_services, app_hint)

    if save:
        reg = DeviceRegistry.load()
        now = datetime.utcnow()
        existing = reg.get(host_str) or reg.get(ip)
        if existing:
            _update_existing_from_probe(existing, result, ssh_user, ssh_key, ip, host_str, port, now)
            reg.upsert(existing)
        else:
            reg.upsert(_new_device_from_probe(result, ssh_user, ssh_key, ip, host_str, port, now))
        reg.save()
        logger.info(f"[probe {ip}] saved to registry as {host_str}")

    return result
