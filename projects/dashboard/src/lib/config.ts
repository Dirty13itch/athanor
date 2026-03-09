export type ServiceCategory =
  | "inference"
  | "observability"
  | "media"
  | "experience"
  | "platform";

export interface DashboardEndpoint {
  url: string;
}

export interface LitellmEndpoint extends DashboardEndpoint {
  apiKey: string;
}

export interface InferenceBackend extends DashboardEndpoint {
  id: string;
  name: string;
  nodeId: string;
  description: string;
  primaryModel: string;
}

export interface MonitoredService extends DashboardEndpoint {
  id: string;
  name: string;
  nodeId: string;
  node: string;
  category: ServiceCategory;
  description: string;
}

export interface ExternalTool extends DashboardEndpoint {
  id: string;
  label: string;
  description: string;
}

export interface QuickLink extends DashboardEndpoint {
  name: string;
  node: string;
  category: string;
}

export interface ClusterNode {
  id: string;
  name: string;
  ip: string;
  role: string;
}

export interface DashboardConfig {
  prometheus: DashboardEndpoint;
  grafana: DashboardEndpoint;
  agentServer: DashboardEndpoint;
  comfyui: DashboardEndpoint;
  stash: DashboardEndpoint;
  speaches: DashboardEndpoint;
  litellm: LitellmEndpoint;
  inferenceBackends: InferenceBackend[];
  services: MonitoredService[];
  nodes: ClusterNode[];
  externalTools: ExternalTool[];
  quickLinks: QuickLink[];
  gpuWorkloads: Record<string, Record<number, string>>;
}

function env(key: string, fallback: string): string {
  const value = process.env[key]?.trim();
  return value ? value.replace(/\/+$/, "") : fallback;
}

function hostEnv(key: string, fallback: string): string {
  return process.env[key]?.trim() || fallback;
}

