"""SSH credential discovery for autonomous host probes."""
from __future__ import annotations

import os
import queue
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DEFAULT_KEY_NAMES = (
    "id_ed25519", "id_rsa", "id_ecdsa",
    "rpi_key", "safetytwin-key",
)


def collect_ssh_keys() -> list[str]:
    keys: list[str] = []
    env_key = os.environ.get("SSH_KEY_PATH") or os.environ.get("SSH_KEY_FILE")
    if env_key and Path(env_key).is_file():
        keys.append(env_key)
    ssh_dir = Path.home() / ".ssh"
    if not ssh_dir.is_dir():
        return keys
    for name in DEFAULT_KEY_NAMES:
        path = ssh_dir / name
        if path.is_file() and ".pub" not in str(path):
            key = str(path)
            if key not in keys:
                keys.append(key)
    for path in sorted(ssh_dir.iterdir()):
        if path.suffix == "" and not path.name.endswith(".pub") and path.name not in (
            "known_hosts", "config", "authorized_keys",
        ):
            key = str(path)
            if key not in keys:
                keys.append(key)
    return keys


def tcp_reachable(ip: str, port: int = 22, timeout: float = 2.0) -> bool:
    import socket as sock
    try:
        with sock.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def try_ssh_credentials(
    ip: str,
    users: list[str],
    keys: list[str],
    port: int = 22,
    timeout: int = 5,
) -> tuple[str, str, str]:
    import getpass

    if not tcp_reachable(ip, port, timeout=min(timeout, 3.0)):
        return "", "", ""

    cur = getpass.getuser()
    users = [cur] + [u for u in users if u != cur]
    result_q: queue.Queue = queue.Queue()

    def try_one(user: str, key: str | None) -> None:
        cmd = [
            "ssh",
            "-o", f"ConnectTimeout={timeout}",
            "-o", "StrictHostKeyChecking=no",
            "-o", "BatchMode=yes",
            "-o", "PasswordAuthentication=no",
            "-p", str(port),
        ]
        if key:
            cmd += ["-i", key]
        cmd += [f"{user}@{ip}", "echo __ok__"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)
            if result.returncode == 0 and "__ok__" in result.stdout:
                result_q.put((user, key or "", f"{user}@{ip}"))
        except Exception:
            pass

    for user in users:
        cmd = [
            "ssh",
            "-o", f"ConnectTimeout={timeout}",
            "-o", "StrictHostKeyChecking=no",
            "-o", "BatchMode=yes",
            "-o", "PasswordAuthentication=no",
            "-p", str(port),
            f"{user}@{ip}", "echo __ok__",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)
            if result.returncode == 0 and "__ok__" in result.stdout:
                return user, "", f"{user}@{ip}"
        except Exception:
            pass

    combos = [(u, k) for u in users for k in ([None] + keys) if k is not None]
    with ThreadPoolExecutor(max_workers=min(len(combos), 16)) as executor:
        futures = [executor.submit(try_one, u, k) for u, k in combos]
        try:
            return result_q.get(timeout=timeout + 3)
        except queue.Empty:
            pass
        for future in futures:
            future.cancel()

    return "", "", ""
