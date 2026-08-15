# Subactor deployment through `semcod/redeploy`

HOME: `semcod` (`redeploy`, toolkit).  
Runtime facts and authority: **ADOPT** from Subactor
(`platform/config/deployment-bindings`, `www-sub-actor/docs/deployment.md`,
knowledge entries). Host fitness: **ADOPT** `wellmanifest/policy-dsl`
(`subactor.host/production-server/v1`, `subactor.host/rpi5/v1`).

This document answers: **how Subactor is deployed today**, and **how operators
drive that topology with `redeploy`** (detect → plan → apply / fleet).

> Status observed: **2026-08-15**. Live public `*.subactor.com` and current
> `sub.actor` publish path are **Plesk**. Full Docker VPS + Traefik for
> Platform/`control.sub.actor` is the **documented target** in
> `www-sub-actor/docs/deployment.md`, not yet the live Founder Control host.

---

## 1. Topology (as-is vs target)

```text
                         ┌─────────────────────────────────────┐
                         │  Plesk 217.160.250.222 (edge)       │
 Internet ──────────────►│  DNS / TLS / mail / static / PHP    │
                         │  Node Toolkit (founder origin)      │
                         └──────────────┬──────────────────────┘
                                        │
          ┌─────────────────────────────┼─────────────────────────────┐
          │                             │                             │
   *.subactor.com                 founder.subactor.com           sub.actor
   static / PHP sites             Node proxy → :19081            Plesk httpdocs
   (SFTP plesk:// sync)           SSH -R from Lenovo             (binding:
                                  → Caddy :18081 → Control       deployment:sub-actor:production)

TARGET (policy-aligned Docker VPS — FORBID Compose inside Plesk):

 Internet ──► Docker VPS (Traefik ACME DNS-01)
                 ├─ https://sub.actor / *.sub.actor   (portal image sha-*)
                 └─ https://control.sub.actor          (Platform Control router)
              Plesk remains DNS/TLS/mail/WWW edge only
```

### Domain map (SSOT)

Source of truth: `subactor/platform/config/deployment-bindings/registry.v1.json`
and `public-pages.json`. Provider for listed sites today: **`plesk`**.

| Domain | Role today | Deploy mechanism |
| --- | --- | --- |
| `subactor.com` | Marketing / main site | Plesk SFTP sync |
| `www.subactor.com`, `docs.subactor.com`, `docs-stage.subactor.com` | Docs / www | Plesk SFTP |
| `logo.subactor.com`, `status.subactor.com`, `contracts.subactor.com`, … | Brand / status | Plesk SFTP |
| `identity.subactor.com`, `chat.subactor.com` | Surface placeholders | Plesk SFTP |
| `auth.subactor.com` | Auth **bootstrap** static site (not full IdP yet) | Plesk SFTP; project `projekty/auth-subactor-com` |
| `founder.subactor.com` | Public Founder Control origin | Plesk Node `plesk-origin` + SSH reverse tunnel |
| `sub.actor` | SaaS portal publish | Plesk webspace `sub.actor/httpdocs` (live); Docker Traefik path documented |
| `control.sub.actor` | Authenticated Control | Documented on Docker VPS; live Founder still via `founder.subactor.com` |
| `*.sub.actor` tenants | Tenant vhosts | Documented Traefik wildcard; live depends on portal stack |

`control.subactor.com` is **not** in the bindings registry.

---

## 2. Current procedures (canonical scripts)

### A. Static / PHP public pages (`*.subactor.com`, often `sub.actor`)

1. Exact deployment binding + plan hash (Digital Twin / Control).
2. `plesk://host/site/command/sync` (SFTP) — credentials from Vault scopes, not
   in Git.
3. HTTP/hash read-back on the bound URL.
4. Entry points: Planfile tickets, `platform/scripts/deploy-public-pages.mjs`,
   project reconciliation.

**redeploy role:** inventory in `examples/subactor/fleet.yaml`; verify steps in
`01-plesk-edge-verify` (curl EQL). Publish mutate stays Subactor `plesk://`
(authority + binding), not a free-form rsync from redeploy.

### B. Founder public Control (`founder.subactor.com`)

1. Publish `projekty/founder-subactor-com/plesk-origin/{app.js,package.json}` to
   Plesk docroot `founder.subactor.com/`.
2. Keep `founder-plesk-tunnel.service` on Lenovo
   (`platform/scripts/founder-plesk-tunnel.sh`) → `prototypowanie.pl:19081`.
3. Doctor: `platform/scripts/founder-public-origin-doctor.sh`.
4. EQL: `/` → 401 Basic; `/founder/form` → 200; `/__origin_health` → 200.

**redeploy role:** `02-founder-origin-verify` migration (health probes only).

### C. Platform Compose (lab / future VPS)

```bash
cd /opt/subactor/src/platform   # or sibling checkout
./scripts/deploy-stack.sh deploy
```

Posture from host `.env` (`SUBACTOR_DEPLOYMENT_TOPOLOGY`,
`CONTROL_DEPLOYMENT_POSTURE`). Never `compose down -v` in deploy procedures.

