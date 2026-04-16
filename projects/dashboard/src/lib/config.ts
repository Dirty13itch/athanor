import type { LensId } from "@/lib/lens";
import dashboardOperatorSurfaces from "@/generated/operator-surfaces.json";

export type ServiceCategory =
  | "inference"
  | "observability"
  | "media"
  | "experience"
  | "platform"
  | "knowledge"
  | "home";

export interface DashboardEndpoint {
  url: string;
  token?: string;
  headers?: Record<string, string>;
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
  probeTimeoutMs?: number;
}

export interface ExternalTool extends DashboardEndpoint {
  id: string;
  label: string;
  description: string;
  canonicalUrl: string;
  runtimeUrl: string;
  node: string;
  category: string;
  operatorRole: string;
  status: string;
  canonicalState: "reachable" | "unreachable" | "http_error" | "not_probed";
  canonicalDetail?: string | null;
  runtimeState: "reachable" | "unreachable" | "http_error" | "not_probed";
  runtimeDetail?: string | null;
}

type ExternalToolState = ExternalTool["runtimeState"];

export interface QuickLink extends DashboardEndpoint {
  name: string;
  node: string;
  category: string;
}

export interface CommandCenterFrontDoor {
  id: string;
  label: string;
  canonicalUrl: string;
  runtimeUrl: string;
  node: string;
  status: string;
  deploymentMode: string;
  targetDeploymentMode: string;
  description: string;
}

export interface ClusterNode {
  id: string;
  name: string;
  ip: string;
  role: string;
}

export interface GrafanaDashboard extends DashboardEndpoint {
  id: string;
  label: string;
  description: string;
}

export interface ProjectRegistryEntry {
  id: string;
  name: string;
  headline: string;
  status: string;
  kind: "core" | "tenant" | "domain" | "scaffold";
  firstClass: boolean;
  lens: LensId;
  primaryRoute: string;
  externalUrl: string | null;
  operators: string[];
}

export interface DashboardConfig {
  prometheus: DashboardEndpoint;
  grafana: DashboardEndpoint;
  agentServer: DashboardEndpoint;
  litellm: DashboardEndpoint;
  comfyui: DashboardEndpoint;
  openWebUi: DashboardEndpoint;
  vaultOpenWebUi: DashboardEndpoint;
  eoq: DashboardEndpoint;
  stash: DashboardEndpoint;
  speaches: DashboardEndpoint;
  langfuse: { url: string; publicKey: string; secretKey: string };
  qdrant: DashboardEndpoint;
  neo4j: DashboardEndpoint;
  homeAssistant: DashboardEndpoint;
  sonarr: DashboardEndpoint;
  radarr: DashboardEndpoint;
  tautulli: DashboardEndpoint;
  plex: DashboardEndpoint;
  prowlarr: DashboardEndpoint;
  sabnzbd: DashboardEndpoint;
  inferenceBackends: InferenceBackend[];
  services: MonitoredService[];
  nodes: ClusterNode[];
  frontDoor: CommandCenterFrontDoor;
  externalTools: ExternalTool[];
  quickLinks: QuickLink[];
  projectRegistry: ProjectRegistryEntry[];
  grafanaDashboards: GrafanaDashboard[];
  gpuWorkloads: Record<string, Record<number, string>>;
}

function env(key: string, fallback: string): string {
  const value = process.env[key]?.trim();
  return value ? value.replace(/\/+$/, "") : fallback;
}

function normalizeExternalToolState(value: string): ExternalToolState {
  switch (value) {
    case "reachable":
    case "unreachable":
    case "http_error":
    case "not_probed":
      return value;
    default:
      return "not_probed";
  }
}

function hostEnv(key: string, fallback: string): string {
  return process.env[key]?.trim() || fallback;
}

