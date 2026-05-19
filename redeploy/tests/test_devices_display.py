"""Tests for devices_display helpers."""
from __future__ import annotations

from redeploy.cli.commands.devices_display import filter_devices
from redeploy.models import KnownDevice


def _device(**kwargs) -> KnownDevice:
    defaults = dict(
        id="pi@10.0.0.1",
        host="pi@10.0.0.1",
        ip="10.0.0.1",
        strategy="docker_full",
        tags=[],
    )
    defaults.update(kwargs)
    return KnownDevice(**defaults)


class TestFilterDevices:
    def test_filter_by_tag(self):
        devices = [
            _device(id="a", tags=["kiosk"]),
            _device(id="b", tags=[]),
        ]
        assert len(filter_devices(devices, tag="kiosk", strategy=None, rpi=False, reachable=False)) == 1

    def test_filter_rpi(self):
        devices = [
            _device(id="a", tags=["raspberry-pi"]),
            _device(id="b", tags=[]),
        ]
        assert len(filter_devices(devices, tag=None, strategy=None, rpi=True, reachable=False)) == 1
