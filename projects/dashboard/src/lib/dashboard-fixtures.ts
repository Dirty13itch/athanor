import type {
  AgentsSnapshot,
  GpuHistoryResponse,
  GpuSnapshotResponse,
  ModelsSnapshot,
  OverviewSnapshot,
  ServicesHistorySnapshot,
  ServicesSnapshot,
} from "@/lib/contracts";

const FIXTURE_BASE_TIME = "2026-03-09T15:00:00.000Z";

function cloneFixture<T>(value: T): T {
  return structuredClone(value);
}

function isoMinutesBefore(base: string, minutesBefore: number) {
  return new Date(new Date(base).getTime() - minutesBefore * 60_000).toISOString();
}

const fixtureNodes: OverviewSnapshot["nodes"] = [
  {
    id: "node1",
    name: "Foundry",
    ip: "192.168.1.244",
    role: "AI inference + agents",
    totalServices: 5,
    healthyServices: 4,
    degradedServices: 1,
    averageLatencyMs: 248,
    gpuUtilization: 74,
  },
  {
    id: "node2",
    name: "Workshop",
    ip: "192.168.1.225",
    role: "Creative + interface",
    totalServices: 3,
    healthyServices: 3,
    degradedServices: 0,
    averageLatencyMs: 189,
    gpuUtilization: 57,
  },
  {
    id: "vault",
    name: "VAULT",
    ip: "192.168.1.203",
    role: "Storage + media + monitoring",
    totalServices: 5,
    healthyServices: 5,
    degradedServices: 0,
    averageLatencyMs: 132,
    gpuUtilization: null,
  },
];

const fixtureServices: ServicesSnapshot["services"] = [
  {
    id: "litellm-proxy",
    name: "LiteLLM Proxy",
    nodeId: "vault",
    node: "VAULT",
    category: "inference",
    description: "Unified model routing and auth edge.",
    url: "http://192.168.1.203:4000/health/readiness",
    healthy: true,
    latencyMs: 82,
    checkedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 2),
    state: "healthy",
  },
  {
    id: "node1-vllm",
    name: "vLLM (Node 1)",
    nodeId: "node1",
    node: "Foundry",
    category: "inference",
    description: "Primary large-model runtime.",
    url: "http://192.168.1.244:8000/v1/models",
    healthy: true,
    latencyMs: 364,
    checkedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 2),
    state: "healthy",
  },
  {
    id: "node2-vllm",
    name: "vLLM (Node 2)",
    nodeId: "node2",
    node: "Workshop",
    category: "inference",
    description: "Secondary interactive runtime.",
    url: "http://192.168.1.225:8000/v1/models",
    healthy: true,
    latencyMs: 218,
    checkedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 2),
    state: "healthy",
  },
  {
    id: "agent-server",
    name: "Agent Server",
    nodeId: "node1",
    node: "Foundry",
    category: "platform",
    description: "FastAPI runtime for Athanor agents.",
    url: "http://192.168.1.244:9000/health",
    healthy: true,
    latencyMs: 141,
    checkedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 2),
    state: "healthy",
  },
  {
    id: "prometheus",
    name: "Prometheus",
    nodeId: "vault",
    node: "VAULT",
    category: "observability",
    description: "Metrics scrape and query surface.",
    url: "http://192.168.1.203:9090/-/healthy",
    healthy: true,
    latencyMs: 109,
    checkedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 2),
    state: "healthy",
  },
  {
    id: "grafana",
    name: "Grafana",
    nodeId: "vault",
    node: "VAULT",
    category: "observability",
    description: "Dashboards and alert drill-down.",
    url: "http://192.168.1.203:3000/api/health",
    healthy: true,
    latencyMs: 154,
    checkedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 2),
    state: "healthy",
  },
  {
    id: "open-webui",
    name: "Open WebUI",
    nodeId: "node2",
    node: "Workshop",
    category: "experience",
    description: "Experimental multi-model chat surface.",
    url: "http://192.168.1.225:3000",
    healthy: true,
    latencyMs: 207,
    checkedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 2),
    state: "healthy",
  },
  {
    id: "comfyui",
    name: "ComfyUI",
    nodeId: "node2",
    node: "Workshop",
    category: "experience",
    description: "Creative workflow engine.",
    url: "http://192.168.1.225:8188/system_stats",
    healthy: true,
    latencyMs: 146,
    checkedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 2),
    state: "healthy",
  },
  {
    id: "speaches",
    name: "Speaches",
    nodeId: "node1",
    node: "Foundry",
    category: "platform",
    description: "Speech synthesis runtime.",
    url: "http://192.168.1.244:8200/health",
    healthy: false,
    latencyMs: null,
    checkedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 2),
    state: "degraded",
  },
  {
    id: "plex",
    name: "Plex",
    nodeId: "vault",
    node: "VAULT",
    category: "media",
    description: "Primary media serving platform.",
    url: "http://192.168.1.203:32400/identity",
    healthy: true,
    latencyMs: 192,
    checkedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 2),
    state: "healthy",
  },
  {
    id: "sonarr",
    name: "Sonarr",
    nodeId: "vault",
    node: "VAULT",
    category: "media",
    description: "TV acquisition automation.",
    url: "http://192.168.1.203:8989/ping",
    healthy: true,
    latencyMs: 101,
    checkedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 2),
    state: "healthy",
  },
  {
    id: "radarr",
    name: "Radarr",
    nodeId: "vault",
    node: "VAULT",
    category: "media",
    description: "Movie acquisition automation.",
    url: "http://192.168.1.203:7878/ping",
    healthy: true,
    latencyMs: 98,
    checkedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 2),
    state: "healthy",
  },
  {
    id: "stash",
    name: "Stash",
    nodeId: "vault",
    node: "VAULT",
    category: "media",
    description: "Media catalog and search runtime.",
    url: "http://192.168.1.203:9999",
    healthy: true,
    latencyMs: 173,
    checkedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 2),
    state: "healthy",
  },
];

