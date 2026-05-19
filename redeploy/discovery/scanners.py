"""Passive and active network scanners for device discovery."""
from __future__ import annotations

import ipaddress
import re
import shutil
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from .helpers import is_ip, is_raspberry_pi_mac, run_shell
from .types import DiscoveredHost


def scan_known_hosts(ssh_user: str = "") -> list[DiscoveredHost]:
    kh = __import__("pathlib").Path.home() / ".ssh" / "known_hosts"
    if not kh.exists():
        return []
    results: list[DiscoveredHost] = []
    for line in kh.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        host_field = line.split()[0]
        if host_field.startswith("|"):
            continue
        host_field = re.sub(r"^\[(.+)\]:\d+$", r"\1", host_field)
        for candidate in host_field.split(","):
            candidate = candidate.strip()
            if not candidate:
                continue
            try:
                ip = socket.gethostbyname(candidate)
            except Exception:
                ip = candidate
            results.append(DiscoveredHost(
                ip=ip,
                hostname=candidate if not is_ip(candidate) else "",
                source="known_hosts",
                ssh_user=ssh_user,
            ))
    logger.debug(f"known_hosts: {len(results)} hosts")
    return results


def scan_arp_cache() -> list[DiscoveredHost]:
    results: list[DiscoveredHost] = []

    if shutil.which("ip"):
        out = run_shell("ip neigh show")
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 5 and re.match(r"\d+\.\d+\.\d+\.\d+", parts[0]):
                mac = parts[4] if len(parts) > 4 else ""
                results.append(DiscoveredHost(
                    ip=parts[0],
                    mac=mac,
                    source="arp",
                    is_raspberry_pi=is_raspberry_pi_mac(mac),
                ))
        if results:
            logger.debug(f"arp (ip neigh): {len(results)} hosts")
            return results

    if shutil.which("arp"):
        out = run_shell("arp -a")
        for line in out.splitlines():
            match = re.search(
                r"\((\d+\.\d+\.\d+\.\d+)\).*?([0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f:]+)",
                line, re.I,
            )
            if match:
                mac = match.group(2)
                results.append(DiscoveredHost(
                    ip=match.group(1),
                    mac=mac,
                    source="arp",
                    is_raspberry_pi=is_raspberry_pi_mac(mac),
                ))
    logger.debug(f"arp: {len(results)} hosts")
    return results


def scan_mdns(timeout: int = 5) -> list[DiscoveredHost]:
    results: list[DiscoveredHost] = []
    if shutil.which("avahi-browse"):
        out = run_shell(f"avahi-browse -t -r -p _ssh._tcp 2>/dev/null", timeout=timeout + 2)
        for line in out.splitlines():
            if line.startswith("="):
                parts = line.split(";")
                if len(parts) >= 8:
                    hostname = parts[3]
                    ip = parts[7]
                    if is_ip(ip):
                        results.append(DiscoveredHost(
                            ip=ip, hostname=hostname, source="mdns", ports_open=[22],
                        ))
    logger.debug(f"mdns: {len(results)} hosts")
    return results


def ping_sweep(subnet: str, timeout: int = 1) -> list[DiscoveredHost]:
    try:
        net = ipaddress.ip_network(subnet, strict=False)
    except ValueError:
        logger.warning(f"Invalid subnet: {subnet}")
        return []

    hosts_to_ping = list(net.hosts())
    if len(hosts_to_ping) > 254:
        logger.warning("Ping sweep limited to /24 (254 hosts)")
        hosts_to_ping = hosts_to_ping[:254]

    def ping_one(ip: str) -> Optional[DiscoveredHost]:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout), str(ip)],
            capture_output=True, timeout=timeout + 1,
        )
        if result.returncode == 0:
            return DiscoveredHost(ip=str(ip), source="ping_sweep")
        return None

    alive: list[DiscoveredHost] = []
    with ThreadPoolExecutor(max_workers=64) as executor:
        futures = {executor.submit(ping_one, str(h)): str(h) for h in hosts_to_ping}
        for future in as_completed(futures):
            host = future.result()
            if host:
                alive.append(host)

    logger.debug(f"ping sweep {subnet}: {len(alive)} alive")
    return alive


