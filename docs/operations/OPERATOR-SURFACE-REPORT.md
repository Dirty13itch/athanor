# Operator Surface Report

Generated from `config/automation-backbone/operator-surface-registry.json` plus the cached operator-surface live probe in `reports/truth-inventory/latest.json` by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

## Front Door Contract

- Registry version: `2026-03-29.1`
- Cached truth snapshot: `2026-04-03T03:48:09.972834+00:00`
- Canonical portal id: `athanor_command_center`
- Canonical operator URL: `https://athanor.local/`
- Canonical node: `dev`
- Runtime service id: `dashboard`
- Current runtime mode: `containerized_service_behind_caddy`
- Target runtime mode: `containerized_service_behind_caddy`
- Multiple active portals allowed: `False`
- Promotion gate: Canonical DEV command center remains reachable from operator desktops at athanor.local, the WORKSHOP shadow portal stays retired, and browser smoke stays green.

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
| `active_production` | 1 |
| `active_specialist` | 21 |
| `retired` | 1 |

## Canonical Portal

- Label: `Athanor Command Center`
- Status: `active_production`
- Canonical URL: `https://athanor.local/`
- Runtime URL: `http://dev.athanor.local:3001/`
- Deployment mode: `containerized_service_behind_caddy`
- Target deployment mode: `containerized_service_behind_caddy`
- Canonical probe: `URLError: timed out`
- Runtime probe: `URLError: timed out`
- Runtime Next.js asset probe: `unknown` root, `0` failing sampled asset(s)
- Sampled failing assets: none

## Shadow Portal

No shadow portals are currently registered.

## Launchpad Surfaces

| Surface | Node | Kind | Canonical URL | Operator role | Canonical probe |
| --- | --- | --- | --- | --- | --- |
| `Grafana` | `vault` | `specialist_tool` | `http://vault.athanor.local:3000/` | `observability` | `200` |
| `Prometheus` | `vault` | `specialist_tool` | `http://vault.athanor.local:9090/` | `observability` | `200` |
| `Uptime Kuma` | `vault` | `specialist_tool` | `http://vault.athanor.local:3009/` | `observability` | `URLError: [WinError 10061] No connection could b` |
| `Langfuse` | `vault` | `specialist_tool` | `http://vault.athanor.local:3030/` | `observability` | `200` |
| `Open WebUI (VAULT)` | `vault` | `specialist_tool` | `http://vault.athanor.local:3090/` | `chat` | `200` |
| `Neo4j Browser` | `vault` | `specialist_tool` | `http://vault.athanor.local:7474/` | `knowledge` | `URLError: [WinError 10061] No connection could b` |
| `Miniflux` | `vault` | `specialist_tool` | `http://vault.athanor.local:8070/` | `knowledge` | `200` |
| `Home Assistant` | `vault` | `specialist_tool` | `http://vault.athanor.local:8123/` | `home` | `200` |
| `Tautulli` | `vault` | `specialist_tool` | `http://vault.athanor.local:8181/` | `media` | `URLError: [WinError 10061] No connection could b` |
| `ntfy` | `vault` | `specialist_tool` | `http://vault.athanor.local:8880/` | `observability` | `200` |
| `Sonarr` | `vault` | `specialist_tool` | `http://vault.athanor.local:8989/` | `media` | `URLError: [WinError 10061] No connection could b` |
| `Radarr` | `vault` | `specialist_tool` | `http://vault.athanor.local:7878/` | `media` | `URLError: [WinError 10061] No connection could b` |
| `Prowlarr` | `vault` | `specialist_tool` | `http://vault.athanor.local:9696/` | `media` | `URLError: [WinError 10061] No connection could b` |
| `SABnzbd` | `vault` | `specialist_tool` | `http://vault.athanor.local:8080/` | `media` | `200` |
| `Stash` | `vault` | `specialist_tool` | `http://vault.athanor.local:9999/` | `media` | `URLError: [WinError 10061] No connection could b` |
| `Plex` | `vault` | `specialist_tool` | `http://vault.athanor.local:32400/web` | `media` | `URLError: [WinError 10061] No connection could b` |
| `Open WebUI (WORKSHOP)` | `workshop` | `specialist_tool` | `http://interface.athanor.local:3000/` | `chat` | `URLError: timed out` |
| `ComfyUI` | `workshop` | `specialist_tool` | `http://interface.athanor.local:8188/` | `creative` | `URLError: timed out` |
| `Empire of Broken Queens` | `workshop` | `domain_app` | `http://interface.athanor.local:3002/` | `domain_product` | `URLError: timed out` |
| `Ulrich Energy` | `workshop` | `domain_app` | `http://interface.athanor.local:3003/` | `domain_product` | `URLError: timed out` |
| `Speaches` | `foundry` | `specialist_tool` | `http://core.athanor.local:8200/` | `creative` | `URLError: timed out` |

