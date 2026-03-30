# Operator Surface Report

Generated from `config/automation-backbone/operator-surface-registry.json` plus the cached operator-surface live probe in `reports/truth-inventory/latest.json` by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

## Front Door Contract

- Registry version: `2026-03-29.1`
- Cached truth snapshot: `2026-03-30T00:04:37.657861+00:00`
- Canonical portal id: `athanor_command_center`
- Canonical operator URL: `https://athanor.local/`
- Canonical node: `dev`
- Runtime service id: `dashboard`
- Current runtime mode: `containerized_service_behind_caddy`
- Target runtime mode: `containerized_service_behind_caddy`
- Multiple active portals allowed: `False`
- Promotion gate: Canonical DEV command center is reachable from operator desktops at athanor.local, the WORKSHOP shadow portal stays retired, and browser smoke is green.

## Summary

- Human-facing surfaces tracked: `37`
- Launchpad-approved surfaces: `21`
- Active production portal count: `1`
- Shadow portal count: `0`
- Duplicate active production portals observed: none

### Surface kinds

| Kind | Count |
| --- | --- |
| `domain_app` | 2 |
| `internal_api` | 14 |
| `portal` | 1 |
| `retired` | 1 |
| `specialist_tool` | 19 |

### Statuses

| Status | Count |
| --- | --- |
| `active_internal` | 14 |
| `active_specialist` | 21 |
| `degraded_production` | 1 |
| `retired` | 1 |

## Canonical Portal

- Label: `Athanor Command Center`
- Status: `degraded_production`
- Canonical URL: `https://athanor.local/`
- Runtime URL: `http://dev.athanor.local:3001/`
- Deployment mode: `containerized_service_behind_caddy`
- Target deployment mode: `containerized_service_behind_caddy`
- Canonical probe: `URLError: [Errno 11001] getaddrinfo failed`
- Runtime probe: `URLError: [Errno 11001] getaddrinfo failed`
- Runtime Next.js asset probe: `unknown` root, `0` failing sampled asset(s)
- Sampled failing assets: none
- DEV runtime probe target: `dev`
- DEV deployment mode observed: `containerized_service_behind_caddy`
- Dashboard container running: `True`
- Dashboard container status: `Up 54 minutes`
- Dashboard container image: `athanor/dashboard:latest`
- Dashboard container ports: `0.0.0.0:3001->3001/tcp, [::]:3001->3001/tcp`
- Dashboard compose working dir: `/opt/athanor/dashboard`
- Dashboard compose config file(s): `/opt/athanor/dashboard/docker-compose.yml`
- Expected dashboard deploy root: `/opt/athanor/dashboard`
- Observed active dashboard root: `/opt/athanor/dashboard`
- Observed compose config file(s): `/opt/athanor/dashboard/docker-compose.yml`
- Dashboard deploy-root drift: `False`
- DEV local runtime probe from host: `200`
- DEV local canonical probe from host: `200`
- Caddy service state: `active` / `running`
- Legacy dashboard systemd state: `inactive` / `dead`
- Legacy dashboard working directory: `/home/shaun/repos/athanor/projects/dashboard`

## Shadow Portal

No shadow portals are currently registered.

## Launchpad Surfaces