const fixtureServiceAggregate: ServicesHistorySnapshot["aggregate"] = [
  { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 180), value: 91 },
  { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 150), value: 93 },
  { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 120), value: 95 },
  { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 90), value: 95 },
  { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 60), value: 97 },
  { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 30), value: 98 },
  { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 0), value: 92 },
];

const fixtureServiceSeries: ServicesHistorySnapshot["series"] = fixtureServices.map((service) => ({
  serviceId: service.id,
  serviceName: service.name,
  nodeId: service.nodeId,
  category: service.category,
  points: fixtureServiceAggregate.map((point, index) => ({
    timestamp: point.timestamp,
    availability:
      service.id === "speaches" && index >= fixtureServiceAggregate.length - 2
        ? 0
        : 1,
    latencyMs:
      service.latencyMs === null
        ? null
        : service.latencyMs + (index % 2 === 0 ? 12 : -8),
  })),
}));

const fixtureGpuSnapshot: GpuSnapshotResponse = {
  generatedAt: FIXTURE_BASE_TIME,
  summary: {
    gpuCount: 4,
    averageUtilization: 66.5,
    averageTemperature: 68.75,
    totalPowerW: 895,
    totalMemoryUsedMiB: 78464,
    totalMemoryMiB: 143360,
  },
  nodes: [
    {
      nodeId: "node1",
      node: "Foundry",
      gpuCount: 2,
      averageUtilization: 78,
      averageTemperature: 72.5,
      totalPowerW: 510,
      totalMemoryUsedMiB: 57344,
      totalMemoryMiB: 98304,
    },
    {
      nodeId: "node2",
      node: "Workshop",
      gpuCount: 2,
      averageUtilization: 55,
      averageTemperature: 65,
      totalPowerW: 385,
      totalMemoryUsedMiB: 21120,
      totalMemoryMiB: 45056,
    },
    {
      nodeId: "vault",
      node: "VAULT",
      gpuCount: 0,
      averageUtilization: null,
      averageTemperature: null,
      totalPowerW: null,
      totalMemoryUsedMiB: null,
      totalMemoryMiB: null,
    },
  ],
  gpus: [
    {
      id: "node1::00000000:01:00.0",
      gpuName: "RTX 4090",
      gpuBusId: "00000000:01:00.0",
      instance: "192.168.1.244:9400",
      nodeId: "node1",
      node: "Foundry",
      utilization: 92,
      memoryUsedMiB: 28672,
      memoryTotalMiB: 49152,
      temperatureC: 76,
      powerW: 288,
    },
    {
      id: "node1::00000000:02:00.0",
      gpuName: "RTX 4090",
      gpuBusId: "00000000:02:00.0",
      instance: "192.168.1.244:9400",
      nodeId: "node1",
      node: "Foundry",
      utilization: 64,
      memoryUsedMiB: 28672,
      memoryTotalMiB: 49152,
      temperatureC: 69,
      powerW: 222,
    },
    {
      id: "node2::00000000:01:00.0",
      gpuName: "RTX 3090",
      gpuBusId: "00000000:01:00.0",
      instance: "192.168.1.225:9400",
      nodeId: "node2",
      node: "Workshop",
      utilization: 58,
      memoryUsedMiB: 12288,
      memoryTotalMiB: 24576,
      temperatureC: 67,
      powerW: 198,
    },
    {
      id: "node2::00000000:02:00.0",
      gpuName: "RTX 3090",
      gpuBusId: "00000000:02:00.0",
      instance: "192.168.1.225:9400",
      nodeId: "node2",
      node: "Workshop",
      utilization: 52,
      memoryUsedMiB: 8832,
      memoryTotalMiB: 20480,
      temperatureC: 63,
      powerW: 187,
    },
  ],
};