export function joinUrl(base: string, path: string): string {
  const normalizedBase = base.replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

const node1Host = hostEnv("ATHANOR_NODE1_HOST", "192.168.1.244");
const node2Host = hostEnv("ATHANOR_NODE2_HOST", "192.168.1.225");
const vaultHost = hostEnv("ATHANOR_VAULT_HOST", "192.168.1.203");

const prometheusUrl = env(
  "ATHANOR_PROMETHEUS_URL",
  process.env.NEXT_PUBLIC_PROMETHEUS_URL?.trim() || `http://${vaultHost}:9090`
);
const grafanaUrl = env("ATHANOR_GRAFANA_URL", `http://${vaultHost}:3000`);
const agentServerUrl = env("ATHANOR_AGENT_SERVER_URL", `http://${node1Host}:9000`);
const node1VllmUrl = env("ATHANOR_NODE1_VLLM_URL", `http://${node1Host}:8000`);
const node2VllmUrl = env("ATHANOR_NODE2_VLLM_URL", `http://${node2Host}:8000`);
const comfyUiUrl = env("ATHANOR_COMFYUI_URL", `http://${node2Host}:8188`);
const openWebUiUrl = env("ATHANOR_OPEN_WEBUI_URL", `http://${node2Host}:3000`);
const litellmUrl = env("ATHANOR_LITELLM_URL", `http://${vaultHost}:4000`);
const sonarrUrl = env("ATHANOR_SONARR_URL", `http://${vaultHost}:8989`);
const radarrUrl = env("ATHANOR_RADARR_URL", `http://${vaultHost}:7878`);
const tautulliUrl = env("ATHANOR_TAUTULLI_URL", `http://${vaultHost}:8181`);
const plexUrl = env("ATHANOR_PLEX_URL", `http://${vaultHost}:32400`);
const stashUrl = env("ATHANOR_STASH_URL", `http://${vaultHost}:9999`);
const speachesUrl = env("ATHANOR_SPEACHES_URL", `http://${node1Host}:8200`);
const litellmApiKey =
  process.env.ATHANOR_LITELLM_API_KEY?.trim() || "sk-athanor-litellm-2026";

export const config = {
  prometheus: {
    url: prometheusUrl,
  },
  grafana: {
    url: grafanaUrl,
  },
  agentServer: {
    url: agentServerUrl,
  },
  comfyui: {
    url: comfyUiUrl,
  },
  stash: {
    url: stashUrl,
  },
  speaches: {
    url: speachesUrl,
  },
  litellm: {
    url: litellmUrl,
    apiKey: litellmApiKey,
  },
  inferenceBackends: [
    {
      id: "litellm-proxy",
      name: "LiteLLM Proxy",
      nodeId: "vault",
      description: "Unified routing layer for direct inference and embeddings.",
      primaryModel: "Router",
      url: litellmUrl,
    },
    {
      id: "node1-vllm",
      name: "Foundry / Qwen3-32B",
      nodeId: "node1",
      description: "Primary large-model inference runtime.",
      primaryModel: "Qwen3-32B",
      url: node1VllmUrl,
    },
    {
      id: "node2-vllm",
      name: "Workshop / Qwen3-14B",
      nodeId: "node2",
      description: "Secondary inference host for interactive workloads.",
      primaryModel: "Qwen3-14B",
      url: node2VllmUrl,
    },
  ],
  services: [
    {
      id: "litellm-proxy",
      name: "LiteLLM Proxy",
      url: joinUrl(litellmUrl, "/health/readiness"),
      nodeId: "vault",
      node: "VAULT",
      category: "inference",
      description: "Central routing and model proxy.",
    },
    {
      id: "node1-vllm",
      name: "vLLM (Node 1)",
      url: joinUrl(node1VllmUrl, "/v1/models"),
      nodeId: "node1",
      node: "Foundry",
      category: "inference",
      description: "Primary vLLM model runtime.",
    },
    {
      id: "node2-vllm",
      name: "vLLM (Node 2)",
      url: joinUrl(node2VllmUrl, "/v1/models"),
      nodeId: "node2",
      node: "Workshop",
      category: "inference",
      description: "Secondary vLLM model runtime.",
    },
    {
      id: "node1-vllm-embedding",
      name: "vLLM Embedding",
      url: `http://${node1Host}:8001/health`,
      nodeId: "node1",
      node: "Foundry",
      category: "inference",
      description: "Embedding runtime for semantic search and retrieval.",
    },
    {
      id: "agent-server",
      name: "Agent Server",
      url: joinUrl(agentServerUrl, "/health"),
      nodeId: "node1",
      node: "Foundry",
      category: "platform",
      description: "FastAPI runtime for Athanor agents.",
    },
    {
      id: "prometheus",
      name: "Prometheus",
      url: joinUrl(prometheusUrl, "/-/healthy"),
      nodeId: "vault",
      node: "VAULT",
      category: "observability",
      description: "Metric collection and query service.",
    },
    {
      id: "grafana",
      name: "Grafana",
      url: joinUrl(grafanaUrl, "/api/health"),
      nodeId: "vault",
      node: "VAULT",
      category: "observability",
      description: "Dashboards, exploration, and alert views.",
    },
    {
      id: "node1-node-exporter",
      name: "Node Exporter (Node 1)",
      url: `http://${node1Host}:9100/metrics`,
      nodeId: "node1",
      node: "Foundry",
      category: "observability",
      description: "Host metrics for Node 1.",
    },
    {
      id: "node2-node-exporter",
      name: "Node Exporter (Node 2)",
      url: `http://${node2Host}:9100/metrics`,
      nodeId: "node2",
      node: "Workshop",
      category: "observability",
      description: "Host metrics for Node 2.",
    },
    {
      id: "node1-dcgm-exporter",
      name: "DCGM Exporter (Node 1)",
      url: `http://${node1Host}:9400/metrics`,
      nodeId: "node1",
      node: "Foundry",
      category: "observability",
      description: "GPU telemetry exporter for Node 1.",
    },
    {
      id: "node2-dcgm-exporter",
      name: "DCGM Exporter (Node 2)",
      url: `http://${node2Host}:9400/metrics`,
      nodeId: "node2",
      node: "Workshop",
      category: "observability",
      description: "GPU telemetry exporter for Node 2.",
    },
    {
      id: "comfyui",
      name: "ComfyUI",
      url: joinUrl(comfyUiUrl, "/system_stats"),
      nodeId: "node2",
      node: "Workshop",
      category: "experience",
      description: "Creative workflow runtime.",
    },
    {
      id: "open-webui",
      name: "Open WebUI",
      url: openWebUiUrl,
      nodeId: "node2",
      node: "Workshop",
      category: "experience",
      description: "Secondary model interface and experimentation surface.",
    },
    {
      id: "speaches",
      name: "Speaches",
      url: joinUrl(speachesUrl, "/health"),
      nodeId: "node1",
      node: "Foundry",
      category: "platform",
      description: "Speech synthesis service.",
    },
    {
      id: "stash",
      name: "Stash",
      url: stashUrl,
      nodeId: "vault",
      node: "VAULT",
      category: "media",
      description: "Media catalog and organization runtime.",
    },
    {
      id: "sonarr",
      name: "Sonarr",
      url: joinUrl(sonarrUrl, "/ping"),
      nodeId: "vault",
      node: "VAULT",
      category: "media",
      description: "TV acquisition and automation.",
    },
    {
      id: "radarr",
      name: "Radarr",
      url: joinUrl(radarrUrl, "/ping"),
      nodeId: "vault",
      node: "VAULT",
      category: "media",
      description: "Movie acquisition and automation.",
    },
    {
      id: "tautulli",
      name: "Tautulli",
      url: tautulliUrl,
      nodeId: "vault",
      node: "VAULT",
      category: "media",
      description: "Plex usage analytics.",
    },
    {
      id: "plex",
      name: "Plex",
      url: joinUrl(plexUrl, "/identity"),
      nodeId: "vault",
      node: "VAULT",
      category: "media",
      description: "Primary media serving platform.",
    },
  ],
  nodes: [
    { id: "node1", name: "Foundry", ip: node1Host, role: "AI inference + agents" },
    { id: "node2", name: "Workshop", ip: node2Host, role: "Creative + interface" },
    { id: "vault", name: "VAULT", ip: vaultHost, role: "Storage + media + monitoring" },
  ],
  externalTools: [
    {
      id: "grafana",
      label: "Grafana",
      description: "Dashboards, alerting, and drill-downs.",
      url: grafanaUrl,
    },
    {
      id: "prometheus",
      label: "Prometheus",
      description: "Raw metrics and PromQL exploration.",
      url: prometheusUrl,
    },
    {
      id: "agent-server",
      label: "Agent Server",
      description: "Live agent metadata and health endpoint.",
      url: agentServerUrl,
    },
    {
      id: "comfyui",
      label: "ComfyUI",
      description: "Creative workflows and generation queues.",
      url: comfyUiUrl,
    },
    {
      id: "open-webui",
      label: "Open WebUI",
      description: "Interactive multi-model chat surface.",
      url: openWebUiUrl,
    },
    {
      id: "plex",
      label: "Plex",
      description: "Media library and playback control.",
      url: joinUrl(plexUrl, "/web"),
    },
  ],
  quickLinks: [
    { name: "Grafana", url: grafanaUrl, node: "VAULT", category: "monitoring" },
    { name: "Prometheus", url: prometheusUrl, node: "VAULT", category: "monitoring" },
    { name: "ComfyUI", url: comfyUiUrl, node: "Workshop", category: "creative" },
    { name: "Open WebUI", url: openWebUiUrl, node: "Workshop", category: "ai" },
    { name: "Plex", url: joinUrl(plexUrl, "/web"), node: "VAULT", category: "media" },
    { name: "Sonarr", url: sonarrUrl, node: "VAULT", category: "media" },
    { name: "Radarr", url: radarrUrl, node: "VAULT", category: "media" },
    { name: "Stash", url: stashUrl, node: "VAULT", category: "media" },
  ],
  gpuWorkloads: {
    [node1Host]: {
      0: "Qwen3-32B",
      1: "Qwen3-32B",
      2: "Utility / overflow",
      3: "Qwen3-32B",
      4: "Qwen3-32B",
    },
    [node2Host]: {
      0: "Qwen3-14B",
      1: "ComfyUI / Flux",
    },
  } as Record<string, Record<number, string>>,
} as const satisfies DashboardConfig;

export function getInferenceBackend(target: string): InferenceBackend | null {
  return config.inferenceBackends.find((backend) => backend.id === target) ?? null;
}

export function getNodeById(nodeId: string): ClusterNode | null {
  return config.nodes.find((node) => node.id === nodeId) ?? null;
}

export function getServiceById(serviceId: string): MonitoredService | null {
  return config.services.find((service) => service.id === serviceId) ?? null;
}

export function resolveChatTarget(target: string | undefined): DashboardEndpoint | null {
  if (!target) {
    return null;
  }

  if (target === "agent-server") {
    return config.agentServer;
  }

  return getInferenceBackend(target);
}

export function getNodeNameFromInstance(instance: string): string {
  return config.nodes.find((node) => instance.includes(node.ip))?.name ?? instance;
}