export function joinUrl(base: string, path: string): string {
  const normalizedBase = base.replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

const foundryHost = hostEnv("ATHANOR_NODE1_HOST", "192.168.1.244");
const workshopHost = hostEnv("ATHANOR_NODE2_HOST", "192.168.1.225");
const vaultHost = hostEnv("ATHANOR_VAULT_HOST", "192.168.1.203");
const devHost = hostEnv("ATHANOR_DEV_HOST", "192.168.1.189");
const workshopLinkHost = hostEnv("ATHANOR_WORKSHOP_LINK_HOST", "interface.athanor.local");
const vaultLinkHost = hostEnv("ATHANOR_VAULT_LINK_HOST", "vault.athanor.local");

const prometheusUrl = env(
  "ATHANOR_PROMETHEUS_URL",
  process.env.NEXT_PUBLIC_PROMETHEUS_URL?.trim() || `http://${vaultHost}:9090`
);
const grafanaUrl = env("ATHANOR_GRAFANA_URL", `http://${vaultHost}:3000`);
const agentServerUrl = env("ATHANOR_AGENT_SERVER_URL", `http://${foundryHost}:9000`);
const agentServerToken = process.env.ATHANOR_AGENT_API_TOKEN?.trim() || "";
const litellmUrl = env("ATHANOR_LITELLM_URL", `http://${vaultHost}:4000`);
const foundryCoordinatorUrl = env("ATHANOR_VLLM_COORDINATOR_URL", `http://${foundryHost}:8000`);
const foundryCoderUrl = env("ATHANOR_VLLM_CODER_URL", `http://${foundryHost}:8100`);
const devEmbeddingUrl = env("ATHANOR_VLLM_EMBEDDING_URL", `http://${devHost}:8001`);
const devRerankerUrl = env("ATHANOR_VLLM_RERANKER_URL", `http://${devHost}:8003`);
const comfyUiUrl = env("ATHANOR_COMFYUI_URL", `http://${workshopHost}:8188`);
const openWebUiUrl = env("ATHANOR_OPEN_WEBUI_URL", `http://${workshopHost}:3000`);
const vaultOpenWebUiUrl = env("ATHANOR_VAULT_OPEN_WEBUI_URL", `http://${vaultHost}:3090`);
const eoqUrl = env("ATHANOR_EOQ_URL", `http://${workshopHost}:3002`);
const sonarrUrl = env("ATHANOR_SONARR_URL", `http://${vaultHost}:8989`);
const radarrUrl = env("ATHANOR_RADARR_URL", `http://${vaultHost}:7878`);
const tautulliUrl = env("ATHANOR_TAUTULLI_URL", `http://${vaultHost}:8181`);
const plexUrl = env("ATHANOR_PLEX_URL", `http://${vaultHost}:32400`);
const stashUrl = env("ATHANOR_STASH_URL", `http://${vaultHost}:9999`);
const prowlarrUrl = env("ATHANOR_PROWLARR_URL", `http://${vaultHost}:9696`);
const sabnzbdUrl = env("ATHANOR_SABNZBD_URL", `http://${vaultHost}:8080`);
const homeAssistantUrl = env("ATHANOR_HOME_ASSISTANT_URL", `http://${vaultHost}:8123`);
const homeAssistantToken =
  process.env.ATHANOR_HOME_ASSISTANT_TOKEN?.trim() ||
  process.env.ATHANOR_HA_TOKEN?.trim() ||
  "";
const qdrantUrl = env("ATHANOR_QDRANT_URL", `http://${vaultHost}:6333`);
const neo4jUrl = env("ATHANOR_NEO4J_URL", `http://${vaultHost}:7474`);
const speachesUrl = env("ATHANOR_SPEACHES_URL", `http://${foundryHost}:8200`);
const langfuseUrl = env("ATHANOR_LANGFUSE_URL", `http://${vaultHost}:3030`);
const langfusePublicKey = process.env.ATHANOR_LANGFUSE_PUBLIC_KEY?.trim() || "pk-lf-athanor";
const langfuseSecretKey = process.env.ATHANOR_LANGFUSE_SECRET_KEY?.trim() || "sk-lf-athanor";
const commandCenterLinkUrl = env("ATHANOR_COMMAND_CENTER_URL", "https://athanor.local");
const grafanaLinkUrl = env("ATHANOR_GRAFANA_LINK_URL", `http://${vaultLinkHost}:3000/`);
const prometheusLinkUrl = env("ATHANOR_PROMETHEUS_LINK_URL", `http://${vaultLinkHost}:9090/`);
const comfyUiLinkUrl = env("ATHANOR_COMFYUI_LINK_URL", `http://${workshopLinkHost}:8188/`);
const workshopOpenWebUiLinkUrl = env("ATHANOR_WORKSHOP_OPEN_WEBUI_LINK_URL", `http://${workshopLinkHost}:3000/`);
const vaultOpenWebUiLinkUrl = env("ATHANOR_VAULT_OPEN_WEBUI_LINK_URL", `http://${vaultLinkHost}:3090/`);
const homeAssistantLinkUrl = env("ATHANOR_HOME_ASSISTANT_LINK_URL", `http://${vaultLinkHost}:8123/`);
const plexLinkUrl = env("ATHANOR_PLEX_LINK_URL", `http://${vaultLinkHost}:32400/web`);
const eoqLinkUrl = env("ATHANOR_EOQ_LINK_URL", `http://${workshopLinkHost}:3002/`);
const ulrichLinkUrl = env("ATHANOR_ULRICH_LINK_URL", `http://${workshopLinkHost}:3003/`);
const sonarrLinkUrl = env("ATHANOR_SONARR_LINK_URL", `http://${vaultLinkHost}:8989/`);
const radarrLinkUrl = env("ATHANOR_RADARR_LINK_URL", `http://${vaultLinkHost}:7878/`);
const prowlarrLinkUrl = env("ATHANOR_PROWLARR_LINK_URL", `http://${vaultLinkHost}:9696/`);
const sabnzbdLinkUrl = env("ATHANOR_SABNZBD_LINK_URL", `http://${vaultLinkHost}:8080/`);
const stashLinkUrl = env("ATHANOR_STASH_LINK_URL", `http://${vaultLinkHost}:9999/`);

const frontDoor: CommandCenterFrontDoor = {
  id: dashboardOperatorSurfaces.frontDoor.id,
  label: dashboardOperatorSurfaces.frontDoor.label,
  canonicalUrl: dashboardOperatorSurfaces.frontDoor.canonicalUrl,
  runtimeUrl: dashboardOperatorSurfaces.frontDoor.runtimeUrl,
  node: dashboardOperatorSurfaces.frontDoor.node,
  status: dashboardOperatorSurfaces.frontDoor.status,
  deploymentMode: dashboardOperatorSurfaces.frontDoor.deploymentMode,
  targetDeploymentMode: dashboardOperatorSurfaces.frontDoor.targetDeploymentMode,
  description: dashboardOperatorSurfaces.frontDoor.description,
};

const launchpadExternalTools: ExternalTool[] = dashboardOperatorSurfaces.externalTools.map((tool) => ({
  id: tool.id,
  label: tool.label,
  description: tool.description,
  url: tool.url,
  canonicalUrl: tool.canonicalUrl,
  runtimeUrl: tool.runtimeUrl,
  node: tool.node,
  category: tool.category,
  operatorRole: tool.operatorRole,
  status: tool.status,
  canonicalState: normalizeExternalToolState(tool.canonicalState),
  canonicalDetail: tool.canonicalDetail ?? null,
  runtimeState: normalizeExternalToolState(tool.runtimeState),
  runtimeDetail: tool.runtimeDetail ?? null,
}));

const launchpadQuickLinks: QuickLink[] = dashboardOperatorSurfaces.quickLinks.map((link) => ({
  name: link.name,
  url: link.url,
  node: link.node,
  category: link.category,
}));

const legacyChatTargetAliases: Record<string, string> = {
  "node1-vllm": "foundry-coordinator",
  "node1-vllm-embedding": "dev-embedding",
  "foundry-utility": "foundry-coder",
};

const legacyInferenceBackends: InferenceBackend[] = [
  {
    id: "foundry-coordinator",
    name: "Foundry Coordinator",
    nodeId: "node1",
    description:
      "Legacy secondary reasoning lane retained only for compatibility-target resolution; not part of the active operator-facing backend catalog.",
    primaryModel: "/models/Qwen3.5-27B-FP8",
    url: foundryCoordinatorUrl,
  },
];

export const config = {
  prometheus: {
    url: prometheusUrl,
  },
  grafana: {
    url: grafanaUrl,
  },
  agentServer: {
    url: agentServerUrl,
    token: agentServerToken,
  },
  litellm: {
    url: litellmUrl,
  },
  comfyui: {
    url: comfyUiUrl,
  },
  openWebUi: {
    url: openWebUiUrl,
  },
  vaultOpenWebUi: {
    url: vaultOpenWebUiUrl,
  },
  eoq: {
    url: eoqUrl,
  },
  stash: {
    url: stashUrl,
  },
  speaches: {
    url: speachesUrl,
  },
  langfuse: {
    url: langfuseUrl,
    publicKey: langfusePublicKey,
    secretKey: langfuseSecretKey,
  },
  qdrant: {
    url: qdrantUrl,
  },
  neo4j: {
    url: neo4jUrl,
  },
  homeAssistant: {
    url: homeAssistantUrl,
  },
  sonarr: {
    url: sonarrUrl,
  },
  radarr: {
    url: radarrUrl,
  },
  tautulli: {
    url: tautulliUrl,
  },
  plex: {
    url: plexUrl,
  },
  prowlarr: {
    url: prowlarrUrl,
  },
  sabnzbd: {
    url: sabnzbdUrl,
  },
  inferenceBackends: [
    {
      id: "litellm-proxy",
      name: "LiteLLM Proxy",
      nodeId: "vault",
      description: "Canonical routing layer for aliases, embeddings, and shared reasoning access.",
      primaryModel: "Router",
      url: litellmUrl,
    },
    {
      id: "foundry-coder",
      name: "Foundry Coder",
      nodeId: "node1",
      description: "Dedicated dolphin coder runtime for autonomous implementation, patching, and code-heavy tasks.",
      primaryModel: "dolphin3-r1-24b",
      url: foundryCoderUrl,
    },
    {
      id: "dev-embedding",
      name: "DEV Embedding",
      nodeId: "dev",
      description: "Canonical embedding runtime for retrieval and knowledge indexing.",
      primaryModel: "qwen3-embed-8b",
      url: devEmbeddingUrl,
    },
    {
      id: "dev-reranker",
      name: "DEV Reranker",
      nodeId: "dev",
      description: "Retrieval reranker runtime for higher-precision memory and search results.",
      primaryModel: "Qwen3-Reranker-0.6B",
      url: devRerankerUrl,
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
      description: "Central alias routing and model auth edge.",
    },
    {
      id: "foundry-coder",
      name: "Foundry Coder",
      url: joinUrl(foundryCoderUrl, "/v1/models"),
      nodeId: "node1",
      node: "Foundry",
      category: "inference",
      description: "Autonomous dolphin coding runtime on the 4090 lane.",
    },
    {
      id: "dev-embedding",
      name: "DEV Embedding",
      url: joinUrl(devEmbeddingUrl, "/v1/models"),
      nodeId: "dev",
      node: "DEV",
      category: "knowledge",
      description: "Embedding runtime for retrieval, indexing, and semantic search.",
    },
    {
      id: "dev-reranker",
      name: "DEV Reranker",
      url: joinUrl(devRerankerUrl, "/v1/models"),
      nodeId: "dev",
      node: "DEV",
      category: "knowledge",
      description: "Reranker runtime for retrieval precision.",
    },
      {
        id: "agent-server",
        name: "Agent Server",
        url: joinUrl(agentServerUrl, "/health"),
        nodeId: "node1",
        node: "Foundry",
        category: "platform",
        description: "FastAPI runtime for the Athanor workforce and task APIs.",
        probeTimeoutMs: 10000,
      },
    {
      id: "qdrant",
      name: "Qdrant",
      url: joinUrl(qdrantUrl, "/collections"),
      nodeId: "vault",
      node: "VAULT",
      category: "knowledge",
      description: "Vector memory and retrieval store.",
    },
    {
      id: "neo4j",
      name: "Neo4j",
      url: neo4jUrl,
      nodeId: "vault",
      node: "VAULT",
      category: "knowledge",
      description: "Graph memory and relationship store.",
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
      id: "foundry-node-exporter",
      name: "Node Exporter (Foundry)",
      url: `http://${foundryHost}:9100/metrics`,
      nodeId: "node1",
      node: "Foundry",
      category: "observability",
      description: "Host metrics for Foundry.",
    },
    {
      id: "workshop-node-exporter",
      name: "Node Exporter (Workshop)",
      url: `http://${workshopHost}:9100/metrics`,
      nodeId: "node2",
      node: "Workshop",
      category: "observability",
      description: "Host metrics for Workshop.",
    },
    {
      id: "vault-node-exporter",
      name: "Node Exporter (VAULT)",
      url: `http://${vaultHost}:9100/metrics`,
      nodeId: "vault",
      node: "VAULT",
      category: "observability",
      description: "Host metrics for VAULT.",
    },
    {
      id: "foundry-dcgm-exporter",
      name: "DCGM Exporter (Foundry)",
      url: `http://${foundryHost}:9400/metrics`,
      nodeId: "node1",
      node: "Foundry",
      category: "observability",
      description: "GPU telemetry exporter for Foundry.",
    },
    {
      id: "workshop-dcgm-exporter",
      name: "DCGM Exporter (Workshop)",
      url: `http://${workshopHost}:9400/metrics`,
      nodeId: "node2",
      node: "Workshop",
      category: "observability",
      description: "GPU telemetry exporter for Workshop.",
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
      id: "workshop-open-webui",
      name: "Workshop Open WebUI",
      url: openWebUiUrl,
      nodeId: "node2",
      node: "Workshop",
      category: "experience",
      description: "Direct local chat surface for raw model access.",
    },
    {
      id: "vault-open-webui",
      name: "VAULT Open WebUI",
      url: vaultOpenWebUiUrl,
      nodeId: "vault",
      node: "VAULT",
      category: "experience",
      description: "LiteLLM-routed chat surface for alias-based access.",
    },
    {
      id: "eoq",
      name: "Empire of Broken Queens",
      url: eoqUrl,
      nodeId: "node2",
      node: "Workshop",
      category: "experience",
      description: "First-class tenant app proving the Athanor project platform.",
    },
    {
      id: "home-assistant",
      name: "Home Assistant",
      url: joinUrl(homeAssistantUrl, "/api/"),
      headers: homeAssistantToken ? { Authorization: `Bearer ${homeAssistantToken}` } : undefined,
      nodeId: "vault",
      node: "VAULT",
      category: "home",
      description: "Smart-home control plane and automation state.",
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
      id: "plex",
      name: "Plex",
      url: joinUrl(plexUrl, "/identity"),
      nodeId: "vault",
      node: "VAULT",
      category: "media",
      description: "Primary media serving platform.",
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
      id: "prowlarr",
      name: "Prowlarr",
      url: prowlarrUrl,
      nodeId: "vault",
      node: "VAULT",
      category: "media",
      description: "Indexer and feed aggregation surface.",
    },
    {
      id: "sabnzbd",
      name: "SABnzbd",
      url: sabnzbdUrl,
      nodeId: "vault",
      node: "VAULT",
      category: "media",
      description: "Downloader and queue management surface.",
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
  ],
  nodes: [
    { id: "node1", name: "Foundry", ip: foundryHost, role: "Coordinator inference and agent execution" },
    { id: "node2", name: "Workshop", ip: workshopHost, role: "Worker inference, creative runtimes, and UI" },
    { id: "vault", name: "VAULT", ip: vaultHost, role: "Routing, memory, media, home, and observability" },
    { id: "dev", name: "DEV", ip: devHost, role: "Ops workstation and retrieval runtimes" },
  ],
  frontDoor,
  externalTools: launchpadExternalTools,
  quickLinks: launchpadQuickLinks,
  projectRegistry: [
    {
      id: "athanor",
      name: "Athanor",
      headline: "Core operating environment for system state, workforce orchestration, and operator judgment.",
      status: "active",
      kind: "core",
      firstClass: true,
      lens: "system",
      primaryRoute: "/",
      externalUrl: null,
      operators: ["Shaun", "Claude"],
    },
    {
      id: "eoq",
      name: "Empire of Broken Queens",
      headline: "First first-class tenant for creative generation, dialogue, and cinematic interaction.",
      status: "active",
      kind: "tenant",
      firstClass: true,
      lens: "eoq",
      primaryRoute: "/backlog?project=eoq",
      externalUrl: eoqLinkUrl,
      operators: ["Claude", "creative-agent", "coding-agent"],
    },
    {
      id: "kindred",
      name: "Kindred",
      headline: "Scaffolded future tenant in concept and research mode.",
      status: "scaffolded",
      kind: "scaffold",
      firstClass: false,
      lens: "default",
      primaryRoute: "/backlog?project=kindred",
      externalUrl: null,
      operators: ["Claude", "research-agent"],
    },
    {
      id: "ulrich-energy",
      name: "Ulrich Energy",
      headline: "Scaffolded operational tenant for field workflows, reporting, and client-facing energy work.",
      status: "scaffolded",
      kind: "scaffold",
      firstClass: false,
      lens: "default",
      primaryRoute: "/backlog?project=ulrich-energy",
      externalUrl: ulrichLinkUrl,
      operators: ["Claude", "coding-agent", "research-agent"],
    },
    {
      id: "media",
      name: "Media Library",
      headline: "Operational domain project spanning curation, acquisition, and catalog quality.",
      status: "operational",
      kind: "domain",
      firstClass: false,
      lens: "media",
      primaryRoute: "/media",
      externalUrl: plexLinkUrl,
      operators: ["media-agent"],
    },
  ],
  grafanaDashboards: [
    {
      id: "node-exporter-full",
      label: "Node Exporter Full",
      description: "Host-level CPU, memory, disk, and network dashboards.",
      url: joinUrl(grafanaUrl, "/d/rYdddlPWk/node-exporter-full"),
    },
    {
      id: "dcgm-exporter",
      label: "NVIDIA DCGM Exporter",
      description: "GPU fleet telemetry and thermal pressure dashboard.",
      url: joinUrl(grafanaUrl, "/d/Oxed_c6Wz/nvidia-dcgm-exporter-dashboard"),
    },
    {
      id: "athanor-operations",
      label: "Athanor Operations",
      description: "Cluster-wide operational metrics and service health.",
      url: joinUrl(grafanaUrl, "/d/3349e8df-5e19-458f-b663-29c2075b73bf/athanor-operations"),
    },
    {
      id: "athanor-inference",
      label: "Athanor Inference",
      description: "vLLM inference throughput, latency, and token rates.",
      url: joinUrl(grafanaUrl, "/d/625cdba9-8234-4d27-a0ec-f8d49a252ff6/athanor-inference"),
    },
    {
      id: "athanor-service-health",
      label: "Athanor Service Health",
      description: "Service uptime, error rates, and endpoint availability.",
      url: joinUrl(grafanaUrl, "/d/athanor-service-health/athanor-service-health"),
    },
    {
      id: "athanor-agent-activity",
      label: "Athanor Agent Activity",
      description: "Agent task execution, run counts, and scheduling metrics.",
      url: joinUrl(grafanaUrl, "/d/athanor-agent-activity/athanor-agent-activity"),
    },
    {
      id: "vault-server-monitor",
      label: "VAULT Server Monitor",
      description: "Unraid array health, Docker containers, and NVMe status.",
      url: joinUrl(grafanaUrl, "/d/vault-server-monitor/vault-server-monitor"),
    },
  ],
  gpuWorkloads: {
    [foundryHost]: {
      0: "Reasoning / coding coordinator",
      1: "Reasoning / coding coordinator",
      2: "Coder runtime",
      3: "Reasoning / coding coordinator",
      4: "Reasoning / coding coordinator",
    },
    [workshopHost]: {
      0: "Worker inference",
      1: "ComfyUI / Flux / video",
    },
    [devHost]: {
      0: "Embeddings + reranker",
    },
  } as Record<string, Record<number, string>>,
} as const satisfies DashboardConfig;

export function getInferenceBackend(target: string): InferenceBackend | null {
  const normalizedTarget = legacyChatTargetAliases[target] ?? target;
  return (
    config.inferenceBackends.find((backend) => backend.id === normalizedTarget) ??
    legacyInferenceBackends.find((backend) => backend.id === normalizedTarget) ??
    null
  );
}

export function getNodeById(nodeId: string): ClusterNode | null {
  return config.nodes.find((node) => node.id === nodeId) ?? null;
}

export function getServiceById(serviceId: string): MonitoredService | null {
  return config.services.find((service) => service.id === serviceId) ?? null;
}

export function getProjectById(projectId: string): ProjectRegistryEntry | null {
  return config.projectRegistry.find((project) => project.id === projectId) ?? null;
}

export function getGrafanaDashboardById(dashboardId: string): GrafanaDashboard | null {
  return config.grafanaDashboards.find((dashboard) => dashboard.id === dashboardId) ?? null;
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

export function resolveChatModel(target: string | undefined, model: string | undefined): string {
  const normalizedModel = model?.trim();
  const backend = getInferenceBackend(target ?? "");
  if (target === "agent-server") {
    return normalizedModel && normalizedModel !== "default"
      ? normalizedModel
      : "general-assistant";
  }

  if (target === "litellm-proxy") {
    return normalizedModel && normalizedModel !== "default" ? normalizedModel : "reasoning";
  }

  if (normalizedModel && normalizedModel !== "default") {
    if (backend?.primaryModel.startsWith("/models/") && !normalizedModel.startsWith("/models/")) {
      return `/models/${normalizedModel.replace(/^\/+/, "")}`;
    }
    return normalizedModel;
  }

  return backend ? backend.primaryModel : "reasoning";
}

export function getNodeNameFromInstance(instance: string): string {
  return config.nodes.find((node) => instance.includes(node.ip))?.name ?? instance;
}

export function agentServerHeaders(): Record<string, string> {
  const token = config.agentServer.token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}