const fixtureGpuHistory: GpuHistoryResponse = {
  generatedAt: FIXTURE_BASE_TIME,
  window: "3h",
  nodes: [
    {
      id: "node1",
      label: "Foundry",
      points: [
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 180), value: 68 },
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 150), value: 71 },
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 120), value: 74 },
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 90), value: 76 },
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 60), value: 79 },
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 30), value: 81 },
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 0), value: 78 },
      ],
    },
    {
      id: "node2",
      label: "Workshop",
      points: [
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 180), value: 42 },
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 150), value: 46 },
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 120), value: 53 },
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 90), value: 56 },
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 60), value: 57 },
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 30), value: 59 },
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 0), value: 55 },
      ],
    },
  ],
  gpus: fixtureGpuSnapshot.gpus.map((gpu, gpuIndex) => ({
    id: gpu.id,
    label: gpu.gpuName,
    nodeId: gpu.nodeId,
    points: [
      180, 150, 120, 90, 60, 30, 0,
    ].map((minutesBefore, index) => ({
      timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, minutesBefore),
      utilization:
        (gpu.utilization ?? 0) -
        (gpuIndex % 2 === 0 ? 10 : 6) +
        index * (gpuIndex % 2 === 0 ? 2 : 1),
      temperatureC:
        (gpu.temperatureC ?? 0) - 4 + index,
      powerW:
        gpu.powerW === null ? null : gpu.powerW - 18 + index * 3,
      memoryRatio:
        gpu.memoryTotalMiB
          ? ((gpu.memoryUsedMiB ?? 0) / gpu.memoryTotalMiB) * 100
          : null,
    })),
  })),
};

const fixtureBackends: ModelsSnapshot["backends"] = [
  {
    id: "litellm-proxy",
    name: "LiteLLM Proxy",
    description: "Unified routing layer for direct inference and embeddings.",
    nodeId: "vault",
    url: "http://192.168.1.203:4000",
    reachable: true,
    modelCount: 3,
    models: ["/models/qwen3-32b", "/models/qwen3-14b", "/models/nomic-embed"],
  },
  {
    id: "node1-vllm",
    name: "Foundry / Qwen3-32B",
    description: "Primary large-model runtime.",
    nodeId: "node1",
    url: "http://192.168.1.244:8000",
    reachable: true,
    modelCount: 2,
    models: ["/models/qwen3-32b", "/models/deepseek-r1-distill"],
  },
  {
    id: "node2-vllm",
    name: "Workshop / Qwen3-14B",
    description: "Secondary runtime for interactive workloads.",
    nodeId: "node2",
    url: "http://192.168.1.225:8000",
    reachable: true,
    modelCount: 2,
    models: ["/models/qwen3-14b", "/models/phi-4-mini"],
  },
];

const fixtureModels: ModelsSnapshot = {
  generatedAt: FIXTURE_BASE_TIME,
  backends: fixtureBackends,
  models: [
    {
      id: "/models/qwen3-32b",
      backendId: "litellm-proxy",
      backend: "LiteLLM Proxy",
      target: "litellm-proxy",
      description: "High-capacity reasoning model.",
      available: true,
    },
    {
      id: "/models/qwen3-14b",
      backendId: "litellm-proxy",
      backend: "LiteLLM Proxy",
      target: "litellm-proxy",
      description: "Fast general assistant model.",
      available: true,
    },
    {
      id: "/models/nomic-embed",
      backendId: "litellm-proxy",
      backend: "LiteLLM Proxy",
      target: "litellm-proxy",
      description: "Embedding model for semantic search.",
      available: true,
    },
    {
      id: "/models/deepseek-r1-distill",
      backendId: "node1-vllm",
      backend: "Foundry / Qwen3-32B",
      target: "node1-vllm",
      description: "Local reasoning runtime.",
      available: true,
    },
    {
      id: "/models/phi-4-mini",
      backendId: "node2-vllm",
      backend: "Workshop / Qwen3-14B",
      target: "node2-vllm",
      description: "Smaller interactive model.",
      available: true,
    },
  ],
};

const fixtureAgents: AgentsSnapshot = {
  generatedAt: FIXTURE_BASE_TIME,
  agents: [
    {
      id: "general-assistant",
      name: "General Assistant",
      description: "Cross-stack research, operations, and writing support.",
      icon: "terminal",
      tools: ["cluster_health", "gpu_snapshot", "model_inventory"],
      status: "ready",
    },
    {
      id: "media-agent",
      name: "Media Agent",
      description: "Plex, stash, and media library support.",
      icon: "film",
      tools: ["plex_status", "stash_search", "recent_history"],
      status: "ready",
    },
    {
      id: "home-agent",
      name: "Home Agent",
      description: "Home automation surface held in standby.",
      icon: "home",
      tools: ["lights", "scenes", "presence"],
      status: "unavailable",
    },
  ],
};

