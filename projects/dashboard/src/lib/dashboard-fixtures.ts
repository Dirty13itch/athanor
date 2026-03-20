import type {
  AgentsSnapshot,
  GallerySnapshot,
  GpuHistoryResponse,
  GpuSnapshotResponse,
  HistorySnapshot,
  HomeSnapshot,
  IntelligenceSnapshot,
  MediaSnapshot,
  MemorySnapshot,
  ModelsSnapshot,
  MonitoringSnapshot,
  OverviewSnapshot,
  ServicesHistorySnapshot,
  ServicesSnapshot,
  WorkforceSnapshot,
} from "@/lib/contracts";
import { config, joinUrl } from "@/lib/config";
import { buildNavAttentionSignals } from "@/lib/nav-attention";

/** Derive the DCGM exporter `host:port` instance string for a given node ID. */
function dcgmInstance(nodeId: string): string {
  const node = config.nodes.find((n) => n.id === nodeId);
  return node ? `${node.ip}:9400` : `${nodeId}:9400`;
}

/** Look up a node IP by node ID from config. */
function nodeIp(nodeId: string): string {
  return config.nodes.find((n) => n.id === nodeId)?.ip ?? "";
}

export const FIXTURE_BASE_TIME = "2026-03-09T15:00:00.000Z";
const ACTIVE_PROJECT_STATUSES = new Set(["active", "operational", "planning", "active_development"]);

function cloneFixture<T>(value: T): T {
  return structuredClone(value);
}

function isoMinutesBefore(base: string, minutesBefore: number) {
  return new Date(new Date(base).getTime() - minutesBefore * 60_000).toISOString();
}

function isoMinutesAfter(base: string, minutesAfter: number) {
  return new Date(new Date(base).getTime() + minutesAfter * 60_000).toISOString();
}

const fixtureNodeMetrics: Record<
  string,
  Pick<
    OverviewSnapshot["nodes"][number],
    "totalServices" | "healthyServices" | "degradedServices" | "averageLatencyMs" | "gpuUtilization"
  >
> = {
  node1: {
    totalServices: 7,
    healthyServices: 6,
    degradedServices: 1,
    averageLatencyMs: 211,
    gpuUtilization: 74,
  },
  node2: {
    totalServices: 6,
    healthyServices: 6,
    degradedServices: 0,
    averageLatencyMs: 176,
    gpuUtilization: 57,
  },
  vault: {
    totalServices: 14,
    healthyServices: 13,
    degradedServices: 1,
    averageLatencyMs: 129,
    gpuUtilization: null,
  },
  dev: {
    totalServices: 2,
    healthyServices: 2,
    degradedServices: 0,
    averageLatencyMs: 141,
    gpuUtilization: 34,
  },
};

const fixtureNodes: OverviewSnapshot["nodes"] = config.nodes.map((node) => ({
  ...node,
  ...fixtureNodeMetrics[node.id],
}));

const fixtureServiceHealth: Record<
  string,
  Pick<ServicesSnapshot["services"][number], "healthy" | "latencyMs" | "state">
> = {
  "litellm-proxy": { healthy: true, latencyMs: 82, state: "healthy" },
  "foundry-coordinator": { healthy: true, latencyMs: 364, state: "healthy" },
  "foundry-coder": { healthy: true, latencyMs: 642, state: "healthy" },
  "workshop-worker": { healthy: true, latencyMs: 218, state: "healthy" },
  "dev-embedding": { healthy: true, latencyMs: 134, state: "healthy" },
  "dev-reranker": { healthy: true, latencyMs: 147, state: "healthy" },
  "agent-server": { healthy: true, latencyMs: 141, state: "healthy" },
  qdrant: { healthy: true, latencyMs: 96, state: "healthy" },
  neo4j: { healthy: true, latencyMs: 133, state: "healthy" },
  prometheus: { healthy: true, latencyMs: 109, state: "healthy" },
  grafana: { healthy: true, latencyMs: 154, state: "healthy" },
  "foundry-node-exporter": { healthy: true, latencyMs: 74, state: "healthy" },
  "workshop-node-exporter": { healthy: true, latencyMs: 69, state: "healthy" },
  "vault-node-exporter": { healthy: true, latencyMs: 62, state: "healthy" },
  "foundry-dcgm-exporter": { healthy: true, latencyMs: 81, state: "healthy" },
  "workshop-dcgm-exporter": { healthy: true, latencyMs: 77, state: "healthy" },
  comfyui: { healthy: true, latencyMs: 146, state: "healthy" },
  "workshop-open-webui": { healthy: true, latencyMs: 207, state: "healthy" },
  "vault-open-webui": { healthy: true, latencyMs: 191, state: "healthy" },
  eoq: { healthy: true, latencyMs: 124, state: "healthy" },
  "home-assistant": { healthy: false, latencyMs: null, state: "degraded" },
  speaches: { healthy: false, latencyMs: null, state: "degraded" },
  plex: { healthy: true, latencyMs: 192, state: "healthy" },
  sonarr: { healthy: true, latencyMs: 101, state: "healthy" },
  radarr: { healthy: true, latencyMs: 98, state: "healthy" },
  tautulli: { healthy: true, latencyMs: 88, state: "healthy" },
  prowlarr: { healthy: true, latencyMs: 93, state: "healthy" },
  sabnzbd: { healthy: true, latencyMs: 126, state: "healthy" },
  stash: { healthy: true, latencyMs: 173, state: "healthy" },
};

const fixtureServices: ServicesSnapshot["services"] = config.services.map((service) => ({
  ...service,
  ...(fixtureServiceHealth[service.id] ?? { healthy: true, latencyMs: 150, state: "healthy" }),
  checkedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 2),
}));

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
      ["speaches", "home-assistant"].includes(service.id) && index >= fixtureServiceAggregate.length - 2
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
    gpuCount: 5,
    averageUtilization: 60,
    averageTemperature: 65.8,
    totalPowerW: 987,
    totalMemoryUsedMiB: 84608,
    totalMemoryMiB: 167936,
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
    {
      nodeId: "dev",
      node: "DEV",
      gpuCount: 1,
      averageUtilization: 34,
      averageTemperature: 54,
      totalPowerW: 92,
      totalMemoryUsedMiB: 6144,
      totalMemoryMiB: 24576,
    },
  ],
  gpus: [
    {
      id: "node1::00000000:01:00.0",
      gpuName: "RTX 4090",
      gpuBusId: "00000000:01:00.0",
      instance: dcgmInstance("node1"),
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
      instance: dcgmInstance("node1"),
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
      instance: dcgmInstance("node2"),
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
      instance: dcgmInstance("node2"),
      nodeId: "node2",
      node: "Workshop",
      utilization: 52,
      memoryUsedMiB: 8832,
      memoryTotalMiB: 20480,
      temperatureC: 63,
      powerW: 187,
    },
    {
      id: "dev::00000000:01:00.0",
      gpuName: "RTX 4090",
      gpuBusId: "00000000:01:00.0",
      instance: dcgmInstance("dev"),
      nodeId: "dev",
      node: "DEV",
      utilization: 34,
      memoryUsedMiB: 6144,
      memoryTotalMiB: 24576,
      temperatureC: 54,
      powerW: 92,
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
    {
      id: "dev",
      label: "DEV",
      points: [
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 180), value: 26 },
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 150), value: 28 },
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 120), value: 30 },
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 90), value: 31 },
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 60), value: 33 },
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 30), value: 36 },
        { timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 0), value: 34 },
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

const fixtureBackendModels: Record<string, string[]> = {
  "litellm-proxy": [
    "reasoning",
    "coding",
    "creative",
    "utility",
    "fast",
    "worker",
    "uncensored",
    "coder",
    "embedding",
    "reranker",
  ],
  "foundry-coordinator": ["qwen3-32b", "deepseek-r1-distill-qwen-32b"],
  "foundry-coder": ["qwen3-coder"],
  "workshop-worker": ["qwen3-35b-a3b-awq", "phi-4-mini"],
  "dev-embedding": ["qwen3-embedding-0.6b"],
  "dev-reranker": ["qwen3-reranker-0.6b"],
};