### D. Documented full portal + Platform (Docker VPS target)

From `www-sub-actor/docs/deployment.md`:

1. Host fit per Policy DSL (16 GiB min / 32 GiB recommended).
2. `capture-platform-lock.sh` → `sync-platform.sh` (exact SHAs).
3. Secrets on host only; GHCR image `ghcr.io/subactor/www-sub-actor:sha-*`.
4. `deploy-all.sh docker <PORTAL_IMAGE>` → Platform then portal.
5. Health: `https://sub.actor/readyz`, tenant resolve smoke.
6. GitHub Environments `staging` / `production` + `release.sh` over SSH.

**redeploy role:** `03-docker-vps-platform` migration wraps the same SSH command
surface for detect/plan/apply and fleet targeting.

### E. auth.subactor.com

Static bootstrap only. Full SSO/OIDC federation is **not** the current runtime.
Do not treat `auth.subactor.com` as the production IdP until a binding + provider
say so.

---

## 3. Using `redeploy` for Subactor

Install: `pipx install redeploy` (see root README).

```bash
cd examples/subactor

# Fleet inventory (roles / tags — no secrets)
redeploy fleet --file fleet.yaml

# Plan only (no SSH)
redeploy run 03-docker-vps-platform/migration.yaml --plan-only

# Dry-run against a configured host (set SUBACTOR_VPS_SSH in env / edit host)
redeploy run 03-docker-vps-platform/migration.yaml --dry-run

# Verify-only edge probes (read-only)
redeploy run 01-plesk-edge-verify/migration.yaml --plan-only
redeploy run 02-founder-origin-verify/migration.yaml --plan-only
```

### Safety rules (fail closed)

| Rule | Why |
| --- | --- |
| No Compose stack inside Plesk | Policy `FORBID RUN_COMPOSE_STACK_INSIDE_PLESK` |
| No Control port 8181 on public host | Policy `FORBID BIND_CONTROL_PORT_8181_PUBLIC` |
| No mutable `main` multi-repo deploy | Use `components.lock` / `sha-*` images |
| No secrets in `migration.yaml` / Git | Host files + Vault; placeholders only here |
| `redeploy apply` ≠ production authority | Subactor grant / binding still required for mutate |
| Validator merge ≠ production apply | Separate POA / Planfile / SSH release |

---

## 4. Example package layout

```text
examples/subactor/
├── README.md
├── fleet.yaml                      # roles: plesk-edge, founder-origin, docker-vps, rpi5-edge
├── 01-plesk-edge-verify/
│   ├── migration.yaml              # curl EQL for public pages
│   └── redeploy.yaml
├── 02-founder-origin-verify/
│   ├── migration.yaml              # founder EQL + tunnel hint
│   └── redeploy.yaml
└── 03-docker-vps-platform/
    ├── migration.yaml              # deploy-all.sh / release surface
    └── redeploy.yaml
```

Hosts in examples use placeholders:

- `deploy@SUBACTOR_VPS_IP` — Docker production VPS
- `operator@LENOVO_LAB` — tunnel / Control lab host
- Plesk verify steps run from the operator machine (no Plesk root required)

Replace placeholders before `--dry-run` / apply. Prefer environment-specific
copies outside Git for real IPs.

---

## 5. Cross-links (do not duplicate SSOT)

| Concern | Canonical location |
| --- | --- |
| Host MUST/SHOULD tables | `wellmanifest/policy-dsl` + `www-sub-actor/docs/deployment.md` §1 |
| Portal/PayPal/ACME/GitHub release | `www-sub-actor/docs/deployment.md` |
| Domain → docroot bindings | `subactor/platform/config/deployment-bindings/registry.v1.json` |
| Founder origin ops | `subactor/projekty/founder-subactor-com/README.md` |
| Auth bootstrap | `subactor/projekty/auth-subactor-com/README.md` |
| redeploy CLI mechanics | `semcod/redeploy/README.md`, `docs/fleet.md` |

When this document disagrees with Subactor registries or live knowledge, **Subactor
SSOT wins**; update this file in the same change set.

---

## 6. Suggested operator sequence (target VPS cutover)

1. `redeploy run 01-plesk-edge-verify/... --plan-only` — baseline public EQL.
2. Qualify VPS with Policy DSL production-server profile.
3. Bootstrap Docker host (`www-sub-actor/scripts/host-bootstrap.sh`).
4. Pin sources (`capture-platform-lock` / `sync-platform`).
5. `redeploy run 03-docker-vps-platform/... --dry-run` then apply under grant.
6. Point `sub.actor` / `*.sub.actor` A/AAAA at VPS; keep Plesk for `*.subactor.com`
   edge until intentionally migrated.
7. Move Founder public URL to `https://control.sub.actor/founder` only after
   Control is healthy on Traefik; keep tunnel as rollback until EQL green.
8. Re-run verify migrations; backup Postgres / `acme-data` / secrets.
