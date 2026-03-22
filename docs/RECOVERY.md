# Athanor Disaster Recovery

*Last updated: 2026-03-19*

---

## Overview

| Metric | Target |
|--------|--------|
| RTO | 2-4 hours (full cluster rebuild) |
| RPO | 24 hours (daily backups, some weekly) |
| SPOF | VAULT -- all databases, routing, monitoring, media |

VAULT failure = full-system outage. Every other node can be rebuilt from scratch; VAULT data cannot.

---

## Backup Inventory

| What | Schedule | Retention | Location (VAULT) | Script |
|------|----------|-----------|-----------------|--------|
| PostgreSQL | Daily 1:30am | 14 days | /mnt/user/data/backups/postgres/ | backup-postgres.sh |
| Stash DB | Daily 2:00am | 14 days | /mnt/user/data/backups/stash/ | backup-stash.sh |
| Qdrant snapshots | Daily 3:00am | 30 days | /mnt/user/data/backups/qdrant/ | backup-qdrant.sh |
| Neo4j dump | Daily 3:15am | 30 days | /mnt/user/data/backups/neo4j/ | backup-neo4j.sh |
| Appdata configs | Daily 4:00am | varies | /mnt/appdatacache/backups/appdata/ | backup-appdata.sh |
| Docker images | Monthly prune | 7 days | -- | cron (1st of month 5am) |

Scripts live at `/opt/athanor/scripts/` on VAULT. Cron entries reinstalled at boot via `/boot/config/go`.

### Verify Backups Are Fresh

```bash
# SSH to VAULT
ssh root@192.168.1.203

# Check each backup directory
ls -lht /mnt/user/data/backups/postgres/ | head -5
ls -lht /mnt/user/data/backups/stash/ | head -5
ls -lht /mnt/user/data/backups/qdrant/ | head -5
ls -lht /mnt/user/data/backups/neo4j/ | head -5
ls -lht /mnt/appdatacache/backups/appdata/ | head -5

# Check backup log
tail -50 /var/log/athanor-backup.log
```

**No offsite backup yet** -- Duplicati to Backblaze B2 is a blocker item.

---

## Service Restart Order

Dependencies flow top-to-bottom. Restore in this exact order:

### Phase 1: Databases (VAULT)
1. **Redis** -- task state, caches (ephemeral, agents rebuild on startup)
2. **PostgreSQL** -- Langfuse, Miniflux, field-inspect
3. **Qdrant** -- knowledge_vault, resources, episodic collections
4. **Neo4j** -- knowledge graph (3237 nodes)
5. **Meilisearch** -- search index

### Phase 2: Routing and Monitoring (VAULT)
6. **LiteLLM** -- all inference routes through here
7. **Prometheus** -- metrics collection
8. **Grafana** -- dashboards
9. **ntfy** -- push notifications

### Phase 3: Inference (FOUNDRY, WORKSHOP)
10. **vllm-coordinator** (FOUNDRY) -- Qwen3.5-27B-FP8 TP=4
11. **vllm-coder** (FOUNDRY) -- Qwen3-Coder-30B
12. **vllm-vision** (WORKSHOP) -- Qwen3.5-35B-A3B-AWQ-4bit
13. **Ollama** (WORKSHOP) -- JOSIEFIED-Qwen3-8B uncensored

### Phase 4: Application Services
14. **Agent Server** (FOUNDRY) -- 9 LangGraph agents
15. **DEV systemd services** -- Gateway, MIND, Memory, Perception, UI
16. **Embedding + Reranker** (DEV) -- Qwen3-Embedding + Reranker
17. **ComfyUI** (WORKSHOP) -- image generation
18. **Dashboard** (WORKSHOP) -- command center

### Phase 5: Media and Auxiliary (VAULT)
19. Stash, Plex, Tautulli, Sonarr, Radarr, Prowlarr, Whisparr, Seerr, Bazarr
20. Tdarr (server + node), qBittorrent/gluetun, SABnzbd
21. Langfuse, Uptime Kuma, Vaultwarden, Headscale, Gitea, n8n

---

## VAULT Container Recreation

SSH: `ssh root@192.168.1.203` (key-only, root password login disabled)

