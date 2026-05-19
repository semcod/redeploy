"""Compare a MigrationSpec's expectations against a live target host."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from loguru import logger

from ..models import MigrationSpec
from ..ssh import SshClient
from .extractor import Extractor
from .models import AuditCheck, AuditReport, Expect
from .probe import Probe


class Auditor:
    MIN_FREE_GIB = 5.0

    def __init__(
        self,
        spec: MigrationSpec,
        spec_path: str | Path = "<spec>",
        *,
        host: Optional[str] = None,
        ssh_key: Optional[str] = None,
    ):
        self.spec = spec
        self.spec_path = str(spec_path)
        self.host = host or spec.target.host or spec.source.host or "local"
        client = SshClient(host=self.host, key=ssh_key)
        self.probe = Probe(client)

    def run(self) -> AuditReport:
        report = AuditReport(
            spec_path=self.spec_path,
            host=self.host,
            target_strategy=str(self.spec.target.strategy.value),
        )

        if not self.probe.client.is_reachable(timeout=10):
            report.add(AuditCheck(
                category="connectivity",
                name=self.host,
                status="fail",
                detail="SSH unreachable",
                fix_hint="check network, SSH key, and BatchMode auth",
            ))
            return report
        report.add(AuditCheck(
            category="connectivity",
            name=self.host,
            status="pass",
            detail="ssh ok",
        ))

        self._add_disk_check(report)

        for exp in Extractor(self.spec).collect():
            report.add(self._probe_one(exp))

        logger.info(report.summary())
        return report

    def _add_disk_check(self, report: AuditReport) -> None:
        free = self.probe.disk_free_gib("~")
        if free is None:
            report.add(AuditCheck(
                category="disk",
                name="~",
                status="warn",
                detail="could not read disk usage",
            ))
            return
        if free < self.MIN_FREE_GIB:
            report.add(AuditCheck(
                category="disk",
                name="~",
                status="fail",
                detail=f"only {free:.1f} GiB free (need ≥ {self.MIN_FREE_GIB:.1f} GiB)",
                fix_hint="prune images / clean /var/tmp / expand storage",
            ))
        else:
            report.add(AuditCheck(
                category="disk",
                name="~",
                status="pass",
                detail=f"{free:.1f} GiB free",
            ))

    def _probe_one(self, exp: Expect) -> AuditCheck:
        handlers = {
            "binary": lambda: self._probe_binary(exp),
            "directory": lambda: self._probe_directory(exp),
            "file": lambda: self._probe_file(exp),
            "local_file": lambda: self._probe_local_file(exp),
            "port_listening": lambda: self._probe_port_listening(exp),
            "container_image": lambda: self._probe_container_image(exp),
            "systemd_unit": lambda: self._probe_systemd_unit(exp, user=False),
            "systemd_user_unit": lambda: self._probe_systemd_unit(exp, user=True),
            "apt_package": lambda: self._probe_apt_package(exp),
        }
        handler = handlers.get(exp.category)
        if handler is None:
            return AuditCheck(
                category=exp.category, name=exp.name,
                status="skip", detail=f"unknown category {exp.category}",
                source_step=exp.source_step,
            )
        return handler()

    def _check(self, exp: Expect, ok: bool, detail: str, *, status_fail: str = "fail") -> AuditCheck:
        return AuditCheck(
            category=exp.category, name=exp.name,
            status="pass" if ok else status_fail,
            detail=detail or ("present" if ok else "missing"),
            fix_hint=exp.fix_hint, source_step=exp.source_step,
        )

    def _probe_binary(self, exp: Expect) -> AuditCheck:
        ok, detail = self.probe.has_binary(exp.name)
        return self._check(exp, ok, detail)

    def _probe_directory(self, exp: Expect) -> AuditCheck:
        ok, detail = self.probe.has_path(exp.name, kind="dir")
        return self._check(exp, ok, detail)

    def _probe_file(self, exp: Expect) -> AuditCheck:
        ok, detail = self.probe.has_path(exp.name, kind="file")
        return self._check(exp, ok, detail)

    def _probe_local_file(self, exp: Expect) -> AuditCheck:
        local_ok = Path(exp.name).expanduser().exists()
        return self._check(
            exp, local_ok,
            "present" if local_ok else "missing on controller",
        )

    def _probe_port_listening(self, exp: Expect) -> AuditCheck:
        ok, detail = self.probe.port_listening(int(exp.name))
        return self._check(exp, ok, detail)

    def _probe_container_image(self, exp: Expect) -> AuditCheck:
        ok, detail = self.probe.has_image(exp.name)
        return self._check(
            exp, ok, detail or ("present" if ok else "will be built by step"),
            status_fail="warn",
        )

    def _probe_systemd_unit(self, exp: Expect, *, user: bool) -> AuditCheck:
        ok, detail = self.probe.has_systemd_unit(exp.name, user=user)
        return self._check(exp, ok, detail)

    def _probe_apt_package(self, exp: Expect) -> AuditCheck:
        ok, detail = self.probe.apt_package(exp.name)
        return self._check(exp, ok, detail)
