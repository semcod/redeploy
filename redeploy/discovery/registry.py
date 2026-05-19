"""Merge discovered hosts into the device registry."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..models import DeviceRegistry, KnownDevice
from .types import DiscoveredHost


def update_registry(
    hosts: list[DiscoveredHost],
    registry: Optional[DeviceRegistry] = None,
    save: bool = True,
) -> DeviceRegistry:
    """Merge discovered hosts into DeviceRegistry and optionally save."""
    reg = registry or DeviceRegistry.load()
    now = datetime.now(timezone.utc)

    for host in hosts:
        if not host.ip:
            continue
        device_id = f"{host.ssh_user}@{host.ip}" if host.ssh_user else host.ip
        existing = reg.get(device_id) or reg.get(host.ip)

        if existing:
            _update_existing_device(existing, host, now)
            reg.upsert(existing)
        elif host.ssh_ok:
            reg.upsert(_new_discovered_device(device_id, host, now))

    if save:
        reg.save()
    return reg


def _update_existing_device(existing: KnownDevice, host: DiscoveredHost, now: datetime) -> None:
    existing.last_seen = now
    if host.mac:
        existing.mac = host.mac
    if host.hostname and not existing.hostname:
        existing.hostname = host.hostname
    if host.ssh_ok:
        existing.last_ssh_ok = now
    if host.is_raspberry_pi and "raspberry-pi" not in existing.tags:
        existing.tags.append("raspberry-pi")


def _new_discovered_device(device_id: str, host: DiscoveredHost, now: datetime) -> KnownDevice:
    tags = ["discovered"]
    if host.is_raspberry_pi:
        tags.append("raspberry-pi")
    return KnownDevice(
        id=device_id,
        host=device_id,
        ip=host.ip,
        mac=host.mac,
        hostname=host.hostname,
        ssh_user=host.ssh_user if host.ssh_user else "",  # type: ignore[call-arg]
        last_seen=now,
        last_ssh_ok=now,
        source=host.source,
        tags=tags,
    )