### Core Databases

```bash
# Redis
docker run -d --name redis --restart unless-stopped \
  -v /mnt/user/appdata/redis:/data \
  redis:7-alpine redis-server --requirepass CHANGE_ME --appendonly yes

# PostgreSQL (shared)
docker run -d --name postgres --restart unless-stopped \
  -p 5432:5432 \
  -v /mnt/user/appdata/postgres:/var/lib/postgresql/data \
  -e POSTGRES_PASSWORD=CHANGE_ME \
  postgres:16-alpine

# Qdrant
docker run -d --name qdrant --restart unless-stopped \
  -p 6333:6333 -p 6334:6334 \
  -v /mnt/user/appdata/qdrant:/qdrant/storage \
  qdrant/qdrant:v1.17.0

# Neo4j
docker run -d --name neo4j --restart unless-stopped \
  -p 7474:7474 -p 7687:7687 \
  -v /mnt/user/appdata/neo4j/data:/data \
  -e NEO4J_AUTH=neo4j/CHANGE_ME \
  neo4j:5-community

# Meilisearch
docker run -d --name meilisearch --restart unless-stopped \
  -p 7700:7700 \
  -v /mnt/user/appdata/meilisearch:/meili_data \
  getmeili/meilisearch:latest
```

### LiteLLM

```bash
docker run -d --name litellm --restart unless-stopped \
  -p 4000:4000 \
  -v /mnt/user/appdata/litellm:/app/config \
  --env-file /mnt/user/appdata/litellm/.env \
  ghcr.io/berriai/litellm:main-v1.81.9-stable \
  --config /app/config/config.yaml

# Verify
curl -H "Authorization: Bearer <REDACTED-see-~/.secrets/litellm-master-key>" http://localhost:4000/health
```

### Monitoring

```bash
# Prometheus
docker run -d --name prometheus --restart unless-stopped \
  -v /mnt/user/appdata/prometheus:/etc/prometheus \
  -v /mnt/user/appdata/prometheus/data:/prometheus \
  prom/prometheus:latest

# Grafana
docker run -d --name grafana --restart unless-stopped \
  -p 3000:3000 \
  -v /mnt/user/appdata/grafana:/var/lib/grafana \
  grafana/grafana:latest

# ntfy
docker run -d --name ntfy --restart unless-stopped \
  -p 8880:80 \
  -v /mnt/user/appdata/ntfy:/etc/ntfy \
  binwiederhier/ntfy serve
```

### Stash (with Intel VAAPI)

```bash
docker run -d --name stash --restart unless-stopped \
  -p 9999:9999 \
  --device /dev/dri:/dev/dri \
  --entrypoint /bin/bash \
  -v /mnt/user/appdata/stash/config:/root/.stash \
  -v /mnt/user/data/media/whisparr:/data/whisparr:ro \
  -v /mnt/user/data/media/stash:/data/stash:ro \
  -v /mnt/user/appdata/stash/generated:/generated \
  -v /mnt/user/appdata/stash/metadata:/metadata \
  -v /mnt/user/appdata/stash/cache:/cache \
  feederbox826/stash-s6:latest \
  -c "/root/.stash/intel-vaapi-init.sh"
# Note: intel-vaapi-init.sh installs intel-media-driver then runs /opt/entrypoint.sh
```

### Tdarr (server + node)

```bash
# Server (no internal node, memory-limited)
docker run -d --name tdarr_server --restart unless-stopped \
  --memory=16g \
  -p 8265:8265 -p 8266:8266 \
  -v /mnt/user/appdata/tdarr/server:/app/server \
  -v /mnt/user/appdata/tdarr/configs:/app/configs \
  -v /mnt/user/appdata/tdarr/logs:/app/logs \
  -v /mnt/user/data/media:/media \
  -e internalNode=false \
  ghcr.io/haveagitgat/tdarr:latest

# External node (ARC A380 QSV)
docker run -d --name tdarr_node --restart unless-stopped \
  --device /dev/dri:/dev/dri \
  -v /mnt/user/appdata/tdarr/configs:/app/configs \
  -v /mnt/user/appdata/tdarr/logs:/app/logs \
  -v /mnt/user/data/media:/media \
  -v /mnt/transcode:/temp \
  -e serverIP=192.168.1.203 -e serverPort=8266 \
  ghcr.io/haveagitgat/tdarr_node:latest
```

