# Deploy Docker Service

Standard pattern for deploying Docker Compose services on Athanor nodes.

## Instructions

When deploying a new service, follow this pattern:

### 1. Choose the Right Node

| Workload Type | Node | Reason |
|---------------|------|--------|
| GPU inference (multi-GPU) | Node 1 (192.168.1.244) | 4x RTX 5070 Ti, EPYC 56C |
| GPU creative/single-GPU | Node 2 (192.168.1.225) | RTX 5090 + RTX 4090 |
| Always-on services | VAULT (192.168.1.203) | Unraid, 24/7 operation |
| Media/storage-bound | VAULT | 164 TB array, NFS exports |
| Monitoring | VAULT | Survives compute node restarts |

### 2. Create Docker Compose File

Place compose files at:
- Nodes: `/opt/athanor/{service}/docker-compose.yml`
- VAULT: Use Unraid Docker or `/mnt/user/appdata/{service}/docker-compose.yml`

Standard compose template:
```yaml
services:
  {service}:
    image: {image}:{tag}
    container_name: {service}
    restart: unless-stopped
    # GPU access (if needed):
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['0']  # or 'all'
              capabilities: [gpu]
    ports:
      - "{host_port}:{container_port}"
    volumes:
      - ./data:/data
      # NFS model storage:
      - /mnt/vault/models:/models:ro
    environment:
      - TZ=America/Chicago
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{container_port}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "3"
```

### 3. Deploy

```bash
# SSH to the target node
ssh node1

# Create service directory
sudo mkdir -p /opt/athanor/{service}

# Copy or create compose file
# Then:
cd /opt/athanor/{service}
sudo docker compose up -d

# Verify
docker compose ps
docker compose logs --tail=50
```

### 4. Verify Health

```bash
# Check container status
docker ps --filter name={service}

# Check logs for errors
docker compose logs --tail=100 {service}

# Test health endpoint
curl -f http://localhost:{port}/health
```

### 5. Network Notes

- Compute nodes reach VAULT via 1GbE (192.168.1.x) — 10GbE pending physical cable move
- NFS shares from VAULT: /mnt/user/data, /mnt/user/models, /mnt/user/appdata, /mnt/user/system
- All services bind 0.0.0.0 for cross-node access
- DNS: Use IP addresses until DNS is configured

### 6. GPU Assignment

Node 1 (4x RTX 5070 Ti):
- GPU 0: PCIe 01:00.0
- GPU 1: PCIe 47:00.0
- GPU 2: PCIe 81:00.0
- GPU 3: PCIe 82:00.0 (display attached)
- For tensor parallelism: use `device_ids: ['all']` or `--gpus all`

Node 2 (RTX 4090 + RTX 5090):
- GPU 0: RTX 4090 (PCIe 01:00.0) — 24 GB GDDR6X
- GPU 1: RTX 5090 (PCIe 03:00.0) — 32 GB GDDR7
- Isolate with `NVIDIA_VISIBLE_DEVICES=0` or `device_ids: ['0']`