const fixtureModelDescriptions: Record<string, string> = {
  reasoning: "LiteLLM alias for primary reasoning work on the Foundry coordinator lane.",
  coding: "LiteLLM alias for code-heavy work on the Foundry coordinator lane.",
  creative: "LiteLLM alias for creative text work routed through the workshop worker lane.",
  utility: "LiteLLM alias for fast utility work routed through the workshop worker lane.",
  fast: "LiteLLM alias for fast interactive work routed through the workshop worker lane.",
  worker: "LiteLLM alias for delegated worker inference on Workshop.",
  uncensored: "Legacy uncensored alias retained on the workshop worker lane.",
  coder: "LiteLLM alias for the dedicated Foundry coding runtime.",
  embedding: "LiteLLM alias for DEV-hosted embeddings.",
  reranker: "LiteLLM alias for DEV-hosted reranking.",
  "qwen3-32b": "Primary large-model runtime on Foundry.",
  "deepseek-r1-distill-qwen-32b": "Reasoning-heavy local coordinator model.",
  "qwen3-coder": "Dedicated coding runtime on Foundry GPU 2.",
  "qwen3-35b-a3b-awq": "Interactive worker runtime on Workshop.",
  "phi-4-mini": "Smaller interactive model for lightweight tasks.",
  "qwen3-embedding-0.6b": "Canonical embedding runtime on DEV.",
  "qwen3-reranker-0.6b": "Canonical reranker runtime on DEV.",
};

const fixtureBackends: ModelsSnapshot["backends"] = config.inferenceBackends.map((backend) => {
  const models = fixtureBackendModels[backend.id] ?? [backend.primaryModel];
  return {
    id: backend.id,
    name: backend.name,
    description: backend.description,
    nodeId: backend.nodeId,
    url: backend.url,
    reachable: true,
    modelCount: models.length,
    models,
  };
});

const fixtureModels: ModelsSnapshot = {
  generatedAt: FIXTURE_BASE_TIME,
  backends: fixtureBackends,
  models: fixtureBackends.flatMap((backend) =>
    backend.models.map((modelId) => ({
      id: modelId,
      backendId: backend.id,
      backend: backend.name,
      target: backend.id,
      description: fixtureModelDescriptions[modelId] ?? backend.description,
      available: backend.reachable,
    }))
  ),
};

const fixtureProjectCatalog: Record<
  string,
  {
    description: string;
    agents: string[];
    needsCount: number;
    constraints: string[];
    mappedAgents: number;
    totalTasks: number;
    pendingTasks: number;
    pendingApprovals: number;
    runningTasks: number;
    completedTasks: number;
    failedTasks: number;
    plannedTasks: number;
    topAgents: string[];
  }
> = {
  athanor: {
    description:
      "The core operating environment: dashboard, agents, monitoring, memory, deployment, and the one-person-maintainable operating model.",
    agents: ["general-assistant", "coding-agent", "knowledge-agent", "research-agent"],
    needsCount: 3,
    constraints: [
      "Favor one-person maintainability over architectural novelty.",
      "Infrastructure work is an enabler, not the product.",
      "Preserve centralized runtime contracts and keep drift tests current.",
    ],
    mappedAgents: 4,
    totalTasks: 4,
    pendingTasks: 1,
    pendingApprovals: 1,
    runningTasks: 1,
    completedTasks: 1,
    failedTasks: 0,
    plannedTasks: 2,
    topAgents: ["research-agent", "knowledge-agent", "general-assistant"],
  },
  eoq: {
    description:
      "AI-driven interactive dark-fantasy tenant where dialogue, memory, scene flow, and visual generation belong to one platform lane.",
    agents: ["creative-agent", "coding-agent", "research-agent", "knowledge-agent"],
    needsCount: 3,
    constraints: [
      "Adult content is intentional and remains part of the creative pipeline.",
      "Keep the tenant integrated into Athanor rather than splitting it into a side app.",
      "All project prompts, outputs, and interface copy stay in English.",
    ],
    mappedAgents: 4,
    totalTasks: 2,
    pendingTasks: 1,
    pendingApprovals: 1,
    runningTasks: 0,
    completedTasks: 0,
    failedTasks: 0,
    plannedTasks: 2,
    topAgents: ["coding-agent", "creative-agent", "research-agent"],
  },
  kindred: {
    description: "Scaffolded future tenant focused on intent, drive, and passion-forward social matching.",
    agents: ["research-agent"],
    needsCount: 1,
    constraints: [
      "Keep work at concept depth until Shaun explicitly promotes it to an active build lane.",
      "Avoid premature UI or backend scaffolds.",
    ],
    mappedAgents: 1,
    totalTasks: 1,
    pendingTasks: 0,
    pendingApprovals: 0,
    runningTasks: 0,
    completedTasks: 1,
    failedTasks: 0,
    plannedTasks: 0,
    topAgents: ["research-agent"],
  },
  "ulrich-energy": {
    description:
      "Scaffolded operational tenant for field workflows, reporting, inspections, and energy-audit operations.",
    agents: ["coding-agent", "research-agent", "knowledge-agent"],
    needsCount: 2,
    constraints: [
      "Treat this as a scaffolded tenant until Shaun promotes it into the active build lane.",
      "Prefer platform-aligned primitives over bespoke one-off architecture.",
    ],
    mappedAgents: 3,
    totalTasks: 0,
    pendingTasks: 0,
    pendingApprovals: 0,
    runningTasks: 0,
    completedTasks: 0,
    failedTasks: 0,
    plannedTasks: 1,
    topAgents: ["coding-agent", "research-agent"],
  },
  media: {
    description: "Operational domain project spanning curation, acquisition, queue health, and catalog quality.",
    agents: ["media-agent", "stash-agent"],
    needsCount: 2,
    constraints: [
      "Prefer quality and fit over indiscriminate library growth.",
      "Treat disk pressure and queue health as real operational constraints.",
    ],
    mappedAgents: 2,
    totalTasks: 1,
    pendingTasks: 0,
    pendingApprovals: 0,
    runningTasks: 0,
    completedTasks: 0,
    failedTasks: 1,
    plannedTasks: 1,
    topAgents: ["media-agent", "stash-agent"],
  },
};

const fixtureProjectSnapshots: OverviewSnapshot["projects"] = config.projectRegistry.map((project) => {
  const details = fixtureProjectCatalog[project.id];
  return {
    id: project.id,
    name: project.name,
    description: details.description,
    headline: project.headline,
    status: project.status,
    kind: project.kind,
    firstClass: project.firstClass,
    lens: project.lens,
    primaryRoute: project.primaryRoute,
    externalUrl: project.externalUrl,
    agents: details.agents,
    needsCount: details.needsCount,
    constraints: details.constraints,
    operatorChain: project.operators,
  };
});

const fixtureProjectPosture: WorkforceSnapshot["projects"] = config.projectRegistry.map((project) => {
  const details = fixtureProjectCatalog[project.id];
  return {
    id: project.id,
    name: project.name,
    status: project.status,
    firstClass: project.firstClass,
    lens: project.lens,
    primaryRoute: project.primaryRoute,
    externalUrl: project.externalUrl,
    needsCount: details.needsCount,
    mappedAgents: details.mappedAgents,
    totalTasks: details.totalTasks,
    pendingTasks: details.pendingTasks,
    pendingApprovals: details.pendingApprovals,
    runningTasks: details.runningTasks,
    completedTasks: details.completedTasks,
    failedTasks: details.failedTasks,
    plannedTasks: details.plannedTasks,
    operatorChain: project.operators,
    topAgents: details.topAgents,
  };
});