### Langfuse (multi-container)

```bash
cd /mnt/user/appdata/langfuse
docker compose up -d
# Containers: langfuse-web, langfuse-worker, langfuse-postgres,
#   langfuse-redis, langfuse-clickhouse, langfuse-minio
# Web UI: port 3030
```

### Media Stack (Plex/Sonarr/Radarr/etc.)

Most media containers use linuxserver.io images with similar patterns:
```bash
# Pattern for *arr apps
docker run -d --name sonarr --restart unless-stopped \
  -p 8989:8989 \
  -v /mnt/user/appdata/sonarr:/config \
  -v /mnt/user/data/media:/data \
  -e PUID=99 -e PGID=100 \
  lscr.io/linuxserver/sonarr:latest

# Same pattern for: radarr(:7878), prowlarr(:9696), bazarr(:6767),
# whisparr(:6969), tautulli(:8181), sabnzbd(:8080), plex
```

### Auxiliary

```bash
# Uptime Kuma
docker run -d --name uptime-kuma --restart unless-stopped \
  -p 3009:3001 -v /mnt/user/appdata/uptime-kuma:/app/data \
  louislam/uptime-kuma:1

# Vaultwarden
docker run -d --name vaultwarden --restart unless-stopped \
  -p 8222:80 -v /mnt/user/appdata/vaultwarden:/data \
  vaultwarden/server:latest

# Headscale
docker run -d --name headscale --restart unless-stopped \
  -p 8443:8443 -v /mnt/user/appdata/headscale:/etc/headscale \
  headscale/headscale:0.23 serve

# Gitea
docker run -d --name gitea --restart unless-stopped \
  -p 3033:3000 -p 2222:22 \
  -v /mnt/user/appdata/gitea:/data \
  gitea/gitea:1.23-rootless
```

---

## Node Rebuild Playbooks

### VAULT Rebuild (Unraid 7.2.0)

1. Install Unraid, restore USB key backup
2. Assign disks to array, start array
3. Configure NVMe pools:
   - nvme0 -> /mnt/appdatacache
   - nvme1 -> /mnt/transcode
   - nvme2 -> /mnt/docker + 8GB swapfile
4. Docker directory: `/mnt/docker` (set in `/boot/config/docker.cfg`: `DOCKER_IMAGE_FILE=""`, `DOCKER_DIR="/mnt/docker"`)
5. Install Community Apps plugin
6. Restore SSH keys: `/boot/config/ssh/root/.ssh/authorized_keys`
7. Pull and start containers (order above)
8. Restore databases from backups (see restore procedures below)
9. Restore cron jobs (sourced from `/boot/config/go` at boot)
10. Set bond0 MTU to 9000 in `/boot/config/network.cfg`

### FOUNDRY Rebuild

1. Install Ubuntu (or container-optimized OS)
2. Install NVIDIA drivers + container toolkit (5 GPUs: 4x5070Ti + 1x4090)
3. Install Docker
4. Mount VAULT NFS: add to `/etc/fstab`: `192.168.1.203:/mnt/user/data/models /mnt/vault/models nfs defaults 0 0`
5. Rsync models to local NVMe: `rsync -avP /mnt/vault/models/ /mnt/local-fast/models/`
6. Set sysctl in `/etc/sysctl.d/99-athanor.conf`:
   ```
   vm.vfs_cache_pressure=50
   vm.dirty_ratio=10
   vm.dirty_background_ratio=5
   ```
