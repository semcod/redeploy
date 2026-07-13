"""deploy command — host cockpit: change gate → live progress → timing report."""
from __future__ import annotations

import time
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table


def _fmt_s(seconds: float | None) -> str:
    if seconds is None:
        return "?"
    seconds = int(seconds)
    return f"{seconds // 60}m{seconds % 60:02d}s"


@click.command("deploy")
@click.argument("spec", type=click.Path(exists=True))
@click.option("--repo", type=click.Path(exists=True), default=".", show_default=True,
              help="Git repo whose changes ship with this deploy.")
@click.option("--remote", default=None, metavar="HOST:DIR",
              help="Target project dir — enables the exact file-delta preview.")
@click.option("--yes", is_flag=True, help="Skip the confirmation gate.")
@click.option("--gate-only", is_flag=True, help="Show the manifest and exit.")
@click.option("--prep", "prep_cmds", multiple=True, metavar="CMD",
              help="Prep commands run in PARALLEL with each other before the "
                   "engine (e.g. folder syncs + db sync simultaneously). "
                   "Any failure aborts the deploy.")
@click.option("--frozen", is_flag=True,
              help="Frozen mode: deploy the HEAD commit captured at gate time "
                   "— delta and contents come from git (archive), WIP/working-"
                   "tree edits never ship; adds --no-sync-project to the "
                   "engine automatically. Requires --remote.")
@click.option("--record", is_flag=True,
              help="After a successful deploy stamp the DEPLOYED commit as "
                   ".deploy-commit on the target (with --frozen: the frozen "
                   "commit, never the post-deploy HEAD). Requires --remote.")
@click.option("--publish-hashes/--no-publish-hashes", "publish_hashes", default=True,
              show_default=True,
              help="Before the engine, run the project's source-hash publisher "
                   "(scripts/redeploy/publish-source-hashes.sh) when present. "
                   "Stale published hashes make skip-if-image-current guards "
                   "falsely SKIP builds of changed sources (incident "
                   "2026-07-12: a green deploy left the old backend image "
                   "running).")
