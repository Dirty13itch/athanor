export const config = {
  prometheus: {
    url: process.env.NEXT_PUBLIC_PROMETHEUS_URL ?? "http://192.168.1.203:9090",
  },
  agentServer: {
    url: "http://192.168.1.244:9000",
  },
  comfyui: {
    url: "http://192.168.1.225:8188",
  },
  stash: {
    url: "http://192.168.1.203:9999",
  },
  speaches: {
    url: "http://192.168.1.244:8200",
  },
  homeAssistant: {
    url: "http://192.168.1.203:8123",
  },
  litellm: {
    url: "http://192.168.1.203:4000",
    apiKey: "sk-athanor-litellm-2026",
  },
  inferenceBackends: [
    {
      name: "LiteLLM Proxy",
      url: "http://192.168.1.203:4000",
    },
    {
      name: "Node 1 — Qwen3.5-27B-FP8",
      url: "http://192.168.1.244:8000",
    },
    {
      name: "Node 2 — Qwen3.5-35B-A3B-AWQ",
      url: "http://192.168.1.225:8000",
    },
    {
      name: "Agents",
      url: "http://192.168.1.244:9000",
    },
  ],
  services: [
    { name: "LiteLLM Proxy", url: "http://192.168.1.203:4000/health/readiness", node: "VAULT" },
    { name: "vLLM (Node 1)", url: "http://192.168.1.244:8000/v1/models", node: "Foundry" },
    { name: "vLLM Embedding", url: "http://192.168.1.244:8001/health", node: "Foundry" },
    { name: "vLLM (Node 2)", url: "http://192.168.1.225:8000/v1/models", node: "Workshop" },
    { name: "Qdrant", url: "http://192.168.1.244:6333/collections", node: "Foundry" },
    { name: "Agent Server", url: "http://192.168.1.244:9000/health", node: "Foundry" },
    { name: "Prometheus", url: "http://192.168.1.203:9090/-/healthy", node: "VAULT" },
    { name: "Grafana", url: "http://192.168.1.203:3000/api/health", node: "VAULT" },
    { name: "Node Exporter (Node 1)", url: "http://192.168.1.244:9100/metrics", node: "Foundry" },
    { name: "Node Exporter (Node 2)", url: "http://192.168.1.225:9100/metrics", node: "Workshop" },
    { name: "DCGM Exporter (Node 1)", url: "http://192.168.1.244:9400/metrics", node: "Foundry" },
    { name: "DCGM Exporter (Node 2)", url: "http://192.168.1.225:9400/metrics", node: "Workshop" },
    { name: "ComfyUI", url: "http://192.168.1.225:8188/system_stats", node: "Workshop" },
    { name: "Open WebUI", url: "http://192.168.1.225:3000", node: "Workshop" },
    { name: "EoBQ", url: "http://192.168.1.225:3002", node: "Workshop" },
    { name: "Sonarr", url: "http://192.168.1.203:8989/ping", node: "VAULT" },
    { name: "Radarr", url: "http://192.168.1.203:7878/ping", node: "VAULT" },
    { name: "Tautulli", url: "http://192.168.1.203:8181", node: "VAULT" },
    { name: "Plex", url: "http://192.168.1.203:32400/identity", node: "VAULT" },
    { name: "SABnzbd", url: "http://192.168.1.203:8080", node: "VAULT" },
    { name: "Prowlarr", url: "http://192.168.1.203:9696/ping", node: "VAULT" },
    { name: "Stash", url: "http://192.168.1.203:9999", node: "VAULT" },
    { name: "Home Assistant", url: "http://192.168.1.203:8123/api/", node: "VAULT", headers: { "Authorization": "Bearer eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJpc3MiOiAiYTQ2ZTRlNTJhZDFjNjgwNzg0ZDQ2NDc2N2NiNmJiZWEiLCAiaWF0IjogMTc3MTk4MzcxNCwgImV4cCI6IDIwODczNDM3MTR9.rvM9WSMEZucl9XTV-zRs1ts21vFAKeQFQRedIY2bVAs" } },
    { name: "Neo4j", url: "http://192.168.1.203:7474", node: "VAULT" },
    { name: "GPU Orchestrator", url: "http://192.168.1.244:9200/health", node: "Foundry" },
    { name: "Speaches", url: "http://192.168.1.244:8200/health", node: "Foundry" },
  ],
  nodes: [
    { name: "Foundry", ip: "192.168.1.244", role: "AI inference + agents", gpuCount: 5, vram: 88, psuWatts: 1600 },
    { name: "Workshop", ip: "192.168.1.225", role: "Creative + interface", gpuCount: 2, vram: 48, psuWatts: 1600 },
    { name: "VAULT", ip: "192.168.1.203", role: "Storage + media + monitoring", gpuCount: 0, vram: 0, psuWatts: 0 },
  ],
  // Known GPU → workload mapping (static, will be made dynamic later)
  gpuWorkloads: {
    "192.168.1.244": {
      0: "Qwen3.5-27B-FP8 TP=4",
      1: "Qwen3.5-27B-FP8 TP=4",
      2: "Huihui-Qwen3-8B utility (4090)",
      3: "Qwen3.5-27B-FP8 TP=4",
      4: "Qwen3.5-27B-FP8 TP=4",
    },
    "192.168.1.225": {
      0: "Qwen3.5-35B-A3B-AWQ (5090)",
      1: "ComfyUI / Flux (5060 Ti)",
    },
  } as Record<string, Record<number, string>>,
  // Power limits per GPU (watts) — matches Ansible config
  gpuPowerLimits: {
    "192.168.1.244": { 0: 300, 1: 300, 2: 450, 3: 300, 4: 300 },
    "192.168.1.225": { 0: 575, 1: 200 },
  } as Record<string, Record<number, number>>,
  quickLinks: [
    { name: "Grafana", url: "http://192.168.1.203:3000/d/3349e8df-5e19-458f-b663-29c2075b73bf/athanor-operations", node: "VAULT", category: "monitoring" },
    { name: "Prometheus", url: "http://192.168.1.203:9090", node: "VAULT", category: "monitoring" },
    { name: "ComfyUI", url: "http://192.168.1.225:8188", node: "Workshop", category: "creative" },
    { name: "Open WebUI", url: "http://192.168.1.225:3000", node: "Workshop", category: "ai" },
    { name: "Plex", url: "http://192.168.1.203:32400/web", node: "VAULT", category: "media" },
    { name: "Sonarr", url: "http://192.168.1.203:8989", node: "VAULT", category: "media" },
    { name: "Radarr", url: "http://192.168.1.203:7878", node: "VAULT", category: "media" },
    { name: "Tautulli", url: "http://192.168.1.203:8181", node: "VAULT", category: "media" },
    { name: "Prowlarr", url: "http://192.168.1.203:9696", node: "VAULT", category: "media" },
    { name: "SABnzbd", url: "http://192.168.1.203:8080", node: "VAULT", category: "media" },
    { name: "EoBQ", url: "http://192.168.1.225:3002", node: "Workshop", category: "creative" },
    { name: "Stash", url: "http://192.168.1.203:9999", node: "VAULT", category: "adult" },
    { name: "Home Assistant", url: "http://192.168.1.203:8123", node: "VAULT", category: "home" },
  ],
} as const;