7. Start containers:
   ```bash
   # vllm-coordinator (TP=4 across GPUs 0,1,3,4)
   docker run -d --name vllm-coordinator --runtime nvidia \
     --gpus '"device=0,1,3,4"' --shm-size 16gb \
     -e FLASHINFER_DISABLE_VERSION_CHECK=1 \
     --restart unless-stopped athanor/vllm:qwen35 \
     python3 -m vllm.entrypoints.openai.api_server \
     --model /models/Qwen3.5-27B-FP8 --served-model-name qwen3.5 \
     --host 0.0.0.0 --port 8000 --tensor-parallel-size 4

   # vllm-coder (GPU 2 - 4090)
   docker run -d --name vllm-coder --runtime nvidia \
     --gpus device=2 -p 8006:8000 \
     -v /mnt/local-fast/models:/models \
     -e FLASHINFER_DISABLE_VERSION_CHECK=1 --shm-size 8gb \
     --restart unless-stopped athanor/vllm:qwen35 \
     python3 -m vllm.entrypoints.openai.api_server \
     --model /models/Qwen3-Coder-30B-A3B-Instruct-AWQ \
     --served-model-name qwen3-coder --host 0.0.0.0 --port 8000 \
     --max-model-len 32768 --gpu-memory-utilization 0.92 \
     --max-num-seqs 16 --enable-auto-tool-choice \
     --tool-call-parser hermes --enable-prefix-caching --dtype auto

   # Agent server
   docker run -d --name athanor-agents --restart unless-stopped \
     -p 9000:9000 --env-file /opt/athanor/agents/.env \
     athanor/agents:latest

   # GPU orchestrator
   docker run -d --name athanor-gpu-orchestrator --restart unless-stopped \
     athanor/gpu-orchestrator:latest

   # Monitoring
   docker run -d --name node-exporter --restart unless-stopped \
     prom/node-exporter:latest
   docker run -d --name dcgm-exporter --restart unless-stopped \
     -p 9400:9400 --runtime nvidia --gpus all \
     nvcr.io/nvidia/k8s/dcgm-exporter:3.3.9-3.6.1-ubuntu22.04
   ```
8. Note: EPYC takes ~3 minutes to POST (224GB ECC RAM check)

### WORKSHOP Rebuild

1. Install Ubuntu
2. Install NVIDIA drivers (RTX 5090 + RTX 5060 Ti)
3. Install Docker
4. SSH user is `athanor` (NOT shaun). Key: `athanor_mgmt`
5. Mount VAULT NFS for models
6. Start containers:
   ```bash
   # vllm-vision (GPU 0 - 5090)
   docker run -d --name vllm-vision --runtime nvidia \
     --gpus device=0 --shm-size 16gb \
     -e FLASHINFER_DISABLE_VERSION_CHECK=1 \
     --restart unless-stopped athanor/vllm:qwen35 \
     python3 -m vllm.entrypoints.openai.api_server \
     --model /models/Qwen3.5-35B-A3B-AWQ-4bit \
     --host 0.0.0.0 --port 8000

   # ComfyUI (GPU 1 - 5060 Ti)
   docker run -d --name comfyui --runtime nvidia \
     --gpus device=1 -p 8188:8188 \
     -v /mnt/vault/models/comfyui:/opt/ComfyUI/models \
     --restart unless-stopped athanor/comfyui:blackwell

   # Ollama
   docker run -d --name ollama --runtime nvidia \
     -p 11434:11434 \
     -v /mnt/user/appdata/ollama:/root/.ollama \
     --restart unless-stopped ollama/ollama:latest
   # Then: docker exec ollama ollama pull qwen3:8b

   # Aesthetic scorer
   docker run -d --name aesthetic-scorer --restart unless-stopped \
     -p 8050:8050 aesthetic-scorer-aesthetic-scorer

   # Dashboard
   docker run -d --name athanor-dashboard --restart unless-stopped \
     -p 3001:3001 athanor/dashboard:latest

   # Monitoring
   docker run -d --name node-exporter --restart unless-stopped \
     prom/node-exporter:latest
   docker run -d --name dcgm-exporter --restart unless-stopped \
     -p 9400:9400 --runtime nvidia --gpus all \
     nvcr.io/nvidia/k8s/dcgm-exporter:3.3.9-3.6.1-ubuntu22.04
   ```

### DEV Rebuild (Ubuntu 24.04)

