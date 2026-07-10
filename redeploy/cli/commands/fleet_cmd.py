"""fleet command group — live device status and parallel spec runs.

Devices/probes come from ``fleet-probes.yaml`` (project root) so the command
stays project-agnostic:

.. code-block:: yaml

    probes:
      - name: pi109
        ssh: pi@192.168.188.109
        units: "c2004-*"
        http:
          - {name: api, url: "http://192.168.188.109:8100/api/v3/health"}
        drift:
          - {repo: ., remote_dir: "~/c2004"}
    jobs:
      - {name: "122", cwd: /home/tom/github/oqlos/oqlos, spec: redeploy/122/migration.md}
      - {name: pi109, cwd: ., spec: redeploy/pi109/migration.md}
"""
from __future__ import annotations

from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

DEFAULT_PROBES_FILE = "fleet-probes.yaml"


def _load_config(path: str | None) -> dict:
    fp = Path(path or DEFAULT_PROBES_FILE)
    if not fp.exists():
        raise click.UsageError(
            f"{fp} not found — describe your devices there (see `redeploy fleet --help`)."
        )
    return yaml.safe_load(fp.read_text()) or {}


def _build_probes(cfg: dict):
    from ...fleet_ops import DriftCheck, FleetProbe, HttpCheck

    probes = []
    for entry in cfg.get("probes", []):
        probes.append(FleetProbe(
            name=entry["name"],
            ssh_host=entry.get("ssh"),
            ping_host=entry.get("ping"),
            unit_glob=entry.get("units"),
            http=[HttpCheck(h["name"], h["url"], int(h.get("timeout", 6)))
                  for h in entry.get("http", [])],
            drift=[DriftCheck(Path(d["repo"]), d["remote_dir"], d.get("name", ""))
                   for d in entry.get("drift", [])],
        ))
    return probes


@click.group("fleet")
def fleet_cmd():
    """Live status and parallel deploys across the device fleet."""


@fleet_cmd.command("status")
@click.option("--config", "config_path", type=click.Path(), default=None,
              help=f"Probe config (default: ./{DEFAULT_PROBES_FILE}).")
@click.option("--device", "only", multiple=True, help="Probe only these device names.")
def fleet_status_cmd(config_path, only):
    """Probe every device in parallel: net, http health, failed units, drift.

    Exit 1 when any device needs attention.
    """
    from ...fleet_ops import fleet_status

    console = Console()
    probes = _build_probes(_load_config(config_path))
    if only:
        probes = [p for p in probes if p.name in only]
    if not probes:
        raise click.UsageError("no matching probes")

    results = fleet_status(probes)
    bad = False
    for res in results:
        style = "green" if res.healthy else "red"
        console.print(f"[bold {style}]── {res.name} ──[/bold {style}]")
        for key, value in res.fields.items():
            mark = "[red]" if value in ("FAIL", "OFFLINE") else ""
            console.print(f"  {key:<16} {mark}{value}{'[/red]' if mark else ''}")
        bad = bad or not res.healthy
    if bad:
        raise SystemExit(1)


@fleet_cmd.command("run")
@click.option("--config", "config_path", type=click.Path(), default=None)
@click.option("--job", "only", multiple=True, help="Run only these job names.")
@click.option("--sequential", is_flag=True, help="One job at a time (default: parallel).")
def fleet_run_cmd(config_path, only, sequential):
    """Run every configured migration spec, in PARALLEL by default.

    Live output is interleaved with a ``[job]`` prefix; a result table with
    exit codes and per-job logs prints at the end. Exit 1 when any job fails.
    """
    from ...fleet_ops import FleetJob, run_jobs

    console = Console()
    cfg = _load_config(config_path)
    jobs = [FleetJob(j["name"], Path(j["cwd"]).resolve(), j["spec"],
                     list(j.get("args", [])))
            for j in cfg.get("jobs", [])]
    if only:
        jobs = [j for j in jobs if j.name in only]
    if not jobs:
        raise click.UsageError("no matching jobs")

    def _line(name: str, line: str) -> None:
        if any(tok in line for tok in ("→ [", "steps completed", "ERROR", "FAIL")):
            console.print(f"[dim]\\[{name}][/dim] {line}")

    results = run_jobs(jobs, parallel=not sequential, line_callback=_line)

    table = Table("job", "exit", "time", "log")
    failed = False
    for res in results:
        failed = failed or res.returncode != 0
        table.add_row(
            res.name,
            f"[{'green' if res.returncode == 0 else 'red'}]{res.returncode}[/]",
            f"{int(res.duration_s // 60)}m{int(res.duration_s % 60):02d}s",
            str(res.log_path),
        )
    console.print(table)
    if failed:
        raise SystemExit(1)
