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
  homeAssistant: {
    url: "http://192.168.1.203:8123",
  },
  inferenceBackends: [
    {
      name: "Node 1 — Qwen3-32B",
      url: "http://192.168.1.244:8000",
    },
    {
      name: "Node 2 — Qwen3-14B",
      url: "http://192.168.1.225:8000",
    },
    {
      name: "Agents",
      url: "http://192.168.1.244:9000",
    },
  ],
  services: [
    { name: "vLLM (Node 1)", url: "http://192.168.1.244:8000/v1/models", node: "Foundry" },
    { name: "vLLM (Node 2)", url: "http://192.168.1.225:8000/v1/models", node: "Workshop" },
    { name: "Agent Server", url: "http://192.168.1.244:9000/health", node: "Foundry" },
    { name: "Prometheus", url: "http://192.168.1.203:9090/-/healthy", node: "VAULT" },
    { name: "Grafana", url: "http://192.168.1.203:3000/api/health", node: "VAULT" },
    { name: "Node Exporter (Node 1)", url: "http://192.168.1.244:9100/metrics", node: "Foundry" },
    { name: "Node Exporter (Node 2)", url: "http://192.168.1.225:9100/metrics", node: "Workshop" },
    { name: "DCGM Exporter (Node 1)", url: "http://192.168.1.244:9400/metrics", node: "Foundry" },
    { name: "DCGM Exporter (Node 2)", url: "http://192.168.1.225:9400/metrics", node: "Workshop" },
    { name: "ComfyUI", url: "http://192.168.1.225:8188/system_stats", node: "Workshop" },
    { name: "Open WebUI", url: "http://192.168.1.225:3000", node: "Workshop" },
    { name: "Sonarr", url: "http://192.168.1.203:8989/ping", node: "VAULT" },
    { name: "Radarr", url: "http://192.168.1.203:7878/ping", node: "VAULT" },
    { name: "Tautulli", url: "http://192.168.1.203:8181", node: "VAULT" },
    { name: "Plex", url: "http://192.168.1.203:32400/identity", node: "VAULT" },
    { name: "SABnzbd", url: "http://192.168.1.203:8080", node: "VAULT" },
    { name: "Prowlarr", url: "http://192.168.1.203:9696/ping", node: "VAULT" },
    { name: "Stash", url: "http://192.168.1.203:9999", node: "VAULT" },
    { name: "Home Assistant", url: "http://192.168.1.203:8123/api/", node: "VAULT" },
  ],
  nodes: [
    { name: "Foundry", ip: "192.168.1.244", role: "AI inference + agents", gpuCount: 5, vram: 88, psuWatts: 1600 },
    { name: "Workshop", ip: "192.168.1.225", role: "Creative + interface", gpuCount: 2, vram: 48, psuWatts: 1600 },
    { name: "VAULT", ip: "192.168.1.203", role: "Storage + media + monitoring", gpuCount: 0, vram: 0, psuWatts: 0 },
  ],
  // Known GPU → workload mapping (static, will be made dynamic later)
  gpuWorkloads: {
    "192.168.1.244": {
      0: "vLLM TP0 (Qwen3-32B)",
      1: "vLLM TP1",
      2: "vLLM TP2",
      3: "vLLM TP3",
      4: "RTX 4090 — Idle",
    },
    "192.168.1.225": {
      0: "ComfyUI (Flux)",
      1: "vLLM (Qwen3-14B)",
    },
  } as Record<string, Record<number, string>>,
  // Power limits per GPU (watts) — matches Ansible config
  gpuPowerLimits: {
    "192.168.1.244": { 0: 320, 1: 240, 2: 240, 3: 240, 4: 240 },
    "192.168.1.225": { 0: 575, 1: 200 },
  } as Record<string, Record<number, number>>,
  quickLinks: [
    { name: "Grafana", url: "http://192.168.1.203:3000", node: "VAULT", category: "monitoring" },
    { name: "Prometheus", url: "http://192.168.1.203:9090", node: "VAULT", category: "monitoring" },
    { name: "ComfyUI", url: "http://192.168.1.225:8188", node: "Workshop", category: "creative" },
    { name: "Open WebUI", url: "http://192.168.1.225:3000", node: "Workshop", category: "ai" },
    { name: "Plex", url: "http://192.168.1.203:32400/web", node: "VAULT", category: "media" },
    { name: "Sonarr", url: "http://192.168.1.203:8989", node: "VAULT", category: "media" },
    { name: "Radarr", url: "http://192.168.1.203:7878", node: "VAULT", category: "media" },
    { name: "Tautulli", url: "http://192.168.1.203:8181", node: "VAULT", category: "media" },
    { name: "Prowlarr", url: "http://192.168.1.203:9696", node: "VAULT", category: "media" },
    { name: "SABnzbd", url: "http://192.168.1.203:8080", node: "VAULT", category: "media" },
    { name: "Stash", url: "http://192.168.1.203:9999", node: "VAULT", category: "adult" },
    { name: "Home Assistant", url: "http://192.168.1.203:8123", node: "VAULT", category: "home" },
  ],
} as const;