const fixtureWorkforceAgents: WorkforceSnapshot["agents"] = [
  {
    id: "general-assistant",
    name: "General Assistant",
    description: "Cross-stack research, operations, and writing support.",
    icon: "terminal",
    type: "proactive",
    status: "ready",
    tools: ["cluster_health", "gpu_snapshot", "model_inventory"],
    totalTasks: 1,
    runningTasks: 0,
    pendingTasks: 0,
    trustScore: 0.81,
    trustGrade: "A",
  },
  {
    id: "media-agent",
    name: "Media Agent",
    description: "Plex, stash, and media library support.",
    icon: "film",
    type: "proactive",
    status: "ready",
    tools: ["plex_status", "stash_search", "recent_history"],
    totalTasks: 1,
    runningTasks: 0,
    pendingTasks: 0,
    trustScore: 0.76,
    trustGrade: "B",
  },
  {
    id: "home-agent",
    name: "Home Agent",
    description: "Home automation surface held in standby until integration is complete.",
    icon: "home",
    type: "proactive",
    status: "unavailable",
    tools: ["lights", "scenes", "presence"],
    totalTasks: 1,
    runningTasks: 0,
    pendingTasks: 0,
    trustScore: 0.51,
    trustGrade: "C",
  },
  {
    id: "creative-agent",
    name: "Creative Agent",
    description: "Image and video generation across ComfyUI workflows.",
    icon: "sparkles",
    type: "reactive",
    status: "ready",
    tools: ["generate_image", "generate_video", "queue_status"],
    totalTasks: 1,
    runningTasks: 0,
    pendingTasks: 1,
    trustScore: 0.74,
    trustGrade: "B",
  },
  {
    id: "research-agent",
    name: "Research Agent",
    description: "Web research, synthesis, and retrieval-heavy discovery.",
    icon: "search",
    type: "reactive",
    status: "ready",
    tools: ["web_search", "fetch_page", "search_knowledge"],
    totalTasks: 2,
    runningTasks: 1,
    pendingTasks: 0,
    trustScore: 0.72,
    trustGrade: "B",
  },
  {
    id: "knowledge-agent",
    name: "Knowledge Agent",
    description: "Documentation, ADR, and knowledge-base curation.",
    icon: "book-open",
    type: "reactive",
    status: "ready",
    tools: ["search_knowledge", "list_documents", "graph_queries"],
    totalTasks: 1,
    runningTasks: 0,
    pendingTasks: 1,
    trustScore: 0.63,
    trustGrade: "B",
  },
  {
    id: "coding-agent",
    name: "Coding Agent",
    description: "Autonomous implementation and codebase operations.",
    icon: "code",
    type: "proactive",
    status: "ready",
    tools: ["generate_code", "write_file", "run_command"],
    totalTasks: 1,
    runningTasks: 0,
    pendingTasks: 1,
    trustScore: 0.68,
    trustGrade: "B",
  },
  {
    id: "stash-agent",
    name: "Stash Agent",
    description: "Specialist catalog and library quality support for the Stash lane.",
    icon: "gallery-horizontal-end",
    type: "reactive",
    status: "ready",
    tools: ["stash_search", "scene_stats", "metadata_cleanup"],
    totalTasks: 0,
    runningTasks: 0,
    pendingTasks: 0,
    trustScore: 0.66,
    trustGrade: "B",
  },
  {
    id: "data-curator",
    name: "Data Curator",
    description: "Background curation, ingestion, and indexing support across the memory fabric.",
    icon: "database",
    type: "proactive",
    status: "ready",
    tools: ["ingest_documents", "sync_qdrant", "index_status"],
    totalTasks: 0,
    runningTasks: 0,
    pendingTasks: 0,
    trustScore: 0.7,
    trustGrade: "B",
  },
];

const fixtureAgents: AgentsSnapshot = {
  generatedAt: FIXTURE_BASE_TIME,
  agents: fixtureWorkforceAgents.map(({ id, name, description, icon, tools, status }) => ({
    id,
    name,
    description,
    icon,
    tools,
    status,
  })),
};

const fixtureSlowestService =
  [...fixtureServices]
    .filter((service) => service.latencyMs !== null)
    .sort((left, right) => (right.latencyMs ?? 0) - (left.latencyMs ?? 0))[0] ?? null;

const fixtureAverageLatencyMs = Math.round(
  fixtureServices
    .flatMap((service) => (service.latencyMs === null ? [] : [service.latencyMs]))
    .reduce((sum, latency, index, values) => sum + latency / values.length, 0)
);