1. Install Ubuntu 24.04, NVIDIA drivers (RTX 5060 Ti)
2. Install: Docker, Python 3.12+, uv, Node.js (system apt, NOT nvm), git
3. Clone repo: `git clone <repo-url> /home/shaun/repos/athanor`
4. Install Python deps: `cd /home/shaun/repos/athanor && uv sync`
5. Copy `.env` from backup or recreate from template
6. Set up systemd services:
   ```bash
   sudo cp deploy/systemd/local-system-*.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now local-system-gateway local-system-mind \
     local-system-memory local-system-perception local-system-ui
   ```
7. Start Docker containers:
   ```bash
   # Embedding
   docker run -d --name vllm-embedding --runtime nvidia \
     -p 8001:8001 --restart unless-stopped \
     nvcr.io/nvidia/vllm:25.12-py3 \
     python3 -m vllm.entrypoints.openai.api_server \
     --model Qwen/Qwen3-Embedding-0.6B --host 0.0.0.0 --port 8001

   # Reranker
   docker run -d --name vllm-reranker --runtime nvidia \
     -p 8003:8003 --restart unless-stopped \
     nvcr.io/nvidia/vllm:25.12-py3 \
     python3 -m vllm.entrypoints.openai.api_server \
     --model Qwen/Qwen3-Reranker-0.6B --host 0.0.0.0 --port 8003
   ```
8. Set up daily maintenance cron (3am)
9. Install OpenFang: binary at `/usr/local/bin/openfang`, config at `~/.openfang/`
10. Set up cluster health timer (systemd, every 5 min)

---

## Database Restore Procedures

### PostgreSQL Restore

```bash
# On VAULT
ls -lt /mnt/user/data/backups/postgres/ | head -5
# Restore latest dump
docker exec -i postgres psql -U postgres < /mnt/user/data/backups/postgres/LATEST.sql
```

### Qdrant Restore

```bash
# List snapshots
ls /mnt/user/data/backups/qdrant/

# Restore each collection
for collection in knowledge_vault resources episodic; do
  curl -X POST "http://localhost:6333/collections/${collection}/snapshots/recover" \
    -H "Content-Type: application/json" \
    -d "{\"location\": \"file:///mnt/user/data/backups/qdrant/${collection}-latest.snapshot\"}"
done
```

### Neo4j Restore

```bash
docker stop neo4j
docker run --rm \
  -v /mnt/user/appdata/neo4j/data:/data \
  -v /mnt/user/data/backups/neo4j:/backups \
  neo4j:5-community neo4j-admin database load \
  --from=/backups/neo4j-latest.dump neo4j --overwrite-destination
docker start neo4j
```

### Stash Restore

```bash
docker stop stash
cp /mnt/user/data/backups/stash/stash-go-latest.sqlite \
   /mnt/user/appdata/stash/config/stash-go.sqlite
docker start stash
```

---

## Critical Config Locations

| Config | Path | Node |
|--------|------|------|
| LiteLLM config | /mnt/user/appdata/litellm/config.yaml | VAULT |
| LiteLLM env | /mnt/user/appdata/litellm/.env | VAULT |
| Prometheus config | /mnt/user/appdata/prometheus/prometheus.yml | VAULT |
| Grafana data | /mnt/user/appdata/grafana/ | VAULT |
| Stash config | /mnt/user/appdata/stash/config/ | VAULT |
| Stash VAAPI init | /mnt/user/appdata/stash/config/intel-vaapi-init.sh | VAULT |
| Tdarr config | /mnt/user/appdata/tdarr/ | VAULT |
| VAULT SSH keys | /boot/config/ssh/root/.ssh/authorized_keys | VAULT |
| VAULT cron/boot | /boot/config/go | VAULT |
| VAULT Docker cfg | /boot/config/docker.cfg | VAULT |
| VAULT network | /boot/config/network.cfg | VAULT |
| Backup scripts | /opt/athanor/scripts/ | VAULT |
| Repo + .env | /home/shaun/repos/athanor/ | DEV |
| Systemd units | /etc/systemd/system/local-system-*.service | DEV |
| OpenFang config | ~/.openfang/config.toml | DEV |
| Agent server env | /opt/athanor/agents/.env | FOUNDRY |
| FOUNDRY sysctl | /etc/sysctl.d/99-athanor.conf | FOUNDRY |
| NFS models mount | /mnt/vault/models/ (fstab) | FOUNDRY, WORKSHOP |
| NVMe model cache | /mnt/local-fast/models/ | FOUNDRY |