## Full Surface Matrix

| Surface | Kind | Node | Status | Navigation | Canonical URL | Runtime URL | Runtime probe |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `athanor_command_center` | `portal` | `dev` | `active_production` | `front_door` | `https://athanor.local/` | `http://dev.athanor.local:3001/` | `URLError: timed out` |
| `workshop_shadow_command_center` | `retired` | `workshop` | `retired` | `hidden` | `https://athanor.local/` | `http://interface.athanor.local:3001/` | `URLError: timed out` |
| `quality_gate` | `internal_api` | `dev` | `active_internal` | `hidden` | `http://dev.athanor.local:8790/health` | `http://192.168.1.189:8790/health` | `URLError: timed out` |
| `semantic_router` | `internal_api` | `dev` | `active_internal` | `hidden` | `http://dev.athanor.local:8060/health` | `http://192.168.1.189:8060/health` | `URLError: timed out` |
| `subscription_burn` | `internal_api` | `dev` | `active_internal` | `hidden` | `http://dev.athanor.local:8065/health` | `http://192.168.1.189:8065/health` | `URLError: timed out` |
| `embedding_api` | `internal_api` | `dev` | `active_internal` | `hidden` | `http://dev.athanor.local:8001/health` | `http://192.168.1.189:8001/health` | `URLError: timed out` |
| `reranker_api` | `internal_api` | `dev` | `active_internal` | `hidden` | `http://dev.athanor.local:8003/health` | `http://192.168.1.189:8003/health` | `URLError: timed out` |
| `grafana` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:3000/` | `http://192.168.1.203:3000/` | `200` |
| `prometheus` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:9090/` | `http://192.168.1.203:9090/` | `200` |
| `uptime_kuma` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:3009/` | `http://192.168.1.203:3009/` | `URLError: [WinError 10061] No connection could b` |
| `langfuse` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:3030/` | `http://192.168.1.203:3030/` | `200` |
| `vault_litellm_proxy` | `internal_api` | `vault` | `active_internal` | `hidden` | `http://vault.athanor.local:4000/health` | `http://192.168.1.203:4000/health` | `401` |
| `vault_open_webui` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:3090/` | `http://192.168.1.203:3090/` | `200` |
| `qdrant_api` | `internal_api` | `vault` | `active_internal` | `hidden` | `http://vault.athanor.local:6333/collections` | `http://192.168.1.203:6333/collections` | `200` |
| `neo4j_browser` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:7474/` | `http://192.168.1.203:7474/` | `URLError: [WinError 10061] No connection could b` |
| `miniflux` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:8070/` | `http://192.168.1.203:8070/` | `200` |
| `home_assistant` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:8123/` | `http://192.168.1.203:8123/` | `200` |
| `tautulli` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:8181/` | `http://192.168.1.203:8181/` | `URLError: [WinError 10061] No connection could b` |
| `ntfy` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:8880/` | `http://192.168.1.203:8880/` | `200` |
| `sonarr` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:8989/` | `http://192.168.1.203:8989/` | `URLError: [WinError 10061] No connection could b` |
| `radarr` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:7878/` | `http://192.168.1.203:7878/` | `URLError: [WinError 10061] No connection could b` |
| `prowlarr` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:9696/` | `http://192.168.1.203:9696/` | `URLError: [WinError 10061] No connection could b` |
| `sabnzbd` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:8080/` | `http://192.168.1.203:8080/` | `200` |
| `stash` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:9999/` | `http://192.168.1.203:9999/` | `URLError: [WinError 10061] No connection could b` |
| `plex` | `specialist_tool` | `vault` | `active_specialist` | `launchpad` | `http://vault.athanor.local:32400/web` | `http://192.168.1.203:32400/web` | `URLError: [WinError 10061] No connection could b` |
| `workshop_open_webui` | `specialist_tool` | `workshop` | `active_specialist` | `launchpad` | `http://interface.athanor.local:3000/` | `http://192.168.1.225:3000/` | `URLError: timed out` |
| `comfyui` | `specialist_tool` | `workshop` | `active_specialist` | `launchpad` | `http://interface.athanor.local:8188/` | `http://192.168.1.225:8188/` | `URLError: timed out` |
| `eoq` | `domain_app` | `workshop` | `active_specialist` | `launchpad` | `http://interface.athanor.local:3002/` | `http://192.168.1.225:3002/` | `URLError: timed out` |
| `ulrich_energy` | `domain_app` | `workshop` | `active_specialist` | `launchpad` | `http://interface.athanor.local:3003/` | `http://192.168.1.225:3003/` | `URLError: timed out` |
| `ws_pty_bridge` | `internal_api` | `workshop` | `active_internal` | `hidden` | `http://interface.athanor.local:3100/health` | `http://192.168.1.225:3100/health` | `URLError: timed out` |
| `workshop_worker_api` | `internal_api` | `workshop` | `active_internal` | `hidden` | `http://interface.athanor.local:8010/health` | `http://192.168.1.225:8010/health` | `URLError: timed out` |
| `aesthetic_scorer_api` | `internal_api` | `workshop` | `active_internal` | `hidden` | `http://interface.athanor.local:8050/` | `http://192.168.1.225:8050/` | `URLError: timed out` |
| `agent_server` | `internal_api` | `foundry` | `active_internal` | `hidden` | `http://core.athanor.local:9000/health` | `http://192.168.1.244:9000/health` | `URLError: timed out` |
| `gpu_orchestrator` | `internal_api` | `foundry` | `active_internal` | `hidden` | `http://core.athanor.local:9200/health` | `http://192.168.1.244:9200/health` | `URLError: timed out` |
| `speaches` | `specialist_tool` | `foundry` | `active_specialist` | `launchpad` | `http://core.athanor.local:8200/` | `http://192.168.1.244:8200/` | `URLError: timed out` |
| `foundry_coordinator_api` | `internal_api` | `foundry` | `active_internal` | `hidden` | `http://core.athanor.local:8000/health` | `http://192.168.1.244:8000/health` | `URLError: timed out` |
| `foundry_coder_api` | `internal_api` | `foundry` | `active_internal` | `hidden` | `http://core.athanor.local:8006/health` | `http://192.168.1.244:8006/health` | `URLError: timed out` |

## Known Drift

- `additional-operator-clients-hostname-rollout-gap` (low): DESK now resolves the canonical command-center and node-host aliases, but any additional operator clients still need the same scripted hosts-file rollout or internal DNS before athanor.local and the *.athanor.local deep links work there. Remediation: None

## Resolved Front-Door Drift

- `desk-operator-hostname-resolution-gap` (high): Resolved on 2026-03-29 by rolling the scripted DESK hosts-file aliases for athanor.local plus the node-host deep links.
- `dev-command-center-static-asset-breakage` (high): Resolved on 2026-03-29 by moving DEV to the containerized dashboard runtime and validating sampled _next/static assets through both :3001 and Caddy.
- `workshop-shadow-command-center-live` (high): Resolved on 2026-03-29 by stopping and removing the WORKSHOP athanor-dashboard container.
- `front-door-reverse-proxy-not-deployed` (medium): Resolved on 2026-03-29 by deploying Caddy on DEV and fronting the dashboard at athanor.local.
- `repo-surfaces-still-certify-workshop-dashboard` (high): Resolved on 2026-03-29 by rewriting the active monitoring, Ansible, helper, and documentation surfaces away from WORKSHOP:3001.
