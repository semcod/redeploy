# Subactor deployment docs moved

**SSOT is `subactor/deployment` (HOME=`subactor`), not this repository.**

- https://github.com/subactor/deployment
- Topology / procedures / fleet wrappers: that repo’s `docs/` and `redeploy/`

This toolkit (`semcod/redeploy`) remains generic: `detect` → `plan` → `apply` /
`fleet`. Subactor operators **ADOPT** it from `subactor/deployment`; they do not
treat `examples/subactor/` here as source of truth.

```bash
git clone git@github.com:subactor/deployment.git
cd deployment
redeploy fleet --file redeploy/fleet.yaml
redeploy run redeploy/03-docker-vps-platform/migration.yaml --plan-only
```