const fixtureOverview: OverviewSnapshot = {
  generatedAt: FIXTURE_BASE_TIME,
  summary: {
    totalServices: fixtureServices.length,
    healthyServices: fixtureServices.filter((service) => service.healthy).length,
    degradedServices: fixtureServices.filter((service) => !service.healthy).length,
    averageLatencyMs: 165,
    averageGpuUtilization: fixtureGpuSnapshot.summary.averageUtilization,
    readyAgents: fixtureAgents.agents.filter((agent) => agent.status === "ready").length,
    totalAgents: fixtureAgents.agents.length,
    reachableBackends: fixtureBackends.filter((backend) => backend.reachable).length,
    totalBackends: fixtureBackends.length,
  },
  nodes: fixtureNodes,
  services: fixtureServices,
  serviceTrend: fixtureServiceAggregate,
  gpuTrend: fixtureGpuHistory.nodes[0].points.map((point, index) => ({
    timestamp: point.timestamp,
    value: Math.round(
      (((fixtureGpuHistory.nodes[0].points[index]?.value ?? 0) +
        (fixtureGpuHistory.nodes[1].points[index]?.value ?? 0)) /
        2) *
        10
    ) / 10,
  })),
  backends: fixtureBackends,
  agents: fixtureAgents.agents,
  alerts: [
    {
      id: "speaches-outage",
      title: "Speaches is degraded",
      description: "Speech synthesis is unreachable from the latest dashboard probe.",
      tone: "degraded",
      href: "/services?service=speaches",
    },
    {
      id: "gpu-hotspot",
      title: "RTX 4090 hotspot on Foundry",
      description: "One card is sitting above 90% utilization and 76C.",
      tone: "warning",
      href: "/gpu?highlight=node1%3A%3A00000000%3A01%3A00.0",
    },
  ],
  hotspots: fixtureGpuSnapshot.gpus.slice(0, 4),
  externalTools: [
    {
      id: "grafana",
      label: "Grafana",
      description: "Dashboards, alerts, and metrics drill-downs.",
      url: "http://192.168.1.203:3000",
    },
    {
      id: "prometheus",
      label: "Prometheus",
      description: "Raw PromQL and scrape-state inspection.",
      url: "http://192.168.1.203:9090",
    },
    {
      id: "comfyui",
      label: "ComfyUI",
      description: "Creative workflows and queue triage.",
      url: "http://192.168.1.225:8188",
    },
    {
      id: "plex",
      label: "Plex",
      description: "Media library and playback control.",
      url: "http://192.168.1.203:32400/web",
    },
  ],
};

const fixtureServicesSnapshot: ServicesSnapshot = {
  generatedAt: FIXTURE_BASE_TIME,
  summary: {
    total: fixtureServices.length,
    healthy: fixtureServices.filter((service) => service.healthy).length,
    degraded: fixtureServices.filter((service) => !service.healthy).length,
    averageLatencyMs: 165,
    slowestServiceId: "node1-vllm",
    slowestServiceName: "vLLM (Node 1)",
  },
  nodes: fixtureNodes,
  services: fixtureServices,
};

const fixtureServicesHistory: ServicesHistorySnapshot = {
  generatedAt: FIXTURE_BASE_TIME,
  window: "3h",
  aggregate: fixtureServiceAggregate,
  series: fixtureServiceSeries,
};

export function isDashboardFixtureMode() {
  return process.env.DASHBOARD_FIXTURE_MODE === "1";
}

export function getFixtureOverviewSnapshot(): OverviewSnapshot {
  return cloneFixture(fixtureOverview);
}

export function getFixtureServicesSnapshot(): ServicesSnapshot {
  return cloneFixture(fixtureServicesSnapshot);
}

export function getFixtureServicesHistory(window: string): ServicesHistorySnapshot {
  const next = cloneFixture(fixtureServicesHistory);
  next.window = window;
  return next;
}

export function getFixtureGpuSnapshot(): GpuSnapshotResponse {
  return cloneFixture(fixtureGpuSnapshot);
}

export function getFixtureGpuHistory(window: string): GpuHistoryResponse {
  const next = cloneFixture(fixtureGpuHistory);
  next.window = window;
  return next;
}

export function getFixtureModelsSnapshot(): ModelsSnapshot {
  return cloneFixture(fixtureModels);
}

export function getFixtureAgentsSnapshot(): AgentsSnapshot {
  return cloneFixture(fixtureAgents);
}