const fixtureWorkforce: WorkforceSnapshot = {
  generatedAt: FIXTURE_BASE_TIME,
  summary: {
    totalTasks: 8,
    pendingTasks: 2,
    pendingApprovals: 2,
    runningTasks: 1,
    completedTasks: 2,
    failedTasks: 1,
    activeGoals: 3,
    unreadNotifications: 1,
    avgTrustScore: 0.72,
    workspaceUtilization: 0.57,
    activeProjects: fixtureProjectPosture.filter((project) => ACTIVE_PROJECT_STATUSES.has(project.status)).length,
    queuedProjects: fixtureProjectPosture.filter(
      (project) =>
        project.pendingTasks > 0 ||
        project.pendingApprovals > 0 ||
        project.runningTasks > 0 ||
        project.plannedTasks > 0
    ).length,
  },
  workplan: {
    current: {
      planId: "wp-1741531200",
      generatedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 48),
      timeContext: "Monday afternoon operator pass",
      focus: "Push EoBQ content and keep Athanor drift in check.",
      taskCount: 4,
      tasks: [
        {
          taskId: "task-eoq-1",
          agentId: "coding-agent",
          projectId: "eoq",
          prompt: "Implement the next EoBQ scene renderer state machine and branching transitions.",
          priority: "high",
          rationale: "Unblocks the playable narrative path for the first tenant milestone.",
          requiresApproval: true,
        },
        {
          taskId: "task-eoq-2",
          agentId: "creative-agent",
          projectId: "eoq",
          prompt: "Generate a portrait pack for the current dark-fantasy cast using the approved style lane.",
          priority: "normal",
          rationale: "Supports the active dialogue and scene work with fresh asset coverage.",
          requiresApproval: false,
        },
        {
          taskId: "task-ath-1",
          agentId: "research-agent",
          projectId: "athanor",
          prompt: "Audit the live LiteLLM alias map against docs and deployment outputs.",
          priority: "high",
          rationale: "Prevents contract drift in the operating environment while the roadmap lands.",
          requiresApproval: false,
        },
        {
          taskId: "task-ath-2",
          agentId: "knowledge-agent",
          projectId: "athanor",
          prompt: "Identify stale command-center docs and produce a delta list with missing operator guidance.",
          priority: "low",
          rationale: "Keeps the one-person operating model legible as the system expands.",
          requiresApproval: false,
        },
      ],
    },
    history: [
      {
        planId: "wp-1741531200",
        generatedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 48),
        timeContext: "Monday afternoon operator pass",
        focus: "Push EoBQ content and keep Athanor drift in check.",
        taskCount: 4,
        tasks: [
          {
            taskId: "task-eoq-1",
            agentId: "coding-agent",
            projectId: "eoq",
            prompt: "Implement the next EoBQ scene renderer state machine and branching transitions.",
            priority: "high",
            rationale: "Unblocks the playable narrative path for the first tenant milestone.",
            requiresApproval: true,
          },
          {
            taskId: "task-eoq-2",
            agentId: "creative-agent",
            projectId: "eoq",
            prompt: "Generate a portrait pack for the current dark-fantasy cast using the approved style lane.",
            priority: "normal",
            rationale: "Supports the active dialogue and scene work with fresh asset coverage.",
            requiresApproval: false,
          },
          {
            taskId: "task-ath-1",
            agentId: "research-agent",
            projectId: "athanor",
            prompt: "Audit the live LiteLLM alias map against docs and deployment outputs.",
            priority: "high",
            rationale: "Prevents contract drift in the operating environment while the roadmap lands.",
            requiresApproval: false,
          },
          {
            taskId: "task-ath-2",
            agentId: "knowledge-agent",
            projectId: "athanor",
            prompt: "Identify stale command-center docs and produce a delta list with missing operator guidance.",
            priority: "low",
            rationale: "Keeps the one-person operating model legible as the system expands.",
            requiresApproval: false,
          },
        ],
      },
      {
        planId: "wp-1741524000",
        generatedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 180),
        timeContext: "Morning planning run",
        focus: "Stabilize the cluster and refill the media lane.",
        taskCount: 3,
        tasks: [
          {
            taskId: "task-media-1",
            agentId: "media-agent",
            projectId: "media",
            prompt: "Review the current Sonarr and Radarr queues for stuck imports and stale downloads.",
            priority: "normal",
            rationale: "Maintains the media stack without adding low-value churn.",
            requiresApproval: false,
          },
          {
            taskId: "task-ath-0",
            agentId: "general-assistant",
            projectId: "athanor",
            prompt: "Summarize degraded services, GPU hotspots, and operator actions for the morning brief.",
            priority: "normal",
            rationale: "Provides a high-signal operating summary for the day.",
            requiresApproval: false,
          },
          {
            taskId: "task-kindred-1",
            agentId: "research-agent",
            projectId: "kindred",
            prompt: "Survey recent passion-based social products and note product patterns worth tracking.",
            priority: "low",
            rationale: "Keeps the scaffolded tenant warm without distracting from active builds.",
            requiresApproval: false,
          },
        ],
      },
    ],
    needsRefill: false,
    schedule: {
      morningRunHourLocal: 7,
      morningRunMinuteLocal: 0,
      refillIntervalHours: 2,
      minPendingTasks: 2,
      nextRunAt: isoMinutesAfter(FIXTURE_BASE_TIME, 96),
    },
  },
  tasks: [
    {
      id: "task-eoq-1",
      agentId: "coding-agent",
      prompt: "Implement the next EoBQ scene renderer state machine and branching transitions.",
      priority: "high",
      status: "pending_approval",
      createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 47),
      startedAt: null,
      completedAt: null,
      durationMs: null,
      requiresApproval: true,
      source: "work_planner",
      projectId: "eoq",
      planId: "wp-1741531200",
      rationale: "Unblocks the playable narrative path for the first tenant milestone.",
      parentTaskId: null,
      result: null,
      error: null,
      stepCount: 0,
    },
    {
      id: "task-eoq-2",
      agentId: "creative-agent",
      prompt: "Generate a portrait pack for the current dark-fantasy cast using the approved style lane.",
      priority: "normal",
      status: "pending",
      createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 46),
      startedAt: null,
      completedAt: null,
      durationMs: null,
      requiresApproval: false,
      source: "work_planner",
      projectId: "eoq",
      planId: "wp-1741531200",
      rationale: "Supports the active dialogue and scene work with fresh asset coverage.",
      parentTaskId: null,
      result: null,
      error: null,
      stepCount: 0,
    },
    {
      id: "task-ath-1",
      agentId: "research-agent",
      prompt: "Audit the live LiteLLM alias map against docs and deployment outputs.",
      priority: "high",
      status: "running",
      createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 44),
      startedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 34),
      completedAt: null,
      durationMs: null,
      requiresApproval: false,
      source: "work_planner",
      projectId: "athanor",
      planId: "wp-1741531200",
      rationale: "Prevents contract drift in the operating environment while the roadmap lands.",
      parentTaskId: null,
      result: null,
      error: null,
      stepCount: 5,
    },
    {
      id: "task-ath-2",
      agentId: "knowledge-agent",
      prompt: "Identify stale command-center docs and produce a delta list with missing operator guidance.",
      priority: "low",
      status: "pending",
      createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 43),
      startedAt: null,
      completedAt: null,
      durationMs: null,
      requiresApproval: false,
      source: "work_planner",
      projectId: "athanor",
      planId: "wp-1741531200",
      rationale: "Keeps the one-person operating model legible as the system expands.",
      parentTaskId: null,
      result: null,
      error: null,
      stepCount: 0,
    },
    {
      id: "task-home-1",
      agentId: "home-agent",
      prompt: "Adjust the evening lighting automation after the recent occupancy drift report.",
      priority: "high",
      status: "pending_approval",
      createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 21),
      startedAt: null,
      completedAt: null,
      durationMs: null,
      requiresApproval: true,
      source: "manual",
      projectId: "athanor",
      planId: null,
      rationale: null,
      parentTaskId: null,
      result: null,
      error: null,
      stepCount: 0,
    },
    {
      id: "task-ath-brief",
      agentId: "general-assistant",
      prompt: "Summarize degraded services, GPU hotspots, and operator actions for the morning brief.",
      priority: "normal",
      status: "completed",
      createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 190),
      startedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 188),
      completedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 183),
      durationMs: 300000,
      requiresApproval: false,
      source: "work_planner",
      projectId: "athanor",
      planId: "wp-1741524000",
      rationale: "Provides a high-signal operating summary for the day.",
      parentTaskId: null,
      result: "Morning brief published with service drift, GPU hotspot, and queue notes.",
      error: null,
      stepCount: 4,
    },
    {
      id: "task-kindred-1",
      agentId: "research-agent",
      prompt: "Survey recent passion-based social products and note product patterns worth tracking.",
      priority: "low",
      status: "completed",
      createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 170),
      startedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 165),
      completedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 149),
      durationMs: 960000,
      requiresApproval: false,
      source: "work_planner",
      projectId: "kindred",
      planId: "wp-1741524000",
      rationale: "Keeps the scaffolded tenant warm without distracting from active builds.",
      parentTaskId: null,
      result: "Research memo recorded with three adjacent product patterns and open questions.",
      error: null,
      stepCount: 6,
    },
    {
      id: "task-media-1",
      agentId: "media-agent",
      prompt: "Review the current Sonarr and Radarr queues for stuck imports and stale downloads.",
      priority: "normal",
      status: "failed",
      createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 150),
      startedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 144),
      completedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 138),
      durationMs: 360000,
      requiresApproval: false,
      source: "work_planner",
      projectId: "media",
      planId: "wp-1741524000",
      rationale: "Maintains the media stack without adding low-value churn.",
      parentTaskId: null,
      result: null,
      error: "Sonarr queue returned a transient upstream timeout during queue hydration.",
      stepCount: 3,
    },
  ],
  goals: [
    {
      id: "goal-ops-1",
      text: "Keep Athanor coherent as a one-person operating environment, not a bag of tools.",
      agentId: "global",
      priority: "high",
      createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 260),
      active: true,
    },
    {
      id: "goal-eoq-1",
      text: "Prioritize EoBQ tenant momentum when tradeoffs compete with internal polish work.",
      agentId: "global",
      priority: "high",
      createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 240),
      active: true,
    },
    {
      id: "goal-docs-1",
      text: "Keep operator-facing docs aligned with current deployment contracts and project posture.",
      agentId: "knowledge-agent",
      priority: "normal",
      createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 220),
      active: true,
    },
  ],
  trust: [
    {
      agentId: "general-assistant",
      trustScore: 0.81,
      trustGrade: "A",
      positiveFeedback: 23,
      negativeFeedback: 2,
      totalFeedback: 25,
      escalationCount: 1,
    },
    {
      agentId: "media-agent",
      trustScore: 0.76,
      trustGrade: "B",
      positiveFeedback: 16,
      negativeFeedback: 3,
      totalFeedback: 19,
      escalationCount: 2,
    },
    {
      agentId: "creative-agent",
      trustScore: 0.74,
      trustGrade: "B",
      positiveFeedback: 13,
      negativeFeedback: 4,
      totalFeedback: 17,
      escalationCount: 2,
    },
    {
      agentId: "research-agent",
      trustScore: 0.72,
      trustGrade: "B",
      positiveFeedback: 18,
      negativeFeedback: 5,
      totalFeedback: 23,
      escalationCount: 3,
    },
    {
      agentId: "coding-agent",
      trustScore: 0.68,
      trustGrade: "B",
      positiveFeedback: 14,
      negativeFeedback: 5,
      totalFeedback: 19,
      escalationCount: 4,
    },
    {
      agentId: "knowledge-agent",
      trustScore: 0.63,
      trustGrade: "B",
      positiveFeedback: 9,
      negativeFeedback: 4,
      totalFeedback: 13,
      escalationCount: 2,
    },
    {
      agentId: "home-agent",
      trustScore: 0.51,
      trustGrade: "C",
      positiveFeedback: 3,
      negativeFeedback: 3,
      totalFeedback: 6,
      escalationCount: 5,
    },
    {
      agentId: "stash-agent",
      trustScore: 0.66,
      trustGrade: "B",
      positiveFeedback: 8,
      negativeFeedback: 2,
      totalFeedback: 10,
      escalationCount: 1,
    },
    {
      agentId: "data-curator",
      trustScore: 0.7,
      trustGrade: "B",
      positiveFeedback: 11,
      negativeFeedback: 3,
      totalFeedback: 14,
      escalationCount: 1,
    },
  ],
  notifications: [
    {
      id: "notif-home-1",
      agentId: "home-agent",
      action: "Adjust evening lighting automation",
      category: "routine",
      confidence: 0.41,
      description: "The home lane wants approval before changing the current presence-based lighting automation.",
      tier: "ask",
      createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 20),
      resolved: false,
      resolution: null,
    },
    {
      id: "notif-media-1",
      agentId: "media-agent",
      action: "Queued a notice about a transient Sonarr import stall",
      category: "content",
      confidence: 0.83,
      description: "The media lane auto-acted and logged the failure for later review.",
      tier: "notify",
      createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 130),
      resolved: true,
      resolution: "approved",
    },
  ],
  workspace: {
    totalItems: 4,
    broadcastItems: 4,
    capacity: 7,
    utilization: 4 / 7,
    competitionRunning: true,
    agentsActive: [
      { agentId: "research-agent", count: 1 },
      { agentId: "general-assistant", count: 1 },
      { agentId: "media-agent", count: 1 },
      { agentId: "knowledge-agent", count: 1 },
    ],
    topItem: {
      id: "ws-ops-1",
      sourceAgent: "general-assistant",
      content: "Forge failures point to a missing 4x-UltraSharp upscaler dependency in the current image lane.",
      priority: "high",
      salience: 4.6,
      createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 8),
      ttlSeconds: 300,
      coalition: ["creative-agent", "coding-agent"],
      projectId: "athanor",
    },
    broadcast: [
      {
        id: "ws-ops-1",
        sourceAgent: "general-assistant",
        content: "Forge failures point to a missing 4x-UltraSharp upscaler dependency in the current image lane.",
        priority: "high",
        salience: 4.6,
        createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 8),
        ttlSeconds: 300,
        coalition: ["creative-agent", "coding-agent"],
        projectId: "athanor",
      },
      {
        id: "ws-eoq-1",
        sourceAgent: "creative-agent",
        content: "EoBQ portrait generation is blocked on fresh prompt cards for the current cast.",
        priority: "normal",
        salience: 2.8,
        createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 11),
        ttlSeconds: 300,
        coalition: ["coding-agent"],
        projectId: "eoq",
      },
      {
        id: "ws-media-1",
        sourceAgent: "media-agent",
        content: "Sonarr queue recovered after timeout, but one import is still worth manual verification.",
        priority: "normal",
        salience: 2.1,
        createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 17),
        ttlSeconds: 300,
        coalition: [],
        projectId: "media",
      },
      {
        id: "ws-kindred-1",
        sourceAgent: "research-agent",
        content: "Kindred research found adjacent products but nothing with strong passion-first onboarding yet.",
        priority: "low",
        salience: 0.9,
        createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 23),
        ttlSeconds: 300,
        coalition: [],
        projectId: "kindred",
      },
    ],
  },
  subscriptions: [
    {
      agentId: "media-agent",
      keywords: ["sonarr", "radarr", "plex", "import", "queue"],
      sourceFilters: ["event:media", "service:plex"],
      threshold: 0.35,
      reactPromptTemplate: "Handle media-domain signal: {content}",
    },
    {
      agentId: "creative-agent",
      keywords: ["forge", "comfyui", "render", "upscaler", "image"],
      sourceFilters: ["event:creative", "project:eoq"],
      threshold: 0.42,
      reactPromptTemplate: "Investigate creative pipeline issue: {content}",
    },
    {
      agentId: "knowledge-agent",
      keywords: ["docs", "adr", "contract", "manifest", "roadmap"],
      sourceFilters: ["project:athanor", "workspace"],
      threshold: 0.28,
      reactPromptTemplate: "Capture and reconcile this operating knowledge: {content}",
    },
  ],
  conventions: {
    proposed: [
      {
        id: "conv-proposed-1",
        type: "quality",
        agentId: "coding-agent",
        description: "Route all operator-facing dashboard changes through typed dashboard-owned APIs before UI adoption.",
        rule: "No new production UI page should call node services directly from the browser.",
        source: "dashboard migration",
        occurrences: 4,
        status: "proposed",
        createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 55),
        confirmedAt: null,
      },
    ],
    confirmed: [
      {
        id: "conv-confirmed-1",
        type: "behavior",
        agentId: "general-assistant",
        description: "Prefer Command Center visibility for high-signal cluster or workforce changes.",
        rule: "Escalate meaningful system drift into the workspace and operator dashboard surfaces.",
        source: "operator review",
        occurrences: 12,
        status: "confirmed",
        createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 720),
        confirmedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 690),
      },
      {
        id: "conv-confirmed-2",
        type: "preference",
        agentId: "knowledge-agent",
        description: "Treat BUILD-MANIFEST as the tactical queue under the Athanor Next roadmap.",
        rule: "Roadmap defines direction; manifest defines execution sequence.",
        source: "docs convergence",
        occurrences: 6,
        status: "confirmed",
        createdAt: isoMinutesBefore(FIXTURE_BASE_TIME, 640),
        confirmedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 600),
      },
    ],
  },
  improvement: {
    totalProposals: 18,
    pending: 3,
    validated: 6,
    deployed: 7,
    failed: 2,
    benchmarkResults: 41,
    lastCycle: {
      timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 95),
      patternsConsumed: 11,
      proposalsGenerated: 4,
      benchmarks: {
        passed: 7,
        total: 8,
        passRate: 0.875,
      },
    },
  },
  agents: fixtureWorkforceAgents,
  projects: fixtureProjectPosture,
  schedules: [
    {
      agentId: "media-agent",
      intervalSeconds: 900,
      intervalHuman: "every 15 min",
      enabled: true,
      lastRunAt: isoMinutesBefore(FIXTURE_BASE_TIME, 12),
      nextRunInSeconds: 180,
      priority: "normal",
    },
    {
      agentId: "home-agent",
      intervalSeconds: 300,
      intervalHuman: "every 5 min",
      enabled: true,
      lastRunAt: isoMinutesBefore(FIXTURE_BASE_TIME, 4),
      nextRunInSeconds: 60,
      priority: "high",
    },
    {
      agentId: "data-curator",
      intervalSeconds: 21600,
      intervalHuman: "every 6 hours",
      enabled: true,
      lastRunAt: isoMinutesBefore(FIXTURE_BASE_TIME, 100),
      nextRunInSeconds: 8400,
      priority: "low",
    },
  ],
};

