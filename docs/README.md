<!-- code2docs:start --># redeploy

![version](https://img.shields.io/badge/version-0.1.0-blue) ![python](https://img.shields.io/badge/python-%3E%3D3.11-blue) ![coverage](https://img.shields.io/badge/coverage-unknown-lightgrey) ![functions](https://img.shields.io/badge/functions-985-green)
> **985** functions | **179** classes | **317** files | CC̄ = 5.0

> Auto-generated project documentation from source code analysis.

**Author:** Tom Softreck <tom@sapletta.com>  
**License:** Apache-2.0  
**Repository:** [https://github.com/maskservice/redeploy](https://github.com/maskservice/redeploy)

## Installation

### From PyPI

```bash
pip install redeploy
```

### From Source

```bash
git clone https://github.com/maskservice/redeploy
cd redeploy
pip install -e .
```

### Optional Extras

```bash
pip install redeploy[dev]    # development tools
pip install redeploy[op3]    # op3 features
pip install redeploy[mcp]    # mcp features
```

## Quick Start

### CLI Usage

```bash
# Generate full documentation for your project
redeploy ./my-project

# Only regenerate README
redeploy ./my-project --readme-only

# Preview what would be generated (no file writes)
redeploy ./my-project --dry-run

# Check documentation health
redeploy check ./my-project

# Sync — regenerate only changed modules
redeploy sync ./my-project
```

### Python API

```python
from redeploy import generate_readme, generate_docs, Code2DocsConfig

# Quick: generate README
generate_readme("./my-project")

# Full: generate all documentation
config = Code2DocsConfig(project_name="mylib", verbose=True)
docs = generate_docs("./my-project", config=config)
```




## Architecture

```
redeploy/
├── goal
├── REFACTORING
├── Makefile
├── REPAIR_LOG
├── DOQL-INTEGRATION
├── pyqual
├── sumd
├── pyproject
├── tree
├── TODO
├── CHANGELOG
├── project
├── README
    ├── patterns
    ├── markpact-implementation-plan
    ├── fleet
    ├── dsl-migration
    ├── op3-migration
    ├── observe
    ├── README
    ├── markpact-audit
        ├── README
    ├── version/
    ├── schema
    ├── observe
    ├── cli/
    ├── data_sync
    ├── heal/
├── redeploy/
    ├── parse
    ├── fleet
    ├── verify
    ├── spec_loader
    ├── ssh
    ├── patterns
    ├── mcp_server
        ├── process_control_template
        ├── detector
    ├── detect/
        ├── remote
        ├── hardware
        ├── hardware_rules
        ├── templates
        ├── workflow
        ├── probes
        ├── builtin/
            ├── templates
        ├── decider
        ├── hint_provider
        ├── loop_detector
        ├── runner
        ├── log_writer
        ├── process
        ├── docker
        ├── kiosk
    ├── steps/
        ├── scm
        ├── hardware
        ├── k3s
        ├── podman
        ├── transfer
        ├── generic
        ├── ssh_credentials
        ├── helpers
        ├── registry
        ├── auto_probe
    ├── discovery/
    ├── discovery_probe
        ├── types
        ├── scanners
    ├── analyze/
        ├── spec_analyzer
        ├── models
        ├── ignore
        ├── preflight_schema
            ├── base
            ├── path
        ├── checkers/
            ├── compose
            ├── command_ref
            ├── binary
            ├── env
            ├── docker_build
            ├── reference
        ├── applier
        ├── loader
    ├── config_apply/
            ├── display
        ├── handlers/
        ├── devices
        ├── persisted
        ├── plan
        ├── blueprint
        ├── manifest
    ├── models/
        ├── hardware
        ├── pipeline
        ├── infra
        ├── enums
        ├── spec
        ├── display
        ├── query
        ├── core
            ├── plan_apply_report
            ├── target
            ├── devices
            ├── state
            ├── inspect
            ├── device_map_renderers
            ├── bump_fix
            ├── exec_
            ├── blueprint
            ├── export
            ├── init
            ├── status
            ├── probe
            ├── mcp_cmd
            ├── plugin
            ├── import_
            ├── plan_apply
        ├── commands/
            ├── detect
            ├── migrate_cmd
            ├── gh_workflow
            ├── device_map
            ├── hardware
            ├── run_cmd
            ├── lint
            ├── devices_display
            ├── prompt_cmd
            ├── diff
            ├── plan_apply_run
            ├── workflow
            ├── plan_apply_shared
            ├── push
            ├── patterns
            ├── plan_cmd
            ├── diagnose
            ├── audit
            ├── probe_display
            ├── apply_cmd
            ├── device_map_actions
                ├── monorepo
                ├── commands
                ├── helpers
            ├── version/
                ├── release
                ├── scanner
                ├── utils/
                    ├── git_config
                    ├── changelog_config
        ├── probe
    ├── audit/
        ├── extractor
        ├── paths
        ├── models
        ├── patterns
        ├── auditor
    ├── plugins/
            ├── notify
        ├── builtin/
            ├── process_control
            ├── browser_reload
            ├── systemd_reload
            ├── hardware_diagnostic
        ├── steps
        ├── exceptions
        ├── runner
    ├── dsl_python/
        ├── docker_steps
        ├── context
        ├── decorators
        ├── panels
        ├── config_txt
    ├── hardware/
        ├── fixes
        ├── raspi_config
        ├── kiosk/
            ├── browsers
            ├── autostart
            ├── output_profiles
            ├── compositors
        ├── data/
            ├── waveshare
            ├── official
            ├── hyperpixel
    ├── markpact/
        ├── parser
        ├── models
        ├── compiler
        ├── progress
        ├── exceptions
        ├── state
    ├── apply/
        ├── state_apply
        ├── handlers
        ├── executor
        ├── rollback
            ├── run_container_build
        ├── utils/
        ├── bump
        ├── git_transaction
        ├── transaction
        ├── changelog
        ├── manifest
        ├── git_integration
        ├── diff
        ├── commits
            ├── base
            ├── toml_
            ├── regex
            ├── yaml_
        ├── sources/
            ├── plain
            ├── json_
    ├── plan/
        ├── planner
    ├── blueprint/
        ├── extractor
        ├── sources/
            ├── hardware
            ├── compose
            ├── infra
            ├── migration
            ├── docker_compose
        ├── generators/
            ├── migration
    ├── integrations/
        ├── op3_bridge
        ├── loader
    ├── dsl/
        ├── parser
        ├── docker_compose
        ├── base
        ├── registry
    ├── iac/
        ├── config_hints
        ├── parsers/
            ├── compose
    ├── README
        ├── rpi5-waveshare-kiosk
        ├── enable-i2c-spi
        ├── waveshare-8-inch-dsi
        ├── official-dsi-7-inch
        ├── argocd_flux
        ├── helm_kustomize
        ├── gitops_ci
        ├── helm_ansible
        ├── README
            ├── migration
            ├── README
            ├── migration
            ├── migration
            ├── README
            ├── migration
            ├── migration
            ├── migration
            ├── README
            ├── migration
        ├── 16-auto-rollback
        ├── 14-blue-green
        ├── 15-canary
        ├── 13-kiosk-appliance
            ├── redeploy
            ├── migration
            ├── README
            ├── redeploy
            ├── migration
            ├── README
            ├── migration
            ├── README
            ├── redeploy
            ├── fleet
            ├── README
            ├── migration
            ├── README
                    ├── tls
            ├── dev
            ├── staging
            ├── redeploy
            ├── prod
            ├── README
            ├── migration
            ├── README
            ├── redeploy
            ├── migration
            ├── README
            ├── redeploy
            ├── migration
            ├── README
            ├── migration-rpi5
                ├── gitlab
                ├── github
            ├── redeploy
            ├── migration
            ├── README
            ├── migration
            ├── README
            ├── migration
            ├── README
            ├── redeploy
            ├── fleet
            ├── migration
            ├── README
    ├── quality_gate
    ├── hardware-108
    ├── hardware-109
            ├── toon
            ├── toon
```

## API Overview

### Classes

- **`AuditEntry`** — Single audit log entry — immutable snapshot of one deployment.
- **`DeployAuditLog`** — Persistent audit log — newline-delimited JSON at ``path``.
- **`DeployReport`** — Human-readable post-deploy report from an AuditEntry.
- **`HealLoopDetector`** — Detect repeated non-converging heal hints for a given step.
- **`HealRunner`** — Wraps Executor with self-healing loop.
- **`DeviceArch`** — —
- **`Stage`** — —
- **`DeviceExpectation`** — Declarative assertions about required infrastructure on a device.
- **`FleetDevice`** — Generic device descriptor — superset of ``deploy``'s DeviceConfig.
- **`FleetConfig`** — Top-level fleet manifest — list of devices with stage / tag organisation.
- **`Fleet`** — Unified first-class fleet — wraps FleetConfig and/or DeviceRegistry.
- **`VerifyContext`** — Accumulates check results during verification.
- **`SpecLoaderError`** — Base error raised when a deployment spec cannot be loaded.
- **`UnsupportedSpecFormatError`** — Raised when the spec file uses an unsupported format.
- **`SshResult`** — —
- **`SshClient`** — Execute commands on a remote host via SSH (or locally).
- **`RemoteProbe`** — Thin wrapper kept for redeploy.detect compatibility.
- **`RemoteExecutor`** — Thin wrapper kept for deploy.core compatibility.
- **`DeployPattern`** — Base class for all deploy patterns.
- **`BlueGreenPattern`** — Zero-downtime blue/green deploy via Traefik (or any label-based proxy).
- **`CanaryPattern`** — Gradual canary rollout: deploy new version, scale up in stages.
- **`RollbackOnFailurePattern`** — Capture pre-deploy image tag, roll back automatically on failure.
- **`Detector`** — Probe infrastructure and produce InfraState.
- **`Condition`** — A single scoreable condition.
- **`DetectionTemplate`** — Named template for a device+environment+strategy combination.
- **`FactExtractor`** — Extract a single key/value pair into the context dict.
- **`TemplateMatch`** — Scored template match.
- **`DetectionResult`** — Full result of template-based detection.
- **`TemplateEngine`** — Score all templates against a context and return ranked matches.
- **`HostDetectionResult`** — Full detection result for a single host.
- **`WorkflowResult`** — Aggregated result across all probed hosts.
- **`DetectionWorkflow`** — Multi-host detection workflow with template scoring.
- **`Action`** — —
- **`Decision`** — —
- **`HealAbort`** — Raised when a heal loop is detected and retries must stop.
- **`HealLoopDetector`** — Detect repeated non-converging heal hints for a given step.
- **`HealRunner`** — Wraps :class:`Executor` with a self-healing loop.
- **`StepLibrary`** — Registry of pre-defined named MigrationSteps.
- **`DiscoveredHost`** — —
- **`ProbeResult`** — Full autonomous probe result for a single host.
- **`SpecAnalyzer`** — Run static checks against a compiled MigrationSpec (and optional raw MarkpactDocument).
- **`IssueSeverity`** — —
- **`Issue`** — —
- **`AnalysisResult`** — —
- **`IgnoreList`** — Read .gitignore and .redeployignore patterns and test if paths are ignored.
- **`PreflightResult`** — —
- **`Checker`** — —
- **`PathChecker`** — Validate local file paths referenced by steps.
- **`CommandPathChecker`** — Scan command strings for hardcoded absolute paths outside the project.
- **`ComposeChecker`** — Validate docker-compose files declared in spec or found in project.
- **`CommandRefChecker`** — Validate command_ref references for nested markdown/script dependencies.
- **`BinaryChecker`** — Warn if commands reference binaries not available locally (best-effort).
- **`EnvFileChecker`** — Check that .env referenced by target.env_file exists.
- **`DockerBuildChecker`** — Validate docker build commands: Dockerfile exists, context is consistent.
- **`ReferenceChecker`** — Ensure command_ref and insert_before point to existing things.
- **`DeployRecord`** — Single deployment event recorded for a device.
- **`KnownDevice`** — Device known to redeploy — persisted in ~/.config/redeploy/devices.yaml.
- **`DeviceMap`** — Full, persisted snapshot of a device: identity + InfraState + HardwareInfo.
- **`DeviceRegistry`** — Persistent device registry — stored at ~/.config/redeploy/devices.yaml.
- **`PersistedModel`** — Mixin for models that can be persisted to/from YAML files.
- **`MigrationStep`** — —
- **`MigrationPlan`** — Full migration plan — output of `plan`, input to `apply`.
- **`ServicePort`** — —
- **`VolumeMount`** — —
- **`ServiceSpec`** — —
- **`HardwareRequirements`** — —
- **`BlueprintSource`** — —
- **`DeviceBlueprint`** — Self-contained, portable deployment recipe.
- **`EnvironmentConfig`** — One named environment in redeploy.yaml.
- **`ProjectManifest`** — Per-project redeploy.yaml — replaces repetitive Makefile variables.
- **`DrmOutput`** — One DRM connector (e.g. card1-DSI-2, card2-HDMI-A-1).
- **`BacklightInfo`** — Sysfs backlight device.
- **`I2CBusInfo`** — —
- **`HardwareDiagnostic`** — Problem found during hardware probe.
- **`HardwareInfo`** — Hardware state produced by hardware probe.
- **`Hook`** — Generyczny hook w pipeline: faza + akcja + opcjonalny warunek.
- **`ServiceInfo`** — —
- **`PortInfo`** — —
- **`ConflictInfo`** — —
- **`RuntimeInfo`** — —
- **`AppHealthInfo`** — —
- **`InfraState`** — Full detected state of infrastructure — output of `detect`.
- **`ConflictSeverity`** — —
- **`StepAction`** — —
- **`StepStatus`** — —
- **`DeployStrategy`** — —
- **`TargetConfig`** — Desired infrastructure state — input to `plan`.
- **`InfraSpec`** — Declarative description of one infrastructure state (from OR to).
- **`MigrationSpec`** — Single YAML file describing full migration: from-state → to-state.
- **`Probe`** — Thin wrapper around SshClient with sensible audit timeouts.
- **`Extractor`** — Walk a MigrationSpec and emit Expect tuples.
- **`AuditCheck`** — Outcome of a single audit probe.
- **`AuditReport`** — —
- **`Expect`** — —
- **`Auditor`** — —
- **`PluginContext`** — Passed to every plugin handler.
- **`PluginRegistry`** — Central registry mapping plugin_type strings to handler callables.
- **`HardwareInfo`** — Hardware diagnostic information.
- **`DSLException`** — Base exception for DSL errors.
- **`StepError`** — Raised when a step fails.
- **`TimeoutError`** — Raised when a step times out.
- **`VerificationError`** — Raised when verification fails.
- **`ConnectionError`** — Raised when SSH/connection fails.
- **`RollbackError`** — Raised when rollback fails.
- **`PythonMigrationRunner`** — Runner for Python-based migrations.
- **`DockerComposeResult`** — Result of docker compose command.
- **`DockerDSL`** — Docker-related DSL actions.
- **`StepContext`** — Tracks the execution of a single step.
- **`MigrationMeta`** — Metadata for a migration.
- **`MigrationRegistry`** — Global registry of migration functions.
- **`StepManager`** — Manages step execution and tracking.
- **`step`** — Context manager for a deployment step.
- **`PanelDefinition`** — Definition of a Raspberry Pi display panel.
- **`ConfigEdit`** — Result of a config.txt edit operation.
- **`BrowserKioskProfile`** — Static definition of a browser kiosk launch profile.
- **`AutostartEntry`** — One entry in a compositor autostart file.
- **`OutputProfile`** — A kanshi output profile definition.
- **`CompositorDefinition`** — Static definition of a Wayland compositor for kiosk use.
- **`MarkpactParseError`** — Raised when a markdown markpact document cannot be parsed.
- **`MarkpactBlock`** — —
- **`MarkpactDocument`** — —
- **`MarkpactCompileError`** — Raised when a markpact document cannot be compiled to MigrationSpec.
- **`ProgressEmitter`** — Emits YAML-formatted progress events to a stream (default: stdout).
- **`StepError`** — Exception raised when a migration step fails.
- **`ResumeState`** — Checkpoint for a single MigrationPlan execution.
- **`ApplyResult`** — —
- **`StateHandler`** — Base class for a declarative state applier.
- **`HardwareStateHandler`** — Applies HardwareInfo-shaped YAML: display transforms, backlight, etc.
- **`InfraStateHandler`** — Placeholder — applies InfraState-shaped YAML (services, ports, etc.).
- **`Executor`** — Execute MigrationPlan steps on a remote host.
- **`GitTransactionResult`** — Result of full version bump transaction with git.
- **`GitVersionBumpTransaction`** — Version bump transaction with Git integration.
- **`StagingResult`** — Result of staging one source.
- **`VersionBumpTransaction`** — Atomic transaction for bumping version across multiple sources.
- **`ChangelogManager`** — Manage CHANGELOG.md in keep-a-changelog format.
- **`SourceConfig`** — Single source of version truth (one file).
- **`GitConfig`** — Git integration settings.
- **`ChangelogConfig`** — Changelog generation settings.
- **`CommitRules`** — Conventional commits → bump type mapping.
- **`CommitsConfig`** — Conventional commits analysis settings.
- **`PackageConfig`** — Single package in monorepo (for policy=independent).
- **`Constraint`** — Cross-package version constraint.
- **`VersionManifest`** — Root manifest model for .redeploy/version.yaml.
- **`GitIntegrationError`** — Git operation failed.
- **`GitIntegration`** — Git operations for version management.
- **`VersionDiff`** — Version comparison result.
- **`ConventionalCommit`** — Parsed conventional commit.
- **`BumpAnalysis`** — Result of analyzing commits for bump decision.
- **`BaseAdapter`** — Base class for source adapters with common utilities.
- **`TomlAdapter`** — Read/write version from TOML files using tomllib/tomli.
- **`RegexAdapter`** — Read/write version using regex pattern with capture group.
- **`YamlAdapter`** — Read/write version from YAML files.
- **`SourceAdapter`** — Protocol for version source adapters.
- **`PlainAdapter`** — Read/write version from plain text file.
- **`JsonAdapter`** — Read/write version from JSON files.
- **`Planner`** — Generate a MigrationPlan from detected infra + desired target.
- **`WorkflowStep`** — —
- **`WorkflowDef`** — Named deployment workflow parsed from ``workflow[name="…"] { … }``.
- **`LoadResult`** — Full result of loading a ``redeploy.css`` file.
- **`DSLNode`** — One parsed block from the CSS-like file.
- **`RedeployDSLParser`** — Parse a ``redeploy.css`` or ``redeploy.less`` file into a list of DSLNode objects.
- **`DockerComposeParser`** — Parser for docker-compose.yml / compose.yaml files.
- **`PortInfo`** — A published / exposed port mapping.
- **`VolumeInfo`** — A volume or bind-mount.
- **`ServiceInfo`** — One logical service / container / pod / deployment.
- **`ConversionWarning`** — A warning emitted by a parser or converter about lossy / uncertain data.
- **`ParsedSpec`** — Common intermediate representation from any IaC/CI-CD parser.
- **`Parser`** — Protocol every format-specific parser must satisfy.
- **`ParserRegistry`** — Dispatch file → registered parser.
- **`ConfigHintsParser`** — Best-effort parser for common DevOps/IaC config files.
- **`DockerComposeParser`** — Parser for Docker Compose files (v2 + v3 schema, Compose Spec).
- **`ArgoCDApplicationParser`** — —
- **`FluxKustomizationParser`** — —
- **`HelmTemplatesParser`** — —
- **`KustomizationParser`** — —
- **`GitHubActionsGitOpsParser`** — —
- **`GitLabCIGitOpsParser`** — —
- **`HelmChartParser`** — —
- **`AnsiblePlaybookParser`** — —

### Functions

- `build_schema(root)` — Build the workspace schema dict.
- `collect_sqlite_counts(app_root, db_specs)` — Collect row counts for the given SQLite tables under *app_root*.
- `rsync_timeout_for_path(path, minimum, base, per_mb)` — Compute a conservative rsync timeout based on file size (seconds).
- `collect_diagnostics(host, failed_step)` — Run targeted SSH diagnostics for a failed step, return combined output.
- `ask_llm(failed_step, step_output, diag, spec_text)` — Ask LiteLLM to propose a fixed YAML block for the failed step.
- `apply_fix_to_spec(spec_path, failed_step, llm_response)` — Extract YAML block from LLM response and patch it into the spec file.
- `write_repair_log(spec_path, version, repairs)` — Write/update REPAIR_LOG.md adjacent to spec file.
- `parse_failed_step(executor_summary, executor)` — Extract (step_id, step_output) from executor state or summary string.
- `parse_docker_ps(output)` — Parse 'docker ps --format "{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}|{{.State}}"' output.
- `parse_container_line(line)` — Parse a single NAME|STATUS|IMAGE pipe-delimited container line.
- `parse_system_info(output)` — Parse KEY:VALUE system info lines (HOSTNAME, UPTIME, DISK, MEM, LOAD) into a dict.
- `parse_diagnostics(output)` — Parse multi-section SSH diagnostics output into structured dict.
- `parse_health_info(output)` — Parse health-check SSH output (HOSTNAME, UPTIME, HEALTH, DISK, LOAD) into a dict.
- `verify_data_integrity(ctx, local_counts, remote_counts)` — Compare local vs remote SQLite row counts and record results in *ctx*.
- `load_migration_spec(path)` — Load a deployment spec from disk.
- `get_pattern(name)` — Return pattern class by name, or None if not found.
- `list_patterns()` — Return all registered pattern names.
- `schema(directory)` — Discover the workspace: find migration specs, read version, git branch.
- `plan_spec(spec, cwd)` — Preview a migration spec: show all steps without executing anything.
- `run_spec(spec, force, dry_run, heal)` — Apply a migration spec.
- `fix_spec(spec_or_dir, hint, bump, retries)` — Self-healing deploy: bump version → apply spec → LLM retry on failure.
- `bump_version(spec_or_dir, level, cwd)` — Bump the project version and update migration spec header.
- `diagnose(host)` — Run SSH diagnostics on a deployment target and return system state.
- `list_specs(directory)` — List all migration specs found in a directory.
- `exec_ssh(host, command)` — Run an ad-hoc SSH command on a remote host.
- `nlp_command(instruction, dry_run, cwd)` — Translate a natural-language instruction into a redeploy command and run it.
- `get_spec_content(path)` — Read the raw content of a migration spec file.
- `get_workspace()` — Return the workspace schema as JSON string.
- `serve(transport, host, port)` — Start the MCP server.
- `probe_hardware(p)` — Probe hardware state of the remote host and return ``HardwareInfo``.
- `analyze(hw)` — Run all diagnostic rules against *hw* and return findings.
- `build_context(state, probe, manifest)` — Flatten InfraState + ProbeResult into a flat dict for condition evaluation.
- `probe_runtime(p)` — Detect installed runtimes: docker, k3s, podman, systemd.
- `probe_ports(p)` — Detect listening ports and which process owns them.
- `probe_iptables_dnat(p, ports)` — Find iptables DNAT rules stealing specific ports (returns [(port, target_ip)]).
- `probe_docker_services(p)` — List running Docker containers.
- `probe_k3s_services(p, namespaces)` — List running k3s pods.
- `probe_systemd_services(p, app)` — List app-related systemd units (also catches kiosk/chromium/openbox).
- `probe_health(host, app, domain)` — HTTP health checks against known endpoints.
- `detect_conflicts(ports, iptables_dnat, runtime, docker_services)` — Identify conflicts: port stealing, duplicate services, etc.
- `detect_strategy(runtime, docker_services, k3s_services, systemd_services)` — Infer the current deployment strategy from detected services.
- `decide_after_failure()` — Return the next action for the heal loop.
- `format_decision_message(decision, step_id)` — Human-readable log / console message for a decision.
- `collect_diagnostics(host, failed_step)` — Run targeted SSH diagnostics for a failed step, return combined output.
- `ask_llm(failed_step, step_output, diag, spec_text)` — Ask LiteLLM to propose a fixed YAML block for the failed step.
- `apply_fix_to_spec(spec_path, failed_step, llm_response)` — Extract YAML block from LLM response and patch it into the spec file.
- `parse_failed_step(executor_summary, executor)` — Extract (step_id, step_output) from executor state or summary string.
- `write_repair_log(spec_path, version, repairs)` — Append an entry to *REPAIR_LOG.md* adjacent to the spec file.
- `collect_ssh_keys()` — —
- `tcp_reachable(ip, port, timeout)` — —
- `try_ssh_credentials(ip, users, keys, port)` — —
- `is_raspberry_pi_mac(mac)` — —
- `run_shell(cmd, timeout)` — —
- `is_ip(value)` — —
- `update_registry(hosts, registry, save)` — Merge discovered hosts into DeviceRegistry and optionally save.
- `parse_probe_input(ip_or_host, users)` — —
- `build_probe_command()` — —
- `build_ssh_command(host, port, timeout, key_opts)` — —
- `run_ssh_probe(cmd, timeout)` — —
- `detect_strategy_remote(host, key, port, timeout)` — —
- `detect_app_from_services(services, app_hint)` — —
- `auto_probe(ip_or_host, users, port, timeout)` — —
- `parse_probe_output(out)` — —
- `infer_strategy(info, services)` — —
- `scan_known_hosts(ssh_user)` — —
- `scan_arp_cache()` — —
- `scan_mdns(timeout)` — —
- `ping_sweep(subnet, timeout)` — —
- `probe_ssh_batch(hosts, users, port, timeout)` — —
- `detect_local_subnet()` — —
- `merge_hosts(hosts)` — —
- `discover(subnet, ssh_users, ssh_port, ping)` — —
- `ensure_redeployignore(base_dir)` — Create .redeployignore with sensible defaults if it doesn't exist.
- `generate_preflight_schema()` — —
- `save_preflight_schema(schema, output_path)` — —
- `resolve_local_path(val, base_dir)` — —
- `is_inside(path, base)` — —
- `scan_compose_file(path, base_dir, result, ign)` — —
- `extract_binaries(cmd)` — —
- `collect_sync_mappings(spec)` — —
- `parse_docker_build(cmd)` — —
- `match_local_src(sync_mappings, remote_context)` — —
- `resolve_local_dockerfile(local_src, dockerfile, base_dir)` — —
- `apply_config_dict(data, probe, console)` — Apply *data* to the host behind *probe*.
- `apply_config_file(path)` — Load *path* and apply its hardware/infra settings to the remote host.
- `load_config_file(path)` — Read *path* and return a dict (YAML or JSON auto-detected).
- `apply_display_transform(console, probe, output_name, transform)` — Apply *transform* to *output_name* via wlr-randr and persist in kanshi config.
- `print_plan_table(console, migration)` — Print migration plan as a table.
- `print_infrastructure_summary(console, state, host)` — Print infrastructure summary from detection state.
- `print_docker_services(console, state)` — Print Docker container status.
- `print_k3s_pods(console, state)` — Print k3s pod status.
- `print_conflicts(console, state)` — Print detection conflicts.
- `print_inspect_app_metadata(console, result)` — Print app metadata from inspect result.
- `print_inspect_environments(console, result)` — Print environments from inspect result.
- `print_inspect_templates(console, result)` — Print detection templates from inspect result.
- `print_inspect_workflows(console, result)` — Print workflows from inspect result.
- `print_inspect_devices(console, result)` — Print devices from inspect result.
- `print_inspect_raw_nodes_summary(console, result)` — Print raw nodes summary from inspect result.
- `print_workflow_summary_table(console, result)` — Print workflow summary as a table.
- `print_workflow_host_details(console, result)` — Print detailed host information from workflow result.
- `generate_workflow_output_css(console, result, app, save_yaml)` — Generate and display/save CSS output from workflow.
- `generate_workflow_output_yaml(console, result, save_yaml)` — Generate and display/save YAML output from workflow.
- `print_import_spec(console, spec)` — Print a ParsedSpec summary to the Rich console.
- `execute_query(obj, query_expr, output_fmt, echo)` — Run a JMESPath *query_expr* against *obj* and echo the result.
- `cli(ctx, verbose)` — redeploy — Infrastructure migration toolkit: detect → plan → apply
- `load_spec_or_exit(console, path)` — Load a migration spec or exit with error.
- `find_manifest_path()` — Find redeploy.yaml manifest in current or parent directories.
- `resolve_device(console, device_id)` — Resolve device from registry or auto-probe.
- `load_spec_with_manifest(console, spec_file, dev)` — Load spec and apply manifest/device overlays.
- `overlay_device_onto_spec(spec, dev, console)` — Overlay device values onto spec target configuration.
- `run_detect_for_spec(console, spec, do_detect)` — Run detect if requested and return planner.
- `run_detect_workflow(console, hosts, manifest, app)` — Run DetectionWorkflow and print rich report.
- `default_report_path(spec_path)` — —
- `resolve_audit_entry(migration, started_at, ok)` — —
- `step_command_block(step)` — —
- `build_checksum_verification(migration, executed)` — Build post-deploy sync verification with checksum-aware rsync dry-run.
- `render_markdown_report(entry, migration, spec_path, checksum)` — —
- `write_markdown_report(console, migration, spec_path, started_at)` — —
- `target(device_id, spec_file, dry_run, plan_only)` — Deploy a spec to a specific registered device.
- `devices(tag, strategy, rpi, reachable)` — List known devices from ~/.config/redeploy/devices.yaml.
- `scan(subnet, ssh_users, ssh_port, ping)` — Discover SSH-accessible devices on the local network.
- `device_add(host, device_id, name, tags)` — Add or update a device in the registry.
- `device_rm(device_id)` — Remove a device from the registry.
- `state_cmd(ctx, action, spec_file, host)` — Inspect or clear resume checkpoints.
- `inspect(ctx, css_file)` — Show parsed content of redeploy.css — environments, templates, workflows.
- `render_yaml(dm)` — Emit *dm* as YAML to stdout.
- `render_json(dm)` — Emit *dm* as indented JSON to stdout.
- `render_rich(console, dm)` — Full rich console report with hardware, infra and issues tables.
- `bump_cmd(spec_or_dir, minor, major)` — Bump the project version (patch by default).
- `fix_cmd(spec_or_dir, hint, bump, minor)` — Self-healing deploy: bump version, then run with LLM auto-fix on failure.
- `exec_cmd(ctx, ref, host, markdown_file)` — Execute a script from a markdown codeblock by reference.
- `exec_multi_cmd(ctx, refs, host, markdown_file)` — Execute multiple scripts from markdown codeblocks by reference.
- `blueprint_cmd()` — Extract, generate and apply DeviceBlueprints (portable deploy recipes).
- `capture(host, name, compose_files, migration_file)` — Probe HOST and extract a DeviceBlueprint from all available sources.
- `twin(blueprint_file, out_path, platform, port_offset)` — Generate a docker-compose.twin.yml from BLUEPRINT_FILE for local testing.
- `deploy(blueprint_file, target_host, out_path, remote_dir)` — Generate (and optionally run) a migration.yaml for TARGET_HOST from BLUEPRINT_FILE.
- `show(blueprint_file, fmt, apply_config, query_expr)` — Display a saved DeviceBlueprint.
- `list_blueprints()` — List all saved DeviceBlueprints.
- `export_cmd(ctx, output, src_file, fmt)` — Convert between redeploy.css and redeploy.yaml formats.
- `init(host, app, domain, strategy)` — Scaffold migration.yaml + redeploy.yaml for this project.
- `status(spec_file)` — Show current project manifest and spec summary.
- `probe(hosts, subnet, users, ssh_port)` — Autonomously probe one or more hosts — detect SSH credentials, strategy, app.
- `mcp_cmd(transport, host, port)` — Start the redeploy MCP server.
- `plugin_cmd(ctx, subcommand, name)` — List or inspect registered redeploy plugins.
- `import_cmd(source, output, target_host, target_strategy)` — Parse an IaC/CI-CD file and produce a migration.yaml scaffold.
- `detect(ctx, host, app, domain)` — Probe infrastructure and produce infra.yaml.
- `migrate(ctx, host, app, domain)` — Full pipeline: detect → plan → apply.
- `gh_workflow_cmd()` — Inspect and run GitHub Actions workflows on demand.
- `gh_workflow_list(repo_root)` — List workflow files and whether they are dispatchable.
- `gh_workflow_analyze(workflow, repo_root)` — Analyze one workflow (or all workflows) for triggers/jobs/dispatch readiness.
- `gh_workflow_run(workflow, repo_root, ref, fields)` — Trigger a GitHub Actions workflow_dispatch run on demand via gh CLI.
- `device_map_cmd(host, name, tags, save)` — Generate a full standardized device snapshot (hardware + infra + diagnostics).
- `hardware(host, output_fmt, show_fix, apply_fix_component)` — Probe and diagnose hardware on a remote host.
- `run(ctx, spec_file, dry_run, plan_only)` — Execute migration from a single YAML spec (source + target in one file).
- `lint(ctx, spec_file, env_name, as_json)` — Static analysis of a migration spec (YAML or markpact .md).
- `filter_devices(devices)` — —
- `render_devices_table(console, devices)` — —
- `prompt_cmd(instruction, schema_only, dry_run, yes)` — Natural-language → redeploy command via LLM.
- `diff(ci_file, host, from_src, to_src)` — Compare IaC file vs live host (drift detection).  [Phase 3 — coming soon]
- `setup_run_logging(resolved_spec)` — Attach file logging; return (handler_id, log_file, started_at).
- `run_lint_phase(console, resolved_spec, lint, file_handler_id)` — Run static lint when enabled; exit process on hard failures.
- `run_preflight_phase(console)` — Generate preflight schema and optionally abort on blockers.
- `workflow_cmd(ctx, name, css_file, dry_run)` — Run a named workflow from redeploy.css.
- `apply_manifest_to_spec(console, manifest, spec, env_name)` — —
- `print_spec_summary(console, spec)` — —
- `perform_live_detect(console, spec)` — —
- `run_apply(console, migration, dry_run, output)` — —
- `load_dotenv_for_heal()` — —
- `detect_project_version(spec_path)` — —
- `print_heal_banner(console, fix_hint)` — —
- `ensure_redeployignore(project_root, console)` — —
- `inject_project_sync_step(migration, spec, project_root, console)` — —
- `load_spec_for_run(console, spec_file, manifest)` — —
- `push(host, files, dry_run, ssh_key)` — Apply desired-state YAML/JSON file(s) to a remote host.
- `patterns(name)` — List available deploy patterns or show detail for one.
- `plan(ctx, infra, target, strategy)` — Generate migration-plan.yaml from infra.yaml + target config.
- `diagnose(ctx, spec, host, ssh_key)` — Compare a migration spec against the live target host.
- `audit(last, host, app, only_failed)` — Show deploy audit log from ~/.config/redeploy/audit.jsonl.
- `collect_probe_hosts(hosts, subnet, console)` — —
- `print_probe_line(console, ip, result)` — —
- `print_reachable_devices_table(console, results)` — —
- `apply(ctx, plan_file, dry_run, step)` — Execute a migration plan.
- `print_saved_maps(console)` — —
- `print_device_map_diff(console, path_a, path_b)` — —
- `probe_device_map(console, host)` — —
- `execute_query_device_map(console, dm, query_expr, output_fmt)` — —
- `emit_device_map(dm, output_fmt)` — —
- `version_cmd()` — Declarative version management: bump, verify, diff.
- `version_current(manifest, package_name, all_packages)` — Show current version from manifest.
- `version_list(manifest, package_name, all_packages)` — List all version sources and their values.
- `version_verify(manifest, package_name, all_packages)` — Verify all sources match manifest version.
- `version_bump(type, manifest, package, all_packages)` — Bump version across all sources atomically.
- `version_set(version, manifest_path_str, package_name, all_packages)` — Set an explicit version across all manifest sources.
- `version_init(scan, review, interactive, excluded_paths)` — Initialize .redeploy/version.yaml manifest.
- `version_diff(manifest, package_name, all_packages, spec)` — Compare manifest version vs spec vs live.
- `resolve_package_release_git_config(manifest_model, package_name)` — Return the git config for *package_name* with optional root fallback.
- `resolve_package_release_changelog_config(manifest_model, package_name)` — Return the changelog config for *package_name* with optional root fallback.
- `audit_spec(spec_path)` — Convenience: load spec from file and run an audit.
- `extract_port(url)` — —
- `normalize_path(path)` — —
- `strip_remote_dir(path)` — —
- `register_plugin(name)` — Decorator shortcut: @register_plugin('browser_reload').
- `load_user_plugins()` — Load user plugins from project-local and user-global directories.
- `notify(ctx)` — —
- `process_control(ctx)` — Kill processes on specified ports.
- `browser_reload(ctx)` — —
- `systemd_reload(ctx)` — —
- `hardware_diagnostic(ctx)` — Perform hardware diagnostics and provide recommendations.
- `ssh(host, command, timeout, check)` — Execute a command on a remote host via SSH.
- `ssh_available(host, timeout, interval)` — Wait for SSH to become available on a host.
- `rsync(src, dst, exclude, delete)` — Synchronize files using rsync.
- `scp(src, dst, timeout)` — Copy files using SCP.
- `wait(seconds, message)` — Wait for specified seconds.
- `http_expect(url, expect, timeout, retries)` — Verify HTTP endpoint returns expected content.
- `version_check(manifest_path, expect, host, url)` — Verify deployed version matches expectation.
- `main()` — CLI entry point for running Python migrations.
- `migration(name, version, description, author)` — Decorator to mark a function as a migration.
- `register(panel)` — Register a panel in the registry.
- `get(panel_id)` — Get a panel by ID.
- `all_panels()` — Get all registered panels sorted by vendor and ID.
- `infer_from_hardware(hw)` — Heuristic panel detection from HardwareInfo.
- `ensure_line(content, line)` — Ensure `line` is present in [section] of config.txt.
- `ensure_lines(content, lines)` — Apply multiple lines in one pass — important because each `ensure_line` re-parses.
- `fix_dsi_not_enabled(hw, panel)` — Generate steps to configure DSI panel + reboot + verify.
- `fix_enable_i2c(hw, panel)` — Enable I2C interface via raspi-config.
- `fix_enable_spi(hw, panel)` — Enable SPI interface via raspi-config.
- `generate_fix_plan(hw, component, panel)` — From a component name or rule name, return fix steps.
- `build_raspi_config_command(interface, state)` — Build a raspi-config nonint command.
- `ensure_autostart_entry(content, entry)` — Idempotently add or replace an entry in an autostart file.
- `generate_labwc_autostart(kiosk_script, kanshi_settle_secs, extra_entries)` — Generate a complete labwc autostart file for a kiosk deployment.
- `dsi_only_profile(dsi_connector, hdmi_connectors, profile_name, transform)` — Factory: DSI panel enabled, all HDMI outputs disabled.
- `parse_markpact_file(path)` — —
- `parse_markpact_text(text)` — —
- `parse_markpact_file_with_refs(path)` — Parse markpact file and extract all referenced scripts.
- `extract_script_by_ref(text, ref_id, language)` — Extract script from codeblock marked with markpact:ref <ref_id>.
- `extract_script_from_markdown(text, section_id, language)` — Extract script content from a markdown code block by section heading.
- `resolve_script_ref(md_content, ref_id, language)` — Resolve a script reference in markdown, trying markpact:ref then section heading.
- `compile_markpact_document(document)` — —
- `compile_markpact_document_to_data(document)` — —
- `state_key(spec_path, host)` — Stable, filesystem-safe identifier for one (spec, host) checkpoint.
- `default_state_path(spec_path, host, base_dir)` — —
- `filter_resumable(step_ids, state)` — Return ids that are NOT yet completed (preserves order).
- `detect_handler(data)` — Return the first handler that accepts *data*, or None.
- `apply_state(data, p, console)` — Auto-detect file type and apply desired state.
- `run_ssh(step, probe)` — Execute SSH command on remote host.
- `run_scp(step, probe, plan)` — Copy file via SCP.
- `run_rsync(step, probe, plan)` — Sync files via rsync.
- `run_docker_build(step, probe, emitter)` — Run docker compose build on remote with periodic progress polling.
- `run_podman_build(step, probe, emitter)` — Run podman build on remote with periodic progress polling.
- `run_docker_health_wait(step, probe)` — Wait until all containers reach 'healthy' or 'running' status.
- `run_container_log_tail(step, probe)` — Fetch and log the last N lines from each container after start.
- `run_http_check(step, probe, retries, delay)` — HTTP check via SSH curl on the remote host (avoids local network/firewall issues).
- `run_version_check(step, probe)` — Version check via SSH curl on the remote host.
- `run_plugin(step, probe, plan, emitter)` — Dispatch to a registered plugin handler.
- `run_wait(step)` — Wait for specified number of seconds.
- `run_inline_script(step, probe, plan)` — Execute multiline bash script via SSH using base64 encoding.
- `run_ensure_config_line(step, probe)` — Idempotent add/replace a line in a remote config.txt.
- `run_raspi_config(step, probe)` — Run raspi-config nonint to enable/disable an interface.
- `run_ensure_kanshi_profile(step, probe)` — Idempotently write or replace a named kanshi output profile.
- `run_ensure_autostart_entry(step, probe)` — Idempotently add or replace keyed entries in a compositor autostart file.
- `run_ensure_browser_kiosk_script(step, probe)` — Write a kiosk-launch.sh script to the remote device.
- `rollback_steps(completed_steps, probe, state)` — Rollback completed steps in reverse order.
- `run_container_build(step, probe, emitter, engine)` — Run container build on remote with periodic progress polling.
- `bump_version(manifest, bump_type, new_version)` — Bump version across all sources atomically.
- `verify_sources(manifest)` — Verify all sources are in sync with manifest.version.
- `bump_version_with_git(manifest, bump_type, repo_path, new_version)` — Bump version with optional git integration.
- `bump_package(manifest, package_name, bump_type, new_version)` — Bump version of a single package in a monorepo manifest.
- `bump_all_packages(manifest, bump_type)` — Bump all packages in a monorepo manifest independently.
- `get_commits_since_tag(repo_path, tag)` — Get commit messages since tag.
- `read_local_version(workspace_root, app)` — Read VERSION file from local workspace.
- `read_remote_version(remote, remote_dir, app)` — Read VERSION file from remote device via SSH.
- `check_version(local, remote)` — Compare local vs remote version string. Returns (match, detail_line).
- `check_version_http(base_url, expected_version, timeout, endpoint)` — Call *endpoint* on a running service. Returns (ok, summary_line, payload).
- `diff_manifest_vs_spec(manifest, spec_version)` — Compare manifest version vs migration.yaml target.version.
- `diff_manifest_vs_live(manifest, live_version)` — Compare manifest version vs live deployed version.
- `format_diff_report(diffs, manifest_version)` — Format diff results as human-readable report.
- `parse_conventional(message)` — Parse a conventional commit message.
- `analyze_commits(since_tag, repo_path, config)` — Analyze commits since tag to determine bump type.
- `format_analysis_report(analysis)` — Format bump analysis as human-readable report.
- `get_adapter(format_name)` — Get adapter by format name.
- `register_adapter(format_name, adapter)` — Register custom adapter.
- `extract_blueprint()` — Build a DeviceBlueprint by reconciling all available sources.
- `build_hw_requirements(hw)` — Derive hardware requirements from a probed *hw* object.
- `merge_compose_files(compose_files, services, seen)` — Parse each docker-compose file and merge specs into *services* / *seen*.
- `extract_services_from_infra(infra, seen)` — Return :class:`ServiceSpec` objects for every service found in *infra*.
- `infer_app_url(infra)` — Guess the application URL from open ports on *infra*.
- `parse_migration_meta(path)` — Read *path* and return ``{"version": "…", "strategy": "…"}`` if found.
- `generate_twin(blueprint)` — Render a docker-compose YAML string for a local digital-twin.
- `generate_migration(blueprint)` — Render a migration.yaml for deploying blueprint to *target_host*.
- `make_op3_context_from_ssh_client(ssh_client)` — Convert :class:`redeploy.ssh.SshClient` -> :class:`opstree.SSHContext`.
- `snapshot_to_infra_state(snapshot, host)` — Convert opstree.Snapshot -> redeploy.InfraState (backward compat).
- `snapshot_to_hardware_info(snapshot)` — Convert opstree.Snapshot -> redeploy.HardwareInfo.
- `diagnostics_to_hardware_diagnostics(diagnostics)` — Convert op3 :class:`opstree.diagnostics.Diagnostic` -> redeploy :class:`redeploy.models.HardwareDiagnostic`.
- `snapshot_to_device_map(snapshot, host, tags)` — Convert opstree.Snapshot -> redeploy.DeviceMap.
- `load_css(path)` — Parse ``redeploy.css`` and return manifest + templates + workflows.
- `load_css_text(text, source_file)` — Parse CSS text directly (for tests).
- `manifest_to_css(manifest, app)` — Render a ProjectManifest back to ``redeploy.css`` format.
- `templates_to_css(templates)` — Render DetectionTemplate list to CSS block.
- `parse_file(path)` — Parse a single file with auto-detected format.
- `parse_dir(root, recursive, skip_errors)` — Parse all recognised files under *root*.
- `parse_json_file(path)` — Tiny helper for plugin authors; currently unused by built-ins.


## Project Structure

📄 `CHANGELOG`
📄 `DOQL-INTEGRATION`
📄 `Makefile`
📄 `README`
📄 `REFACTORING`
📄 `REPAIR_LOG`
📄 `TODO`
📄 `docs.README`
📄 `docs.dsl-migration`
📄 `docs.fleet`
📄 `docs.markpact-audit`
📄 `docs.markpact-implementation-plan`
📄 `docs.observe`
📄 `docs.op3-migration`
📄 `docs.parsers.README`
📄 `docs.patterns`
📄 `examples.README`
📄 `examples.hardware.enable-i2c-spi`
📄 `examples.hardware.official-dsi-7-inch`
📄 `examples.hardware.rpi5-waveshare-kiosk`
📄 `examples.hardware.waveshare-8-inch-dsi`
📄 `examples.md.01-rpi5-deploy.migration`
📄 `examples.md.01-vps-version-bump.README`
📄 `examples.md.01-vps-version-bump.migration`
📄 `examples.md.02-k3s-to-docker.README`
📄 `examples.md.02-k3s-to-docker.migration`
📄 `examples.md.02-multi-language.migration`
📄 `examples.md.03-all-actions.migration`
📄 `examples.md.03-docker-to-podman-quadlet.README`
📄 `examples.md.03-docker-to-podman-quadlet.migration`
📄 `examples.md.04-v3-state-reconciliation.migration`
📄 `examples.md.README`
📄 `examples.redeploy_iac_parsers.argocd_flux` (4 functions, 2 classes)
📄 `examples.redeploy_iac_parsers.gitops_ci` (5 functions, 2 classes)
📄 `examples.redeploy_iac_parsers.helm_ansible` (4 functions, 2 classes)
📄 `examples.redeploy_iac_parsers.helm_kustomize` (5 functions, 2 classes)
📄 `examples.yaml.01-vps-version-bump.README`
📄 `examples.yaml.01-vps-version-bump.migration`
📄 `examples.yaml.02-k3s-to-docker.README`
📄 `examples.yaml.02-k3s-to-docker.migration`
📄 `examples.yaml.03-docker-to-podman-quadlet.README`
📄 `examples.yaml.03-docker-to-podman-quadlet.migration`
📄 `examples.yaml.04-rpi-kiosk.README`
📄 `examples.yaml.04-rpi-kiosk.migration`
📄 `examples.yaml.04-rpi-kiosk.migration-rpi5`
📄 `examples.yaml.04-rpi-kiosk.redeploy`
📄 `examples.yaml.05-iot-fleet-ota.README`
📄 `examples.yaml.05-iot-fleet-ota.migration`
📄 `examples.yaml.05-iot-fleet-ota.redeploy`
📄 `examples.yaml.06-local-dev.README`
📄 `examples.yaml.06-local-dev.migration`
📄 `examples.yaml.06-local-dev.redeploy`
📄 `examples.yaml.07-staging-to-prod.README`
📄 `examples.yaml.07-staging-to-prod.migration`
📄 `examples.yaml.07-staging-to-prod.redeploy`
📄 `examples.yaml.08-rollback.README`
📄 `examples.yaml.08-rollback.migration`
📄 `examples.yaml.09-fleet-yaml.README`
📄 `examples.yaml.09-fleet-yaml.fleet`
📄 `examples.yaml.09-fleet-yaml.redeploy`
📄 `examples.yaml.10-multienv.README`
📄 `examples.yaml.10-multienv.dev`
📄 `examples.yaml.10-multienv.prod`
📄 `examples.yaml.10-multienv.redeploy`
📄 `examples.yaml.10-multienv.staging`
📄 `examples.yaml.11-traefik-tls.README`
📄 `examples.yaml.11-traefik-tls.migration`
📄 `examples.yaml.11-traefik-tls.traefik.dynamic.tls`
📄 `examples.yaml.12-ci-pipeline.README`
📄 `examples.yaml.12-ci-pipeline.deploy.github`
📄 `examples.yaml.12-ci-pipeline.deploy.gitlab`
📄 `examples.yaml.12-ci-pipeline.migration`
📄 `examples.yaml.12-ci-pipeline.redeploy`
📄 `examples.yaml.13-kiosk-appliance`
📄 `examples.yaml.13-multi-app-monorepo.README`
📄 `examples.yaml.13-multi-app-monorepo.fleet`
📄 `examples.yaml.13-multi-app-monorepo.migration`
📄 `examples.yaml.13-multi-app-monorepo.redeploy`
📄 `examples.yaml.14-blue-green`
📄 `examples.yaml.15-canary`
📄 `examples.yaml.16-auto-rollback`
📄 `goal`
📄 `project`
📄 `pyproject`
📄 `pyqual`
📦 `redeploy`
📦 `redeploy.analyze`
📦 `redeploy.analyze.checkers`
📄 `redeploy.analyze.checkers.base` (1 functions, 1 classes)
📄 `redeploy.analyze.checkers.binary` (2 functions, 1 classes)
📄 `redeploy.analyze.checkers.command_ref` (2 functions, 1 classes)
📄 `redeploy.analyze.checkers.compose` (6 functions, 1 classes)
📄 `redeploy.analyze.checkers.docker_build` (7 functions, 1 classes)
📄 `redeploy.analyze.checkers.env` (1 functions, 1 classes)
📄 `redeploy.analyze.checkers.path` (5 functions, 2 classes)
📄 `redeploy.analyze.checkers.reference` (1 functions, 1 classes)
📄 `redeploy.analyze.ignore` (4 functions, 1 classes)
📄 `redeploy.analyze.models` (3 functions, 3 classes)
📄 `redeploy.analyze.preflight_schema` (6 functions, 1 classes)
📄 `redeploy.analyze.spec_analyzer` (3 functions, 1 classes)
📦 `redeploy.apply`
📄 `redeploy.apply.exceptions` (1 functions, 1 classes)
📄 `redeploy.apply.executor` (17 functions, 1 classes)
📄 `redeploy.apply.handlers` (22 functions)
📄 `redeploy.apply.progress` (11 functions, 1 classes)
📄 `redeploy.apply.rollback` (1 functions)
📄 `redeploy.apply.state` (13 functions, 1 classes)
📄 `redeploy.apply.state_apply` (9 functions, 4 classes)
📦 `redeploy.apply.utils`
📄 `redeploy.apply.utils.run_container_build` (1 functions)
📦 `redeploy.audit` (1 functions)
📄 `redeploy.audit.auditor` (13 functions, 1 classes)
📄 `redeploy.audit.extractor` (5 functions, 1 classes)
📄 `redeploy.audit.models` (3 functions, 3 classes)
📄 `redeploy.audit.paths` (3 functions)
📄 `redeploy.audit.patterns`
📄 `redeploy.audit.probe` (8 functions, 1 classes)
📦 `redeploy.blueprint`
📄 `redeploy.blueprint.extractor` (1 functions)
📦 `redeploy.blueprint.generators`
📄 `redeploy.blueprint.generators.docker_compose` (2 functions)
📄 `redeploy.blueprint.generators.migration` (1 functions)
📦 `redeploy.blueprint.sources`
📄 `redeploy.blueprint.sources.compose` (6 functions)
📄 `redeploy.blueprint.sources.hardware` (1 functions)
📄 `redeploy.blueprint.sources.infra` (2 functions)
📄 `redeploy.blueprint.sources.migration` (1 functions)
📦 `redeploy.cli` (3 functions)
📦 `redeploy.cli.commands`
📄 `redeploy.cli.commands.apply_cmd` (1 functions)
📄 `redeploy.cli.commands.audit` (1 functions)
📄 `redeploy.cli.commands.blueprint` (8 functions)
📄 `redeploy.cli.commands.bump_fix` (12 functions)
📄 `redeploy.cli.commands.detect` (1 functions)
📄 `redeploy.cli.commands.device_map` (1 functions)
📄 `redeploy.cli.commands.device_map_actions` (5 functions)
📄 `redeploy.cli.commands.device_map_renderers` (7 functions)
📄 `redeploy.cli.commands.devices` (4 functions)
📄 `redeploy.cli.commands.devices_display` (2 functions)
📄 `redeploy.cli.commands.diagnose` (1 functions)
📄 `redeploy.cli.commands.diff` (1 functions)
📄 `redeploy.cli.commands.exec_` (6 functions)
📄 `redeploy.cli.commands.export` (6 functions)
📄 `redeploy.cli.commands.gh_workflow` (15 functions)
📄 `redeploy.cli.commands.hardware` (11 functions)
📄 `redeploy.cli.commands.import_` (8 functions)
📄 `redeploy.cli.commands.init` (1 functions)
📄 `redeploy.cli.commands.inspect` (2 functions)
📄 `redeploy.cli.commands.lint` (1 functions)
📄 `redeploy.cli.commands.mcp_cmd` (1 functions)
📄 `redeploy.cli.commands.migrate_cmd` (1 functions)
📄 `redeploy.cli.commands.patterns` (1 functions)
📄 `redeploy.cli.commands.plan_apply`
📄 `redeploy.cli.commands.plan_apply_report` (10 functions)
📄 `redeploy.cli.commands.plan_apply_run` (3 functions)
📄 `redeploy.cli.commands.plan_apply_shared` (10 functions)
📄 `redeploy.cli.commands.plan_cmd` (1 functions)
📄 `redeploy.cli.commands.plugin` (1 functions)
📄 `redeploy.cli.commands.probe` (1 functions)
📄 `redeploy.cli.commands.probe_display` (3 functions)
📄 `redeploy.cli.commands.prompt_cmd` (4 functions)
📄 `redeploy.cli.commands.push` (1 functions)
📄 `redeploy.cli.commands.run_cmd` (1 functions)
📄 `redeploy.cli.commands.state` (4 functions)
📄 `redeploy.cli.commands.status` (1 functions)
📄 `redeploy.cli.commands.target` (1 functions)
📦 `redeploy.cli.commands.version`
📄 `redeploy.cli.commands.version.commands` (8 functions)
📄 `redeploy.cli.commands.version.helpers` (10 functions)
📄 `redeploy.cli.commands.version.monorepo` (5 functions)
📄 `redeploy.cli.commands.version.release` (6 functions)
📄 `redeploy.cli.commands.version.scanner` (18 functions)
📦 `redeploy.cli.commands.version.utils`
📄 `redeploy.cli.commands.version.utils.changelog_config` (1 functions)
📄 `redeploy.cli.commands.version.utils.git_config` (1 functions)
📄 `redeploy.cli.commands.workflow` (3 functions)
📄 `redeploy.cli.core` (7 functions)
📄 `redeploy.cli.display` (25 functions)
📄 `redeploy.cli.query` (1 functions)
📦 `redeploy.config_apply`
📄 `redeploy.config_apply.applier` (3 functions)
📦 `redeploy.config_apply.handlers`
📄 `redeploy.config_apply.handlers.display` (2 functions)
📄 `redeploy.config_apply.loader` (1 functions)
📄 `redeploy.data_sync` (2 functions)
📦 `redeploy.detect`
📦 `redeploy.detect.builtin`
📄 `redeploy.detect.builtin.templates`
📄 `redeploy.detect.detector` (4 functions, 1 classes)
📄 `redeploy.detect.hardware` (2 functions)
📄 `redeploy.detect.hardware_rules` (3 functions)
📄 `redeploy.detect.probes` (9 functions)
📄 `redeploy.detect.remote`
📄 `redeploy.detect.templates` (13 functions, 6 classes)
📄 `redeploy.detect.workflow` (12 functions, 3 classes)
📦 `redeploy.discovery`
📄 `redeploy.discovery.auto_probe` (9 functions)
📄 `redeploy.discovery.helpers` (3 functions)
📄 `redeploy.discovery.registry` (3 functions)
📄 `redeploy.discovery.scanners` (8 functions)
📄 `redeploy.discovery.ssh_credentials` (3 functions)
📄 `redeploy.discovery.types` (2 classes)
📄 `redeploy.discovery_probe` (2 functions)
📦 `redeploy.dsl`
📄 `redeploy.dsl.loader` (12 functions, 3 classes)
📄 `redeploy.dsl.parser` (8 functions, 2 classes)
📦 `redeploy.dsl_python`
📄 `redeploy.dsl_python.context` (3 functions, 1 classes)
📄 `redeploy.dsl_python.decorators` (8 functions, 4 classes)
📄 `redeploy.dsl_python.docker_steps` (6 functions, 2 classes)
📄 `redeploy.dsl_python.exceptions` (4 functions, 6 classes)
📄 `redeploy.dsl_python.runner` (5 functions, 1 classes)
📄 `redeploy.dsl_python.steps` (7 functions)
📄 `redeploy.fleet` (23 functions, 6 classes)
📦 `redeploy.hardware`
📄 `redeploy.hardware.config_txt` (2 functions, 1 classes)
📦 `redeploy.hardware.data`
📄 `redeploy.hardware.data.hyperpixel`
📄 `redeploy.hardware.data.official`
📄 `redeploy.hardware.data.waveshare`
📄 `redeploy.hardware.fixes` (6 functions)
📦 `redeploy.hardware.kiosk`
📄 `redeploy.hardware.kiosk.autostart` (3 functions, 1 classes)
📄 `redeploy.hardware.kiosk.browsers` (1 functions, 1 classes)
📄 `redeploy.hardware.kiosk.compositors` (1 functions, 1 classes)
📄 `redeploy.hardware.kiosk.output_profiles` (2 functions, 1 classes)
📄 `redeploy.hardware.panels` (5 functions, 1 classes)
📄 `redeploy.hardware.raspi_config` (1 functions)
📦 `redeploy.heal`
📄 `redeploy.heal.decider` (2 functions, 2 classes)
📄 `redeploy.heal.hint_provider` (8 functions)
📄 `redeploy.heal.log_writer` (1 functions)
📄 `redeploy.heal.loop_detector` (4 functions, 2 classes)
📄 `redeploy.heal.runner` (5 functions, 1 classes)
📦 `redeploy.iac`
📄 `redeploy.iac.base` (13 functions, 7 classes)
📄 `redeploy.iac.config_hints` (15 functions, 1 classes)
📄 `redeploy.iac.docker_compose` (23 functions, 1 classes)
📦 `redeploy.iac.parsers`
📄 `redeploy.iac.parsers.compose` (18 functions, 1 classes)
📄 `redeploy.iac.registry` (4 functions)
📦 `redeploy.integrations`
📄 `redeploy.integrations.op3_bridge` (5 functions)
📦 `redeploy.markpact`
📄 `redeploy.markpact.compiler` (6 functions, 1 classes)
📄 `redeploy.markpact.models` (2 classes)
📄 `redeploy.markpact.parser` (10 functions, 1 classes)
📄 `redeploy.mcp_server` (15 functions)
📦 `redeploy.models`
📄 `redeploy.models.blueprint` (3 functions, 6 classes)
📄 `redeploy.models.devices` (13 functions, 4 classes)
📄 `redeploy.models.enums` (4 classes)
📄 `redeploy.models.hardware` (5 classes)
📄 `redeploy.models.infra` (6 classes)
📄 `redeploy.models.manifest` (6 functions, 2 classes)
📄 `redeploy.models.persisted` (2 functions, 1 classes)
📄 `redeploy.models.pipeline` (1 classes)
📄 `redeploy.models.plan` (2 classes)
📄 `redeploy.models.spec` (6 functions, 3 classes)
📄 `redeploy.observe` (14 functions, 3 classes)
📄 `redeploy.parse` (10 functions)
📄 `redeploy.patterns` (11 functions, 4 classes)
📦 `redeploy.plan`
📄 `redeploy.plan.planner` (21 functions, 1 classes)
📦 `redeploy.plugins` (10 functions, 2 classes)
📦 `redeploy.plugins.builtin`
📄 `redeploy.plugins.builtin.browser_reload` (3 functions)
📄 `redeploy.plugins.builtin.hardware_diagnostic` (11 functions, 1 classes)
📄 `redeploy.plugins.builtin.notify` (7 functions)
📄 `redeploy.plugins.builtin.process_control` (3 functions)
📄 `redeploy.plugins.builtin.systemd_reload` (2 functions)
📄 `redeploy.schema` (6 functions)
📄 `redeploy.spec_loader` (1 functions, 2 classes)
📄 `redeploy.ssh` (17 functions, 4 classes)
📦 `redeploy.steps` (4 functions, 1 classes)
📄 `redeploy.steps.docker` (1 functions)
📄 `redeploy.steps.generic` (1 functions)
📄 `redeploy.steps.hardware` (1 functions)
📄 `redeploy.steps.k3s` (1 functions)
📄 `redeploy.steps.kiosk`
📄 `redeploy.steps.podman` (1 functions)
📄 `redeploy.steps.process` (1 functions)
📄 `redeploy.steps.scm` (1 functions)
📄 `redeploy.steps.transfer` (1 functions)
📄 `redeploy.templates.process_control_template`
📄 `redeploy.verify` (7 functions, 1 classes)
📦 `redeploy.version` (4 functions)
📄 `redeploy.version.bump` (6 functions)
📄 `redeploy.version.changelog` (15 functions, 1 classes)
📄 `redeploy.version.commits` (3 functions, 2 classes)
📄 `redeploy.version.diff` (3 functions, 1 classes)
📄 `redeploy.version.git_integration` (13 functions, 2 classes)
📄 `redeploy.version.git_transaction` (5 functions, 2 classes)
📄 `redeploy.version.manifest` (10 functions, 8 classes)
📦 `redeploy.version.sources` (5 functions, 1 classes)
📄 `redeploy.version.sources.base` (5 functions, 1 classes)
📄 `redeploy.version.sources.json_` (3 functions, 1 classes)
📄 `redeploy.version.sources.plain` (2 functions, 1 classes)
📄 `redeploy.version.sources.regex` (2 functions, 1 classes)
📄 `redeploy.version.sources.toml_` (3 functions, 1 classes)
📄 `redeploy.version.sources.yaml_` (3 functions, 1 classes)
📄 `redeploy.version.transaction` (6 functions, 2 classes)
📄 `reports.hardware-108`
📄 `reports.hardware-109`
📄 `scripts.quality_gate`
📄 `sumd`
📄 `testql-scenarios.generated-cli-tests.testql.toon`
📄 `testql-scenarios.generated-from-pytests.testql.toon`
📄 `tree`

## Requirements

- Python >= >=3.11
- pydantic >=2.0- pyyaml >=6.0- markdown-it-py >=3.0- click >=8.0- loguru >=0.7- paramiko >=3.0- httpx >=0.25- rich >=13.0- jmespath >=1.0- goal >=2.1.0- costs >=0.1.20- pfix >=0.1.60

## Contributing

**Contributors:**
- Tom Softreck <tom@sapletta.com>

We welcome contributions! Open an issue or pull request to get started.
### Development Setup

```bash
# Clone the repository
git clone https://github.com/maskservice/redeploy
cd redeploy

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest
```

## Documentation

- 💡 [Examples](./examples) — Usage examples and code samples

### Generated Files

| Output | Description | Link |
|--------|-------------|------|
| `README.md` | Project overview (this file) | — |
| `examples` | Usage examples and code samples | [View](./examples) |

<!-- code2docs:end -->