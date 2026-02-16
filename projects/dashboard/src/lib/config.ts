export const config = {
  prometheus: {
    url: process.env.NEXT_PUBLIC_PROMETHEUS_URL ?? "http://192.168.1.203:9090",
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
    { name: "vLLM (Node 1)", url: "http://192.168.1.244:8000/v1/models", node: "Node 1" },
    { name: "vLLM (Node 2)", url: "http://192.168.1.225:8000/v1/models", node: "Node 2" },
    { name: "Agent Server", url: "http://192.168.1.244:9000/health", node: "Node 1" },
    { name: "Prometheus", url: "http://192.168.1.203:9090/-/healthy", node: "VAULT" },
    { name: "Grafana", url: "http://192.168.1.203:3000/api/health", node: "VAULT" },
    { name: "Node Exporter (Node 1)", url: "http://192.168.1.244:9100/metrics", node: "Node 1" },
    { name: "Node Exporter (Node 2)", url: "http://192.168.1.225:9100/metrics", node: "Node 2" },
    { name: "DCGM Exporter (Node 1)", url: "http://192.168.1.244:9400/metrics", node: "Node 1" },
    { name: "DCGM Exporter (Node 2)", url: "http://192.168.1.225:9400/metrics", node: "Node 2" },
    { name: "ComfyUI", url: "http://192.168.1.225:8188/system_stats", node: "Node 2" },
    { name: "Open WebUI", url: "http://192.168.1.225:3000", node: "Node 2" },
    { name: "Sonarr", url: "http://192.168.1.203:8989/ping", node: "VAULT" },
    { name: "Radarr", url: "http://192.168.1.203:7878/ping", node: "VAULT" },
    { name: "Tautulli", url: "http://192.168.1.203:8181", node: "VAULT" },
    { name: "Plex", url: "http://192.168.1.203:32400/identity", node: "VAULT" },
  ],
  nodes: [
    { name: "Node 1 (core)", ip: "192.168.1.244", role: "GPU inference" },
    { name: "Node 2 (interface)", ip: "192.168.1.225", role: "GPU inference + creative" },
    { name: "VAULT", ip: "192.168.1.203", role: "Storage & monitoring" },
  ],
} as const;