const fixtureOverview: OverviewSnapshot = {
  generatedAt: FIXTURE_BASE_TIME,
  summary: {
    totalServices: fixtureServices.length,
    healthyServices: fixtureServices.filter((service) => service.healthy).length,
    degradedServices: fixtureServices.filter((service) => !service.healthy).length,
    averageLatencyMs: fixtureAverageLatencyMs,
    averageGpuUtilization: fixtureGpuSnapshot.summary.averageUtilization,
    readyAgents: fixtureAgents.agents.filter((agent) => agent.status === "ready").length,
    totalAgents: fixtureAgents.agents.length,
    reachableBackends: fixtureBackends.filter((backend) => backend.reachable).length,
    totalBackends: fixtureBackends.length,
    activeProjects: fixtureProjectSnapshots.filter((project) => ACTIVE_PROJECT_STATUSES.has(project.status)).length,
    firstClassProjects: fixtureProjectSnapshots.filter((project) => project.firstClass).length,
  },
  nodes: fixtureNodes,
  services: fixtureServices,
  serviceTrend: fixtureServiceAggregate,
  gpuTrend: fixtureGpuHistory.nodes[0].points.map((point, index) => {
    const samples = fixtureGpuHistory.nodes
      .map((series) => series.points[index]?.value)
      .filter((value): value is number => value !== null && value !== undefined);
    const average = samples.reduce((sum, value) => sum + value, 0) / samples.length;
    return {
      timestamp: point.timestamp,
      value: Math.round(average * 10) / 10,
    };
  }),
  backends: fixtureBackends,
  agents: fixtureAgents.agents,
  projects: fixtureProjectSnapshots,
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
  externalTools: config.externalTools,
  navAttention: buildNavAttentionSignals({
    workforce: fixtureWorkforce,
    services: fixtureServices,
    agents: fixtureAgents.agents,
    judge: {
      generated_at: FIXTURE_BASE_TIME,
      summary: {
        recent_verdicts: 5,
        accept_count: 3,
        reject_count: 2,
        review_required: 2,
        acceptance_rate: 0.6,
        pending_review_queue: 2,
      },
    },
    updatedAt: FIXTURE_BASE_TIME,
  }),
  workforce: fixtureWorkforce,
};

