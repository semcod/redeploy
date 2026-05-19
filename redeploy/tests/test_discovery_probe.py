"""Tests for discovery_probe parsing helpers."""
from __future__ import annotations

from redeploy.discovery_probe import infer_strategy, parse_probe_output


SAMPLE_PROBE_OUTPUT = """
__arch__=aarch64
__os__=Debian GNU/Linux 12
__hostname__=pi109
__docker__=1
__podman__=0
__chromium__=0
__docker_active__=1
c2004-backend.service
c2004-frontend.service
__end_services__
"""


class TestParseProbeOutput:
    def test_parses_metadata_and_services(self):
        info, services = parse_probe_output(SAMPLE_PROBE_OUTPUT)
        assert info["arch"] == "aarch64"
        assert info["has_docker"] is True
        assert info["docker_active"] is True
        assert "c2004-backend.service" in services


class TestInferStrategy:
    def test_docker_full_when_docker_active(self):
        info = {"docker_active": True, "has_docker": True}
        assert infer_strategy(info, []) == "docker_full"

    def test_podman_quadlet(self):
        info = {"has_podman": True}
        assert infer_strategy(info, []) == "podman_quadlet"

    def test_native_kiosk(self):
        info = {"has_chromium": True}
        services = ["kiosk-chromium.service"]
        assert infer_strategy(info, services) == "native_kiosk"

    def test_systemd_fallback(self):
        assert infer_strategy({}, []) == "systemd"