def probe_ssh_batch(
    hosts: list[DiscoveredHost],
    users: list[str],
    port: int = 22,
    timeout: int = 4,
    max_workers: int = 32,
) -> list[DiscoveredHost]:
    def try_ssh(host: DiscoveredHost) -> DiscoveredHost:
        for user in users:
            target = f"{user}@{host.ip}"
            cmd = [
                "ssh",
                "-o", "ConnectTimeout=4",
                "-o", "StrictHostKeyChecking=no",
                "-o", "BatchMode=yes",
                "-o", "PasswordAuthentication=no",
                "-p", str(port),
                target, "echo ok",
            ]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 1)
                if result.returncode == 0 and "ok" in result.stdout:
                    host.ssh_ok = True
                    host.ssh_user = user
                    host.last_ssh_ok = datetime.now(timezone.utc)  # type: ignore[attr-defined]
                    break
            except Exception:
                pass
        return host

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(try_ssh, hosts))


def detect_local_subnet() -> Optional[str]:
    if shutil.which("ip"):
        out = run_shell("ip route show")
        for line in out.splitlines():
            match = re.search(r"(\d+\.\d+\.\d+\.\d+/\d+)\s+dev", line)
            if match:
                try:
                    network = ipaddress.ip_network(match.group(1), strict=False)
                    if not network.is_loopback and network.prefixlen >= 16:
                        return str(network)
                except ValueError:
                    pass
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
        parts = local_ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    except Exception:
        pass
    return None


def merge_hosts(hosts: list[DiscoveredHost]) -> list[DiscoveredHost]:
    by_ip: dict[str, DiscoveredHost] = {}
    for host in hosts:
        if host.ip in by_ip:
            existing = by_ip[host.ip]
            if not existing.mac and host.mac:
                existing.mac = host.mac
            if not existing.hostname and host.hostname:
                existing.hostname = host.hostname
            if host.ssh_ok:
                existing.ssh_ok = True
                existing.ssh_user = existing.ssh_user or host.ssh_user
            if existing.source == "unknown":
                existing.source = host.source
            if host.is_raspberry_pi:
                existing.is_raspberry_pi = True
        else:
            by_ip[host.ip] = host
    return list(by_ip.values())


def discover(
    subnet: Optional[str] = None,
    ssh_users: Optional[list[str]] = None,
    ssh_port: int = 22,
    ping: bool = False,
    mdns: bool = True,
    probe_ssh: bool = True,
    timeout: int = 5,
) -> list[DiscoveredHost]:
    import getpass

    ssh_users = ssh_users or [getpass.getuser(), "root", "pi", "ubuntu", "admin"]
    found: list[DiscoveredHost] = []

    found.extend(scan_known_hosts(ssh_user=ssh_users[0]))
    found.extend(scan_arp_cache())
    if mdns:
        found.extend(scan_mdns(timeout=timeout))
    if ping:
        sub = subnet or detect_local_subnet()
        if sub:
            logger.info(f"Ping sweep: {sub}")
            found.extend(ping_sweep(sub, timeout=timeout))

    found = merge_hosts(found)

    rpi_devices = [h for h in found if h.is_raspberry_pi]
    if rpi_devices:
        logger.info(
            f"Found {len(rpi_devices)} Raspberry Pi device(s): "
            f"{', '.join(h.ip for h in rpi_devices)}"
        )

    if probe_ssh and found:
        logger.info(f"SSH probe: {len(found)} hosts ({timeout}s timeout each)")
        found = probe_ssh_batch(found, users=ssh_users, port=ssh_port, timeout=timeout)

    found.sort(key=lambda h: [int(x) for x in h.ip.split(".") if x.isdigit()])
    return found