const fixtureServicesSnapshot: ServicesSnapshot = {
  generatedAt: FIXTURE_BASE_TIME,
  summary: {
    total: fixtureServices.length,
    healthy: fixtureServices.filter((service) => service.healthy).length,
    degraded: fixtureServices.filter((service) => !service.healthy).length,
    averageLatencyMs: fixtureAverageLatencyMs,
    slowestServiceId: fixtureSlowestService?.id ?? null,
    slowestServiceName: fixtureSlowestService?.name ?? null,
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

const fixtureHistorySnapshot: HistorySnapshot = {
  generatedAt: FIXTURE_BASE_TIME,
  summary: {
    activityCount: 4,
    conversationCount: 4,
    outputCount: 5,
    reviewCount: fixtureWorkforce.tasks.filter((task) =>
      ["pending_approval", "failed", "completed"].includes(task.status)
    ).length,
  },
  projects: fixtureOverview.projects,
  agents: fixtureWorkforce.agents,
  tasks: fixtureWorkforce.tasks,
  activity: [
    {
      id: "activity-1",
      agentId: "coding-agent",
      projectId: "eoq",
      actionType: "write_scene_renderer",
      inputSummary: "Reworked the EoBQ scene renderer to support branching transitions.",
      outputSummary: "Renderer state machine updated and preview assets refreshed.",
      toolsUsed: ["read_file", "write_file", "run_command"],
      durationMs: 142000,
      timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 12),
      relatedTaskId: "task-eoq-1",
      relatedThreadId: "thread-eoq-1",
      reviewTaskId: "task-eoq-1",
      status: "pending_approval",
      href: "/review?selection=task-eoq-1",
    },
    {
      id: "activity-2",
      agentId: "creative-agent",
      projectId: "eoq",
      actionType: "generate_portrait_pack",
      inputSummary: "Queued fresh character portraits for the current cast.",
      outputSummary: "Three candidate portrait generations are ready for review.",
      toolsUsed: ["generate_image", "queue_status"],
      durationMs: 78000,
      timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 24),
      relatedTaskId: "task-eoq-2",
      relatedThreadId: "thread-eoq-2",
      reviewTaskId: null,
      status: "completed",
      href: "/gallery?selection=EoBQ%2Fcharacter",
    },
    {
      id: "activity-3",
      agentId: "research-agent",
      projectId: "athanor",
      actionType: "audit_runtime_contracts",
      inputSummary: "Compared live routing against the Athanor Next contract map.",
      outputSummary: "LiteLLM alias map is aligned, but one dashboard route still needed migration.",
      toolsUsed: ["web_search", "cluster_health", "search_knowledge"],
      durationMs: 91000,
      timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 37),
      relatedTaskId: "task-ath-1",
      relatedThreadId: "thread-ath-1",
      reviewTaskId: null,
      status: "running",
      href: "/activity?selection=activity-3",
    },
    {
      id: "activity-4",
      agentId: "knowledge-agent",
      projectId: "athanor",
      actionType: "document_delta",
      inputSummary: "Compiled stale command-center docs and missing runbook notes.",
      outputSummary: "Draft operator delta list stored for review.",
      toolsUsed: ["search_knowledge", "write_file"],
      durationMs: 54000,
      timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 51),
      relatedTaskId: "task-ath-2",
      relatedThreadId: "thread-ath-2",
      reviewTaskId: "task-ath-2",
      status: "completed",
      href: "/outputs?selection=output-2",
    },
  ],
  conversations: [
    {
      id: "conversation-1",
      threadId: "thread-eoq-1",
      agentId: "coding-agent",
      projectId: "eoq",
      userMessage: "Finish the branching scene renderer and keep the UI transitions deterministic.",
      assistantResponse: "I split the renderer into explicit state edges and generated a review-ready diff.",
      toolsUsed: ["read_file", "write_file", "run_command"],
      durationMs: 142000,
      timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 12),
      relatedTaskId: "task-eoq-1",
      href: "/conversations?selection=thread-eoq-1",
    },
    {
      id: "conversation-2",
      threadId: "thread-eoq-2",
      agentId: "creative-agent",
      projectId: "eoq",
      userMessage: "Generate the next portrait lane using the approved dark-fantasy style.",
      assistantResponse: "Queued three portrait variants and attached the generation prompts for review.",
      toolsUsed: ["generate_image", "queue_status"],
      durationMs: 78000,
      timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 24),
      relatedTaskId: "task-eoq-2",
      href: "/gallery?selection=EoBQ%2Fcharacter",
    },
    {
      id: "conversation-3",
      threadId: "thread-ath-1",
      agentId: "research-agent",
      projectId: "athanor",
      userMessage: "Audit the live alias map and highlight any drift against docs.",
      assistantResponse: "The runtime map is aligned after the DEV retrieval move. One legacy dashboard lane still bypassed the family snapshot model.",
      toolsUsed: ["cluster_health", "search_knowledge"],
      durationMs: 91000,
      timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 37),
      relatedTaskId: "task-ath-1",
      href: "/insights?selection=pattern-contract-drift",
    },
    {
      id: "conversation-4",
      threadId: "thread-ath-2",
      agentId: "knowledge-agent",
      projectId: "athanor",
      userMessage: "Find stale docs and prepare the delta summary.",
      assistantResponse: "I mapped the stale references and linked them to the new Athanor Next roadmap layers.",
      toolsUsed: ["search_knowledge", "write_file"],
      durationMs: 54000,
      timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 51),
      relatedTaskId: "task-ath-2",
      href: "/review?selection=task-ath-2",
    },
  ],
  outputs: [
    {
      id: "output-1",
      path: "output/eoq/scene-renderer-state-machine.diff",
      fileName: "scene-renderer-state-machine.diff",
      category: "scene",
      sizeBytes: 18942,
      modifiedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 11),
      projectId: "eoq",
      relatedTaskId: "task-eoq-1",
      previewAvailable: true,
      href: "/outputs?selection=output-1",
    },
    {
      id: "output-2",
      path: "output/athanor/operator-doc-delta.md",
      fileName: "operator-doc-delta.md",
      category: "research",
      sizeBytes: 8234,
      modifiedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 49),
      projectId: "athanor",
      relatedTaskId: "task-ath-2",
      previewAvailable: true,
      href: "/outputs?selection=output-2",
    },
    {
      id: "output-3",
      path: "output/eoq/portraits/queen-portrait-a.webp",
      fileName: "queen-portrait-a.webp",
      category: "character",
      sizeBytes: 2483942,
      modifiedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 23),
      projectId: "eoq",
      relatedTaskId: "task-eoq-2",
      previewAvailable: false,
      href: "/gallery?selection=EoBQ%2Fcharacter",
    },
    {
      id: "output-4",
      path: "output/athanor/runtime-audit.md",
      fileName: "runtime-audit.md",
      category: "research",
      sizeBytes: 12490,
      modifiedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 34),
      projectId: "athanor",
      relatedTaskId: "task-ath-1",
      previewAvailable: true,
      href: "/outputs?selection=output-4",
    },
    {
      id: "output-5",
      path: "output/eoq/scene-cast-prompts.json",
      fileName: "scene-cast-prompts.json",
      category: "scene",
      sizeBytes: 4912,
      modifiedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 21),
      projectId: "eoq",
      relatedTaskId: "task-eoq-2",
      previewAvailable: true,
      href: "/outputs?selection=output-5",
    },
  ],
};

const fixtureIntelligenceSnapshot: IntelligenceSnapshot = {
  generatedAt: FIXTURE_BASE_TIME,
  projects: fixtureOverview.projects,
  agents: fixtureWorkforce.agents,
  report: {
    timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 18),
    periodHours: 24,
    eventCount: 117,
    activityCount: 84,
    patterns: [
      {
        type: "contract_drift",
        severity: "high",
        agentId: "research-agent",
        count: 2,
        sampleErrors: ["Legacy route bypassed the family snapshot loader."],
        topics: { dashboard: 4, config: 3 },
        actions: { migrate: 1 },
      },
      {
        type: "creative_backlog",
        severity: "medium",
        agentId: "creative-agent",
        count: 3,
        sampleErrors: [],
        topics: { eoq: 5, portraits: 3 },
        actions: { queue: 2 },
      },
      {
        type: "doc_alignment",
        severity: "low",
        agentId: "knowledge-agent",
        count: 4,
        sampleErrors: [],
        topics: { roadmap: 2, manifest: 2 },
        actions: { update: 2 },
      },
    ],
    recommendations: [
      "Finish migrating the remaining legacy dashboard routes onto family snapshots.",
      "Review the pending EoBQ renderer diff before promoting the next creative cycle.",
      "Keep DEV retrieval endpoints in the service-history and monitoring views.",
    ],
    autonomyAdjustments: [
      {
        agentId: "coding-agent",
        category: "code_write",
        previous: 0.64,
        delta: -0.04,
        next: 0.6,
      },
      {
        agentId: "creative-agent",
        category: "image_generation",
        previous: 0.7,
        delta: 0.05,
        next: 0.75,
      },
    ],
    agentBehavior: [
      {
        agentId: "research-agent",
        dominantTopic: "runtime contracts",
        dominantType: "audit",
        entityCount: 14,
        actions: { audit: 4, summarize: 2 },
      },
      {
        agentId: "creative-agent",
        dominantTopic: "portraits",
        dominantType: "generation",
        entityCount: 9,
        actions: { queue: 3, preview: 2 },
      },
    ],
  },
  learning: {
    timestamp: FIXTURE_BASE_TIME,
    metrics: {
      cache: {
        totalEntries: 184,
        hitRate: 0.42,
        tokensSaved: 128432,
        avgSimilarity: 0.86,
      },
      circuits: {
        services: 19,
        open: 1,
        halfOpen: 1,
        closed: 17,
        totalFailures: 8,
      },
      preferences: {
        modelTaskPairs: 12,
        totalSamples: 87,
        avgCompositeScore: 0.74,
        converged: 6,
      },
      trust: {
        agentsTracked: 7,
        avgTrustScore: 0.69,
        highTrust: 2,
        lowTrust: 1,
      },
      diagnosis: {
        recentFailures: 3,
        patternsDetected: 5,
        autoRemediations: 2,
      },
      memory: {
        collections: 3,
        totalPoints: 1824,
      },
      tasks: {
        total: 48,
        completed: 33,
        failed: 4,
        successRate: 0.6875,
      },
    },
    summary: {
      overallHealth: 0.72,
      dataPoints: 7,
      positiveSignals: [
        "Semantic cache hit rate is improving.",
        "Trust is stabilizing for the high-autonomy lanes.",
        "Improvement benchmarks are passing consistently.",
      ],
      assessment: "Compounding",
    },
  },
  improvement: fixtureWorkforce.improvement,
  reviewTasks: fixtureWorkforce.tasks.filter((task) =>
    ["pending_approval", "failed", "completed"].includes(task.status)
  ),
};