@click.argument("run_args", nargs=-1, type=click.UNPROCESSED)
def deploy_cmd(spec, repo, remote, yes, gate_only, prep_cmds, frozen, record, publish_hashes, run_args):
    """Deploy SPEC with host-side control: what ships, how long, live progress.

    \b
    1. GATE   — HEAD/tag, uncommitted WIP, exact delta vs the target's
                .deploy-commit, predicted duration (history) → confirm.
    2. RUN    — engine's --progress-yaml stream rendered as `step N/M`,
                per-step Δ vs previous runs, live ETA.
    3. REPORT — total time vs last run, slowest steps table.

    \b
    --frozen deploys a FROZEN state: the delta is .deploy-commit..HEAD and
    file contents ship from HEAD (git archive | ssh tar) — edits made while
    the deploy runs cannot leak into the target (incident 2026-07-10).

    \b
    Examples:
        redeploy deploy redeploy/pi109/migration.md --remote pi@host:~/c2004
        redeploy deploy redeploy/122/migration.md --repo . --yes
        redeploy deploy spec.md --remote pi@host:~/c2004 --frozen --record
        redeploy deploy spec.md --gate-only
    """
    import subprocess as sp

    from ...deploy_watch import StepHistory, build_manifest, run_with_progress

    console = Console()
    cwd = Path(repo).resolve()
    if frozen and not remote:
        raise click.UsageError("--frozen wymaga --remote HOST:DIR (cel frozen_sync)")
    if record and not remote:
        raise click.UsageError("--record wymaga --remote HOST:DIR")
    history = StepHistory.load(spec, cwd)
    manifest = build_manifest(cwd, remote=remote, history=history, frozen=frozen)

    # Frozen: zamrażamy commit JUŻ NA BRAMCE — commity/edycje zrobione w
    # trakcie wdrożenia nie zmieniają tego, co jedzie ani co stemplujemy.
    frozen_commit = None
    if frozen:
        frozen_commit = sp.check_output(
            ["git", "-C", str(cwd), "rev-parse", "HEAD"], text=True
        ).strip()

    # ── 1. gate ──────────────────────────────────────────────────────────────
    console.print(f"[bold]── bramka wdrożenia ──[/bold]  spec={spec}")
    console.print(f"  HEAD          {manifest.head}  [dim]{manifest.describe}[/dim]")
    if frozen:
        console.print(
            f"  [bold magenta]TRYB FROZEN: wdrażany commit {frozen_commit} "
            f"— pliki WIP NIE jadą[/bold magenta]"
        )
        if manifest.wip_files:
            console.print(
                f"  [dim]WIP pominięte: {len(manifest.wip_files)} plik(ów) "
                f"zostaje tylko na hoście[/dim]"
            )
    elif manifest.wip_files:
        console.print(f"  [yellow]WIP (jedzie z deployem): {len(manifest.wip_files)} plik(ów)[/yellow]")
        for path in manifest.wip_files[:8]:
            console.print(f"    [dim]{path}[/dim]")
        if len(manifest.wip_files) > 8:
            console.print(f"    [dim]… +{len(manifest.wip_files) - 8}[/dim]")
    else:
        console.print("  WIP           [green]brak — czyste drzewo[/green]")
    if remote:
        delta_label = "delta HEAD → cel" if frozen else "delta → cel  "
        if manifest.delta_error:
            console.print(f"  delta         [yellow]{manifest.delta_error}[/yellow]")
        else:
            console.print(
                f"  {delta_label} {len(manifest.delta_sync)} plik(ów), "
                f"{len(manifest.delta_delete)} usunięć"
            )
            for path in manifest.delta_sync[:8]:
                console.print(f"    [dim]{path}[/dim]")
            if len(manifest.delta_sync) > 8:
                console.print(f"    [dim]… +{len(manifest.delta_sync) - 8}[/dim]")
    if manifest.last_total_s:
        console.print(f"  poprzedni czas {_fmt_s(manifest.last_total_s)}")
    if manifest.eta_s:
        console.print(f"  przewidywany  ~{_fmt_s(manifest.eta_s)}")

    if gate_only:
        return
    if not yes and not click.confirm("Wdrożyć?", default=False):
        console.print("[yellow]przerwano na bramce[/yellow]")
        raise SystemExit(4)

    # ── 1a-bis. publish source hashes (guard skip-if-image-current) ─────────
    if publish_hashes:
        from ...source_hash import project_hash_publisher

        publisher = project_hash_publisher(cwd)
        if publisher is not None:
            import subprocess as sp

            t_pub = time.time()
            proc = sp.run(["bash", str(publisher)], cwd=str(cwd),
                          capture_output=True, text=True)
            if proc.returncode != 0:
                console.print(
                    f"[red]publikacja hashy nieudana ({publisher.name}):[/red] "
                    f"{(proc.stderr or proc.stdout)[-300:].strip()}"
                )
                raise SystemExit(5)
            scopes = sum(1 for line in proc.stdout.splitlines() if line.startswith("PASS"))
            console.print(
                f"[bold]hashe źródeł[/bold] opublikowane: {scopes} scope'ów "
                f"({_fmt_s(time.time() - t_pub)}) — guard skip-if-current aktualny"
            )

    # ── 1b. parallel prep (folders + db simultaneously) ─────────────────────
    if prep_cmds:
        import subprocess as sp
        from concurrent.futures import ThreadPoolExecutor

        t_prep = time.time()
        console.print(f"[bold]prep[/bold] {len(prep_cmds)} zadań równolegle…")

        def _prep(cmd: str):
            t = time.time()
            proc = sp.run(["bash", "-lc", cmd], cwd=str(cwd),
                          capture_output=True, text=True)
            return cmd, proc.returncode, time.time() - t, proc.stdout[-400:], proc.stderr[-400:]

        with ThreadPoolExecutor(max_workers=len(prep_cmds)) as pool:
            outcomes = list(pool.map(_prep, prep_cmds))
        prep_failed = False
        for cmd, rc, dt, out, err in outcomes:
            mark = "[green]✓[/green]" if rc == 0 else "[red]✗[/red]"
            console.print(f"  {mark} ({_fmt_s(dt)}) {cmd}")
            if rc != 0:
                prep_failed = True
                for chunk in (out, err):
                    if chunk.strip():
                        console.print(f"    [dim]{chunk.strip()[:300]}[/dim]")
        console.print(f"  prep łącznie: {_fmt_s(time.time() - t_prep)} (równolegle)")
        if prep_failed:
            console.print("[red]prep nieudany — przerywam przed silnikiem[/red]")
            raise SystemExit(5)

    # ── 1c. frozen sync (prep przed silnikiem) ───────────────────────────────
    run_args = list(run_args)
    if frozen:
        from ...gitsync import GitSyncError, frozen_sync

        host, _, remote_dir = remote.partition(":")
        console.print(
            f"[bold]frozen sync[/bold] commit {frozen_commit[:12]} → {remote} "
            f"(treść z HEAD, git archive)…"
        )
        t_frozen = time.time()
        try:
            delta = frozen_sync(cwd, host, remote_dir, base_commit=None)
        except GitSyncError as exc:
            console.print(f"[red]frozen sync nieudany: {exc}[/red]")
            raise SystemExit(5)
        console.print(
            f"  [green]✓[/green] ({_fmt_s(time.time() - t_frozen)}) "
            f"{len(delta.sync)} plik(ów), {len(delta.delete)} usunięć"
        )
        # Silnik nie może już rsyncować working tree — projekt jedzie z HEAD.
        if "--no-sync-project" not in run_args:
            run_args.append("--no-sync-project")
        # Kroki `action: rsync` w spec-u też mają jechać z zamrożonego commitu
        # (bez tego przemycają WIP working tree — incydent 2026-07-12).
        if "--frozen-commit" not in run_args:
            run_args += ["--frozen-commit", frozen_commit]

    # ── 2. run with live progress ────────────────────────────────────────────
    state = {"t0": time.time(), "total": 0}

    def on_event(kind: str, ev: dict) -> None:
        elapsed = _fmt_s(time.time() - state["t0"])
        if kind == "start":
            state["total"] = ev.get("total_steps", 0)
            console.print(f"[bold]start[/bold] {state['total']} kroków — plan (migration.md):")
            for step in ev.get("steps", []) or []:
                console.print(
                    f"  [dim]{step.get('n'):>3}. {step.get('id','')}"
                    f"  {str(step.get('description',''))[:70]}[/dim]"
                )
        elif kind == "step_start":
            n, total = ev.get("n", "?"), state["total"] or "?"
            expected = ev.get("expected_s")
            eta = ev.get("eta_s")
            suffix = ""
            if expected:
                suffix += f"  [dim]~{_fmt_s(expected)}[/dim]"
            if eta:
                suffix += f"  [dim]ETA {_fmt_s(eta)}[/dim]"
            console.print(
                f"[{elapsed}] [cyan]etap {n}/{total}[/cyan] [bold]{ev.get('id','')}[/bold]"
                f" [dim]{str(ev.get('description',''))[:60]}[/dim]{suffix}"
            )
        elif kind == "step_done":
            duration = ev.get("duration_s")
            if duration and duration > 5:
                console.print(f"[{elapsed}]   [green]✓[/green] {ev.get('id','')} ({_fmt_s(duration)})")
        elif kind == "step_fail":
            console.print(f"[{elapsed}]   [red]✗ {ev.get('id','')}: {str(ev.get('error',''))[:120]}[/red]")

    report = run_with_progress(
        spec, cwd, extra_args=run_args, history=history, on_event=on_event
    )

    # ── 3. report ────────────────────────────────────────────────────────────
    console.print()
    status = "[green]OK[/green]" if report.returncode == 0 else f"[red]exit={report.returncode}[/red]"
    delta_last = ""
    if history.totals[:-1] and report.returncode == 0:
        prev = history.totals[-2] if len(history.totals) >= 2 else None
        if prev:
            sign = "+" if report.total_s > prev else "−"
            delta_last = f"  (Δ {sign}{_fmt_s(abs(report.total_s - prev))} vs poprzedni)"
    console.print(
        f"[bold]── wynik ──[/bold] {status}  "
        f"{report.completed}/{report.total_steps} kroków  "
        f"czas {_fmt_s(report.total_s)}{delta_last}"
    )
    if report.failed_step:
        console.print(f"  [red]padł krok: {report.failed_step}[/red]  log: {report.log_path}")
    slowest = sorted(report.durations.items(), key=lambda kv: -kv[1])[:5]
    if slowest:
        table = Table("najwolniejsze kroki", "czas", box=None)
        for sid, duration in slowest:
            table.add_row(sid, _fmt_s(duration))
        console.print(table)
    console.print(f"[dim]log silnika: {report.log_path}[/dim]")
    if record and report.returncode == 0:
        from ...gitsync import record_deploy_commit

        host, _, remote_dir = remote.partition(":")
        # W trybie frozen stemplujemy commit ZAMROŻONY na bramce — commity
        # zrobione W TRAKCIE deployu nie dojechały i nie mogą być oznaczone
        # jako wdrożone (incydent 2026-07-10).
        stamped = record_deploy_commit(cwd, host, remote_dir, commit=frozen_commit)
        suffix = " (frozen — nie bieżący HEAD)" if frozen else ""
        console.print(f"  [dim].deploy-commit → {stamped[:12]}{suffix}[/dim]")
    if report.returncode != 0:
        raise SystemExit(report.returncode)
