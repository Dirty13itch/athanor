import { NextResponse } from "next/server";

const AGENT_SERVER = "http://192.168.1.244:9000";

export interface AgentInfo {
  name: string;
  description: string;
  tools: string[];
  status: "online" | "offline";
}

// Agent metadata — describes each agent's purpose and toolset
const AGENT_METADATA: Record<string, { description: string; tools: string[] }> = {
  "general-assistant": {
    description: "System monitoring and infrastructure management. Checks service health, GPU metrics, storage, and vLLM models.",
    tools: ["check_services", "get_gpu_metrics", "get_vllm_models", "get_storage_info"],
  },
  "media-agent": {
    description: "Media stack management. Search and add TV shows (Sonarr), movies (Radarr), and monitor Plex activity (Tautulli).",
    tools: ["search_tv", "add_tv_show", "search_movies", "add_movie", "get_plex_activity", "get_library_stats"],
  },
  "home-agent": {
    description: "Smart home control via Home Assistant. Manage lights, climate, switches, and automations.",
    tools: ["get_entity_state", "control_lights", "control_climate", "search_entities", "list_automations"],
  },
};

export async function GET() {
  try {
    const res = await fetch(`${AGENT_SERVER}/health`, {
      signal: AbortSignal.timeout(5000),
    });

    if (!res.ok) {
      return NextResponse.json({ status: "offline", agents: [] });
    }

    const data = await res.json();
    const agentNames: string[] = data.agents ?? [];

    const agents: AgentInfo[] = agentNames.map((name) => ({
      name,
      description: AGENT_METADATA[name]?.description ?? "No description available.",
      tools: AGENT_METADATA[name]?.tools ?? [],
      status: "online" as const,
    }));

    return NextResponse.json({ status: "online", agents });
  } catch {
    return NextResponse.json({ status: "offline", agents: [] });
  }
}