const fixtureMemorySnapshot: MemorySnapshot = {
  generatedAt: FIXTURE_BASE_TIME,
  projects: fixtureOverview.projects,
  summary: {
    qdrantOnline: true,
    neo4jOnline: true,
    points: 1824,
    vectors: 1824,
    graphNodes: 612,
    graphRelationships: 2841,
  },
  preferences: [
    {
      score: 0.95,
      content: "Keep Athanor desktop-first and optimized for a single operator.",
      signalType: "remember_this",
      agentId: "global",
      category: "ux",
      timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 180),
    },
    {
      score: 0.91,
      content: "EoBQ is the first active first-class tenant after Athanor core.",
      signalType: "config_choice",
      agentId: "knowledge-agent",
      category: "project",
      timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 300),
    },
    {
      score: 0.84,
      content: "Prefer visible focus states and reduced-motion-safe interactions in the dashboard.",
      signalType: "thumbs_up",
      agentId: "coding-agent",
      category: "accessibility",
      timestamp: isoMinutesBefore(FIXTURE_BASE_TIME, 420),
    },
  ],
  recentItems: [
    {
      id: "recent-1",
      title: "Athanor Next Master Roadmap",
      url: null,
      source: "docs",
      category: "roadmap",
      subcategory: "design",
      description: "North-star design layer for Athanor Next.",
      indexedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 40),
    },
    {
      id: "recent-2",
      title: "EoBQ portrait direction pack",
      url: config.eoq.url,
      source: "eoq",
      category: "creative",
      subcategory: "reference",
      description: "Character portrait references and style constraints.",
      indexedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 90),
    },
    {
      id: "recent-3",
      title: "LiteLLM alias contract notes",
      url: null,
      source: "ops",
      category: "system",
      subcategory: "routing",
      description: "Alias mapping and fallback semantics.",
      indexedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 150),
    },
    {
      id: "recent-4",
      title: "Dark fantasy onboarding comparisons",
      url: null,
      source: "research",
      category: "kindred",
      subcategory: "market",
      description: "Adjacent products and passion-first onboarding analysis.",
      indexedAt: isoMinutesBefore(FIXTURE_BASE_TIME, 230),
    },
  ],
  categories: [
    { name: "roadmap", count: 112 },
    { name: "creative", count: 388 },
    { name: "system", count: 247 },
    { name: "research", count: 194 },
  ],
  topTopics: [
    { name: "Athanor Next", connections: 61 },
    { name: "EoBQ", connections: 54 },
    { name: "LiteLLM", connections: 37 },
    { name: "ComfyUI", connections: 28 },
  ],
  graphLabels: ["Project", "Topic", "Preference", "Task", "Tenant", "Service"],
};

const fixtureMonitoringSnapshot: MonitoringSnapshot = {
  generatedAt: FIXTURE_BASE_TIME,
  summary: {
    reachableNodes: 4,
    totalNodes: 4,
    averageCpu: 47.5,
    totalMemUsed: 111239652352,
    totalMemTotal: 266287972352,
    networkRxRate: 9437184,
    networkTxRate: 4194304,
  },
  nodes: [
    {
      id: "node1",
      name: "Foundry",
      ip: nodeIp("node1"),
      role: "Coordinator inference and agent execution",
      cpuUsage: 68,
      memUsed: 73873436672,
      memTotal: 137438953472,
      diskUsed: 731637227520,
      diskTotal: 1099511627776,
      networkRxRate: 5242880,
      networkTxRate: 2621440,
      uptime: 604800,
      load1: 4.2,
      cpuHistory: [44, 48, 52, 56, 61, 65, 68],
      memHistory: [49, 50, 51, 52, 53, 53, 54],
    },
    {
      id: "node2",
      name: "Workshop",
      ip: nodeIp("node2"),
      role: "Worker inference, creative runtimes, and UI",
      cpuUsage: 41,
      memUsed: 25769803776,
      memTotal: 68719476736,
      diskUsed: 362387865600,
      diskTotal: 549755813888,
      networkRxRate: 3145728,
      networkTxRate: 1048576,
      uptime: 518400,
      load1: 2.3,
      cpuHistory: [25, 28, 33, 36, 39, 40, 41],
      memHistory: [31, 33, 34, 36, 37, 37, 38],
    },
    {
      id: "vault",
      name: "VAULT",
      ip: nodeIp("vault"),
      role: "Routing, memory, media, home, and observability",
      cpuUsage: 17,
      memUsed: 11811160064,
      memTotal: 34359738368,
      diskUsed: 2336462209024,
      diskTotal: 4398046511104,
      networkRxRate: 1572864,
      networkTxRate: 786432,
      uptime: 950400,
      load1: 1.1,
      cpuHistory: [11, 12, 14, 15, 17, 16, 17],
      memHistory: [30, 31, 31, 32, 33, 34, 34],
    },
    {
      id: "dev",
      name: "DEV",
      ip: nodeIp("dev"),
      role: "Ops workstation and retrieval runtimes",
      cpuUsage: 64,
      memUsed: 0,
      memTotal: 25769803776,
      diskUsed: 171798691840,
      diskTotal: 549755813888,
      networkRxRate: 1310720,
      networkTxRate: 524288,
      uptime: 259200,
      load1: 3.6,
      cpuHistory: [29, 36, 44, 51, 57, 61, 64],
      memHistory: [21, 22, 23, 24, 24, 25, 26],
    },
  ],
  dashboards: fixtureOverview.externalTools
    .filter((tool) => ["grafana", "prometheus"].includes(tool.id))
    .map((tool) => ({
      id: tool.id,
      label: tool.label,
      description: tool.description,
      url: tool.url,
    })),
};

const fixtureMediaSnapshot: MediaSnapshot = {
  generatedAt: FIXTURE_BASE_TIME,
  streamCount: 2,
  sessions: [
    {
      friendlyName: "Living Room Shield",
      title: "Dune: Part Two",
      state: "playing",
      progressPercent: 46,
      transcodeDecision: "direct play",
      mediaType: "movie",
      year: "2024",
      thumb: null,
    },
    {
      friendlyName: "Bedroom Apple TV",
      title: "Shogun S01E05",
      state: "paused",
      progressPercent: 71,
      transcodeDecision: "transcode",
      mediaType: "episode",
      year: "2024",
      thumb: null,
    },
  ],
  downloads: [
    {
      id: "download-1",
      title: "The Last of Us S02E01",
      source: "Sonarr",
      progressPercent: 68,
      status: "downloading",
      timeLeft: "12m",
    },
    {
      id: "download-2",
      title: "Civil War (2024)",
      source: "Radarr",
      progressPercent: 24,
      status: "queued",
      timeLeft: "41m",
    },
  ],
  tvUpcoming: [
    {
      id: "tv-1",
      title: "The Last of Us",
      seriesTitle: "The Last of Us",
      seasonNumber: 2,
      episodeNumber: 1,
      airDateUtc: isoMinutesAfter(FIXTURE_BASE_TIME, 60 * 20),
      hasFile: false,
    },
  ],
  movieUpcoming: [
    {
      id: "movie-1",
      title: "Nosferatu",
      seriesTitle: null,
      seasonNumber: null,
      episodeNumber: null,
      airDateUtc: isoMinutesAfter(FIXTURE_BASE_TIME, 60 * 24 * 4),
      hasFile: false,
    },
  ],
  watchHistory: [
    {
      id: "watch-1",
      friendlyName: "Living Room Shield",
      title: "Blue Eye Samurai",
      date: isoMinutesBefore(FIXTURE_BASE_TIME, 210),
      duration: "54m",
      watchedStatus: 1,
    },
    {
      id: "watch-2",
      friendlyName: "Bedroom Apple TV",
      title: "Arcane",
      date: isoMinutesBefore(FIXTURE_BASE_TIME, 420),
      duration: "47m",
      watchedStatus: 1,
    },
  ],
  tvLibrary: {
    total: 412,
    monitored: 401,
    episodes: 17428,
    sizeGb: 28493,
  },
  movieLibrary: {
    total: 1386,
    monitored: 1362,
    episodes: null,
    sizeGb: 18241,
    hasFile: 1317,
  },
  stash: {
    sceneCount: 18492,
    imageCount: 23011,
    performerCount: 781,
    studioCount: 128,
    tagCount: 2987,
    scenesSize: 1149239298048,
    scenesDuration: 4893200,
  },
  launchLinks: [
    { id: "plex", label: "Plex", url: joinUrl(config.plex.url, "/web") },
    { id: "sonarr", label: "Sonarr", url: config.sonarr.url },
    { id: "radarr", label: "Radarr", url: config.radarr.url },
    { id: "stash", label: "Stash", url: config.stash.url },
  ],
};