| Surface | Node | Kind | Canonical URL | Operator role | Canonical probe |
| --- | --- | --- | --- | --- | --- |
| `Grafana` | `vault` | `specialist_tool` | `http://vault.athanor.local:3000/` | `observability` | `URLError: [Errno 11001] getaddrinfo failed` |
| `Prometheus` | `vault` | `specialist_tool` | `http://vault.athanor.local:9090/` | `observability` | `URLError: [Errno 11001] getaddrinfo failed` |
| `Uptime Kuma` | `vault` | `specialist_tool` | `http://vault.athanor.local:3009/` | `observability` | `URLError: [Errno 11001] getaddrinfo failed` |
| `Langfuse` | `vault` | `specialist_tool` | `http://vault.athanor.local:3030/` | `observability` | `URLError: [Errno 11001] getaddrinfo failed` |
| `Open WebUI (VAULT)` | `vault` | `specialist_tool` | `http://vault.athanor.local:3090/` | `chat` | `URLError: [Errno 11001] getaddrinfo failed` |
| `Neo4j Browser` | `vault` | `specialist_tool` | `http://vault.athanor.local:7474/` | `knowledge` | `URLError: [Errno 11001] getaddrinfo failed` |
| `Miniflux` | `vault` | `specialist_tool` | `http://vault.athanor.local:8070/` | `knowledge` | `URLError: [Errno 11001] getaddrinfo failed` |
| `Home Assistant` | `vault` | `specialist_tool` | `http://vault.athanor.local:8123/` | `home` | `URLError: [Errno 11001] getaddrinfo failed` |
| `Tautulli` | `vault` | `specialist_tool` | `http://vault.athanor.local:8181/` | `media` | `URLError: [Errno 11001] getaddrinfo failed` |
| `ntfy` | `vault` | `specialist_tool` | `http://vault.athanor.local:8880/` | `observability` | `URLError: [Errno 11001] getaddrinfo failed` |
| `Sonarr` | `vault` | `specialist_tool` | `http://vault.athanor.local:8989/` | `media` | `URLError: [Errno 11001] getaddrinfo failed` |
| `Radarr` | `vault` | `specialist_tool` | `http://vault.athanor.local:7878/` | `media` | `URLError: [Errno 11001] getaddrinfo failed` |
| `Prowlarr` | `vault` | `specialist_tool` | `http://vault.athanor.local:9696/` | `media` | `URLError: [Errno 11001] getaddrinfo failed` |
| `SABnzbd` | `vault` | `specialist_tool` | `http://vault.athanor.local:8080/` | `media` | `URLError: [Errno 11001] getaddrinfo failed` |
| `Stash` | `vault` | `specialist_tool` | `http://vault.athanor.local:9999/` | `media` | `URLError: [Errno 11001] getaddrinfo failed` |
| `Plex` | `vault` | `specialist_tool` | `http://vault.athanor.local:32400/web` | `media` | `URLError: [Errno 11001] getaddrinfo failed` |
| `Open WebUI (WORKSHOP)` | `workshop` | `specialist_tool` | `http://interface.athanor.local:3000/` | `chat` | `URLError: [Errno 11001] getaddrinfo failed` |
| `ComfyUI` | `workshop` | `specialist_tool` | `http://interface.athanor.local:8188/` | `creative` | `URLError: [Errno 11001] getaddrinfo failed` |
| `Empire of Broken Queens` | `workshop` | `domain_app` | `http://interface.athanor.local:3002/` | `domain_product` | `URLError: [Errno 11001] getaddrinfo failed` |
| `Ulrich Energy` | `workshop` | `domain_app` | `http://interface.athanor.local:3003/` | `domain_product` | `URLError: [Errno 11001] getaddrinfo failed` |
| `Speaches` | `foundry` | `specialist_tool` | `http://core.athanor.local:8200/` | `creative` | `URLError: [Errno 11001] getaddrinfo failed` |

## Full Surface Matrix

