# Subactor examples for `redeploy`

Operational package for Subactor edge + Docker VPS topology.

Narrative: [`../../docs/subactor-deployment.md`](../../docs/subactor-deployment.md).

## Commands

```bash
# From repo root
redeploy fleet --file examples/subactor/fleet.yaml

redeploy run examples/subactor/01-plesk-edge-verify/migration.yaml --plan-only
redeploy run examples/subactor/02-founder-origin-verify/migration.yaml --plan-only
redeploy run examples/subactor/03-docker-vps-platform/migration.yaml --plan-only

# After editing host placeholders:
redeploy run examples/subactor/03-docker-vps-platform/migration.yaml --dry-run
```

## What these examples do / do not do

| Example | Does | Does not |
| --- | --- | --- |
| `01-plesk-edge-verify` | Document curl EQL for public pages | Mutate Plesk docroots |
| `02-founder-origin-verify` | Document Founder origin probes | Start/stop the SSH tunnel |
| `03-docker-vps-platform` | Wrap documented `deploy-all.sh` surface | Invent secrets or unpinned `main` |

Publish to Plesk remains Subactor `plesk://` + deployment bindings.