const fixtureGallerySnapshot: GallerySnapshot = {
  generatedAt: FIXTURE_BASE_TIME,
  queueRunning: 1,
  queuePending: 2,
  deviceName: "RTX 5090",
  vramUsedGiB: 18.4,
  vramTotalGiB: 32,
  items: [
    {
      id: "gallery-1",
      prompt:
        "Cinematic portrait of a regal queen in dark armor, candlelit throne room, photorealistic, 8k.",
      outputPrefix: "EoBQ/character",
      timestamp: Math.floor(new Date(isoMinutesBefore(FIXTURE_BASE_TIME, 23)).getTime() / 1000),
      outputImages: [{ filename: "queen-portrait-a.webp", subfolder: "EoBQ/character", type: "output" }],
    },
    {
      id: "gallery-2",
      prompt:
        "Wide establishing shot of a black-iron throne room with long shadows and drifting ash.",
      outputPrefix: "EoBQ/scene",
      timestamp: Math.floor(new Date(isoMinutesBefore(FIXTURE_BASE_TIME, 42)).getTime() / 1000),
      outputImages: [{ filename: "throne-room-wide.webp", subfolder: "EoBQ/scene", type: "output" }],
    },
    {
      id: "gallery-3",
      prompt: "Painterly portrait exploration for a future Kindred onboarding card.",
      outputPrefix: "kindred/concepts",
      timestamp: Math.floor(new Date(isoMinutesBefore(FIXTURE_BASE_TIME, 85)).getTime() / 1000),
      outputImages: [{ filename: "kindred-concept-a.webp", subfolder: "kindred/concepts", type: "output" }],
    },
  ],
};

const fixtureHomeSnapshot: HomeSnapshot = {
  generatedAt: FIXTURE_BASE_TIME,
  online: false,
  configured: false,
  title: "Home Assistant",
  summary: "Home Assistant is reachable only after onboarding and credential wiring are complete.",
  setupSteps: [
    {
      id: "ha-runtime",
      label: "Home Assistant runtime reachable",
      status: "pending",
      note: "Dashboard probe has not confirmed a healthy API response yet.",
    },
    {
      id: "ha-onboarding",
      label: "Complete Home Assistant onboarding",
      status: "blocked",
      note: "Requires an authenticated browser session on the Home Assistant surface.",
    },
    {
      id: "home-agent",
      label: "Enable home-agent operational lane",
      status: "blocked",
      note: "Wait until onboarding and credential wiring are complete.",
    },
    {
      id: "ha-mcp",
      label: "Expose focused home-control panels in Athanor",
      status: "pending",
      note: "Follow after the base integration is verified.",
    },
  ],
  panels: [
    {
      id: "lights",
      label: "Lights",
      description: "Room-by-room brightness, scenes, and lighting state.",
      href: "/home?panel=lights",
    },
    {
      id: "climate",
      label: "Climate",
      description: "Thermostat, humidity, and HVAC state.",
      href: "/home?panel=climate",
    },
    {
      id: "presence",
      label: "Presence",
      description: "Who is home, presence rules, and automations.",
      href: "/home?panel=presence",
    },
  ],
};

export function isDashboardFixtureMode() {
  return process.env.DASHBOARD_FIXTURE_MODE === "1";
}

export function getFixtureOverviewSnapshot(): OverviewSnapshot {
  return cloneFixture(fixtureOverview);
}

export function getFixtureWorkforceSnapshot(): WorkforceSnapshot {
  return cloneFixture(fixtureWorkforce);
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

export function getFixtureHistorySnapshot(): HistorySnapshot {
  return cloneFixture(fixtureHistorySnapshot);
}

export function getFixtureIntelligenceSnapshot(): IntelligenceSnapshot {
  return cloneFixture(fixtureIntelligenceSnapshot);
}

export function getFixtureMemorySnapshot(): MemorySnapshot {
  return cloneFixture(fixtureMemorySnapshot);
}

export function getFixtureMonitoringSnapshot(): MonitoringSnapshot {
  return cloneFixture(fixtureMonitoringSnapshot);
}

export function getFixtureMediaSnapshot(): MediaSnapshot {
  return cloneFixture(fixtureMediaSnapshot);
}

export function getFixtureGallerySnapshot(): GallerySnapshot {
  return cloneFixture(fixtureGallerySnapshot);
}

export function getFixtureHomeSnapshot(): HomeSnapshot {
  return cloneFixture(fixtureHomeSnapshot);
}

function isoToUnixSeconds(iso: string | null) {
  if (!iso) {
    return 0;
  }

  return Math.floor(new Date(iso).getTime() / 1000);
}

export function getFixtureAgentTasks(options?: { agent?: string | null; limit?: number | null }) {
  const agent = options?.agent?.trim() || null;
  const limit = options?.limit ?? null;
  const tasks = fixtureWorkforce.tasks
    .filter((task) => (agent ? task.agentId === agent : true))
    .map((task) => ({
      id: task.id,
      agent: task.agentId,
      prompt: task.prompt,
      priority: task.priority,
      status: task.status,
      result: task.result ?? "",
      error: task.error ?? "",
      created_at: isoToUnixSeconds(task.createdAt),
      started_at: isoToUnixSeconds(task.startedAt),
      completed_at: isoToUnixSeconds(task.completedAt),
      metadata: {
        project_id: task.projectId,
        plan_id: task.planId,
        requires_approval: task.requiresApproval,
        rationale: task.rationale,
      },
      parent_task_id: task.parentTaskId ?? "",
      description: task.prompt,
      title: task.prompt,
    }));

  return cloneFixture(limit ? tasks.slice(0, limit) : tasks);
}

export function getFixtureAgentActivity(options?: { agent?: string | null; limit?: number | null }) {
  const agent = options?.agent?.trim() || null;
  const limit = options?.limit ?? null;
  const activity = fixtureHistorySnapshot.activity
    .filter((item) => (agent ? item.agentId === agent : true))
    .map((item) => ({
      id: item.id,
      agent: item.agentId,
      source: item.agentId,
      action_type: item.actionType,
      action: item.actionType,
      input_summary: item.inputSummary,
      summary: item.inputSummary,
      output_summary: item.outputSummary,
      detail: item.outputSummary,
      timestamp: isoToUnixSeconds(item.timestamp),
      status: item.status,
      href: item.href,
      related_task_id: item.relatedTaskId,
      related_thread_id: item.relatedThreadId,
    }));

  return cloneFixture(limit ? activity.slice(0, limit) : activity);
}

export function getFixtureAgentOutputs() {
  return cloneFixture(
    fixtureHistorySnapshot.outputs.map((output) => ({
      id: output.id,
      path: output.path,
      file_name: output.fileName,
      category: output.category,
      size_bytes: output.sizeBytes,
      modified: isoToUnixSeconds(output.modifiedAt),
      project_id: output.projectId,
      related_task_id: output.relatedTaskId,
      preview_available: output.previewAvailable,
      href: output.href,
    }))
  );
}

export function getFixtureAgentPatterns(options?: { agent?: string | null }) {
  const agent = options?.agent?.trim() || null;
  const report = fixtureIntelligenceSnapshot.report;
  const patterns = (report?.patterns ?? [])
    .filter((pattern) => (agent ? pattern.agentId === agent : true))
    .map((pattern) => ({
      type: pattern.type,
      severity: pattern.severity,
      agent: pattern.agentId,
      count: pattern.count,
      success_rate: undefined,
      thumbs_up: undefined,
      thumbs_down: undefined,
      runs: undefined,
    }));

  return cloneFixture({
    patterns,
    recommendations: report?.recommendations ?? [],
    generated_at: fixtureIntelligenceSnapshot.generatedAt,
  });
}