---

## Health Check Verification

Run after recovery to confirm all services are operational:

```bash
# === VAULT ===
curl -s -H "Authorization: Bearer <REDACTED-see-~/.secrets/litellm-master-key>" \
  http://192.168.1.203:4000/health | python3 -m json.tool
curl -s http://192.168.1.203:6333/collections | python3 -m json.tool
curl -s http://192.168.1.203:7474 | head -5
docker exec redis redis-cli -a PASSWORD ping  # expect PONG
curl -s http://192.168.1.203:9999  # Stash

# Prometheus target count
curl -s http://192.168.1.203:9090/api/v1/targets | \
  python3 -c "import sys,json; t=json.load(sys.stdin); \
  up=sum(1 for x in t['data']['activeTargets'] if x['health']=='up'); \
  total=len(t['data']['activeTargets']); print(f'{up}/{total} targets UP')"

# === FOUNDRY ===
curl -s http://192.168.1.244:8000/v1/models | python3 -m json.tool
curl -s http://192.168.1.244:8006/v1/models | python3 -m json.tool
curl -s http://192.168.1.244:9000/v1/agents

# === WORKSHOP ===
curl -s http://192.168.1.225:8000/v1/models | python3 -m json.tool
curl -s http://192.168.1.225:8188/system_stats | python3 -m json.tool
curl -s http://192.168.1.225:11434/api/tags

# === DEV ===
curl -s http://localhost:8700/health
curl -s http://localhost:8001/v1/models
curl -s http://localhost:8003/v1/models
systemctl status local-system-{gateway,mind,memory,perception,ui} --no-pager
```

---

## NFS Stale Handles (after VAULT reboot)

FOUNDRY and WORKSHOP mount `/mnt/vault/models/` from VAULT over NFS. After VAULT reboots:

```bash
# On FOUNDRY and WORKSHOP
sudo umount -f /mnt/vault/models
sudo mount -a

# Restart containers that were loading from NFS
docker restart vllm-coordinator vllm-coder  # FOUNDRY
docker restart vllm-vision comfyui          # WORKSHOP
```

---

## VAULT Cron Schedule

| Time | Job |
|------|-----|
| 1:30am daily | PostgreSQL backup |
| 2:00am daily | Stash DB backup |
| 3:00am daily | Qdrant snapshot backup |
| 3:15am daily | Neo4j dump backup |
| 3:30am Sunday | Tdarr: scan Whisparr library |
| 4:00am daily | Appdata config backup |
| 4:30am daily | Tdarr: cleanup old transcode temp files |
| Every 5 min | Container watchdog (auto-restart crashed containers) |
| 5:00am 1st/month | Docker image prune (>7 days) |

---

## Known Recovery Gotchas

- FOUNDRY EPYC takes ~3 minutes to POST (224GB ECC RAM check). Wait before SSH.
- VAULT SSH: root only, key-only auth. If native SSH hangs, use `python3 scripts/vault-ssh.py`
- Stash VAAPI: intel-vaapi-init.sh must run before stash. Container uses custom entrypoint.
- Tdarr: memory-limit server to 16GB or V8 heap will bloat to 46GB+
- LiteLLM: most cloud API keys are NOT in the container env. Only Anthropic works out of the box.
- vLLM needs `FLASHINFER_DISABLE_VERSION_CHECK=1` or it refuses to start.
- ComfyUI pip packages (insightface, facexlib, etc.) are lost on image rebuild. Reinstall after.
- PuLID Flux patch is in Docker volume, not git. Reapply if custom_nodes volume is recreated.
- Container watchdog script runs every 5 min and auto-restarts crashed containers.
- Unraid `/boot/config/go` is the boot script -- cron jobs and mount setup live here.
- Docker images tagged `athanor/*` are custom-built. If registry is lost, rebuild from Dockerfiles in repo.

---

*See also: `docs/SERVICES.md` (full service inventory), `docs/guides/` (operational guides)*
