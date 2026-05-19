"""Parse remote probe shell output and infer deployment strategy."""


def parse_probe_output(out: str) -> tuple[dict, list[str]]:
    info: dict = {}
    services: list[str] = []
    in_services = False

    for line in out.splitlines():
        line = line.strip()
        if line.startswith("__arch__="):
            info["arch"] = line.split("=", 1)[1]
        elif line.startswith("__os__="):
            info["os_info"] = line.split("=", 1)[1]
        elif line.startswith("__hostname__="):
            info["hostname"] = line.split("=", 1)[1]
        elif line.startswith("__docker__="):
            info["has_docker"] = line.endswith("1")
        elif line.startswith("__podman__="):
            info["has_podman"] = line.endswith("1")
        elif line.startswith("__chromium__="):
            info["has_chromium"] = line.endswith("1")
        elif line.startswith("__docker_active__="):
            info["docker_active"] = line.endswith("1")
        elif line == "__end_services__":
            in_services = False
        elif in_services:
            if line:
                services.append(line)
        elif line.endswith(".service") or ("loaded" in line and "active" in line):
            in_services = True
            if line.endswith(".service"):
                services.append(line)

    return info, services


def infer_strategy(info: dict, services: list[str]) -> str:
    if info.get("docker_active") or info.get("has_docker"):
        return "docker_full"
    if info.get("has_podman"):
        return "podman_quadlet"
    if info.get("has_chromium") and any("kiosk" in s or "chromium" in s for s in services):
        return "native_kiosk"
    return "systemd"