| Surface | Kind | Node | Status | Navigation | Canonical URL | Runtime URL | Runtime probe |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `athanor_command_center` | `portal` | `dev` | `degraded_production` | `front_door` | `https://athanor.local/` | `http://dev.athanor.local:3001/` | `URLError: [Errno 11001] getaddrinfo failed` |
| `workshop_shadow_command_center` | `retired` | `workshop` | `retired` | `hidden` | `https://athanor.local/` | `http://192.168.1.225:3001/` | `URLError: [WinError 10061] No connection could b` |
| `quality_gate` | `internal_api` | `dev` | `active_internal` | `hidden` | `http://dev.athanor.local:8790/health` | `http://192.168.1.189:8790/health` | `200` |
| `semantic_router` | `internal_api` | `dev` | `active_internal` | `hidden` | `http://dev.athanor.local:8060/health` | `http://192.168.1.189:8060/health` | `200` |
| `subscription_burn` | `internal_api` | `dev` | `active_internal` | `hidden` | `http://dev.athanor.local:8065/health` | `http://192.168.1.189:8065/health` | `200` |
| `embedding_api` | `internal_api` | `dev` | `active_internal` | `hidden` | `http://dev.athanor.local:8001/health` | `http://192.168.1.189:8001/health` | `200` |
| `reranker_api` | `internal_api` | `dev` | `active_internal` | `hidden` | `http://dev.athanor.local:8003/health` | `http://192.168.1.189:8003/health` | `200` |
| `grafana` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:3000/` | `http://192.168.1.203:3000/` | `200` |
| `prometheus` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:9090/` | `http://192.168.1.203:9090/` | `200` |
| `uptime_kuma` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:3009/` | `http://192.168.1.203:3009/` | `200` |
| `langfuse` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:3030/` | `http://192.168.1.203:3030/` | `200` |
| `vault_litellm_proxy` | `internal_api` | `vault` | `active_internal` | `hidden` | `http://vault.athanor.local:4000/health` | `http://192.168.1.203:4000/health` | `401` |
| `vault_open_webui` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:3090/` | `http://192.168.1.203:3090/` | `200` |
| `qdrant_api` | `internal_api` | `vault` | `active_internal` | `hidden` | `http://vault.athanor.local:6333/collections` | `http://192.168.1.203:6333/collections` | `200` |
| `neo4j_browser` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:7474/` | `http://192.168.1.203:7474/` | `200` |
| `miniflux` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:8070/` | `http://192.168.1.203:8070/` | `200` |
| `home_assistant` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:8123/` | `http://192.168.1.203:8123/` | `200` |
| `tautulli` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:8181/` | `http://192.168.1.203:8181/` | `200` |
| `ntfy` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:8880/` | `http://192.168.1.203:8880/` | `200` |
| `sonarr` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:8989/` | `http://192.168.1.203:8989/` | `200` |
| `radarr` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:7878/` | `http://192.168.1.203:7878/` | `200` |
| `prowlarr` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:9696/` | `http://192.168.1.203:9696/` | `200` |
| `sabnzbd` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:8080/` | `http://192.168.1.203:8080/` | `200` |
| `stash` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:9999/` | `http://192.168.1.203:9999/` | `200` |
| `plex` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:32400/web` | `http://192.168.1.203:32400/web` | `200` |
| `workshop_open_webui` | `specialist_tool` | `workshop` | `active_specialist` | `launchpad` | `http://interface.athanor.local:3000/` | `http://192.168.1.225:3000/` | `200` |
| `comfyui` | `specialist_tool` | `workshop` | `active_specialist` | `launchpad` | `http://interface.athanor.local:8188/` | `http://192.168.1.225:8188/` | `200` |
| `eoq` | `domain_app` | `workshop` | `active_specialist` | `launchpad` | `http://interface.athanor.local:3002/` | `http://192.168.1.225:3002/` | `200` |
| `ulrich_energy` | `domain_app` | `workshop` | `active_specialist` | `launchpad` | `http://interface.athanor.local:3003/` | `http://192.168.1.225:3003/` | `200` |
| `ws_pty_bridge` | `internal_api` | `workshop` | `active_internal` | `hidden` | `http://interface.athanor.local:3100/health` | `http://192.168.1.225:3100/health` | `200` |
| `workshop_worker_api` | `internal_api` | `workshop` | `active_internal` | `hidden` | `http://interface.athanor.local:8010/health` | `http://192.168.1.225:8010/health` | `200` |
| `aesthetic_scorer_api` | `internal_api` | `workshop` | `active_internal` | `hidden` | `http://interface.athanor.local:8050/` | `http://192.168.1.225:8050/` | `404` |
| `agent_server` | `internal_api` | `foundry` | `active_internal` | `hidden` | `http://core.athanor.local:9000/health` | `http://192.168.1.244:9000/health` | `200` |
| `gpu_orchestrator` | `internal_api` | `foundry` | `active_internal` | `hidden` | `http://core.athanor.local:9200/health` | `http://192.168.1.244:9200/health` | `200` |
| `speaches` | `specialist_tool` | `foundry` | `active_specialist` | `launchpad` | `http://core.athanor.local:8200/` | `http://192.168.1.244:8200/` | `200` |
| `foundry_coordinator_api` | `internal_api` | `foundry` | `active_internal` | `hidden` | `http://core.athanor.local:8000/health` | `http://192.168.1.244:8000/health` | `200` |
| `foundry_coder_api` | `internal_api` | `foundry` | `active_internal` | `hidden` | `http://core.athanor.local:8006/health` | `http://192.168.1.244:8006/health` | `200` |

## Known Drift

- `desk-operator-hostname-resolution-gap` (high): DEV now serves the command center cleanly through Caddy, but operator desktops still need athanor.local hostname resolution before the canonical URL is reachable without host overrides. Remediation: None

## Resolved Front-Door Drift

- `dev-command-center-static-asset-breakage` (high): Resolved on 2026-03-29 by moving DEV to the containerized dashboard runtime and validating sampled _next/static assets through both :3001 and Caddy.
- `workshop-shadow-command-center-live` (high): Resolved on 2026-03-29 by stopping and removing the WORKSHOP athanor-dashboard container.
- `front-door-reverse-proxy-not-deployed` (medium): Resolved on 2026-03-29 by deploying Caddy on DEV and fronting the dashboard at athanor.local.
- `repo-surfaces-still-certify-workshop-dashboard` (high): The active monitoring, Ansible, helper, and documentation surfaces have been rewritten away from WORKSHOP:3001. Remaining front-door drift is now client-side hostname rollout, not repo-certified split-brain.
