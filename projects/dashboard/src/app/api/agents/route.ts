import { NextResponse } from "next/server";
import { config } from "@/lib/config";

// Fallback metadata — used when /v1/agents endpoint is unavailable
// (e.g., agent server running older version without the endpoint)
const FALLBACK_METADATA: Record<
  string,
  { name: string; description: string; tools: string[]; icon: string }
> = {
  "general-assistant": {
    name: "General Assistant",
    description:
      "System monitoring, GPU metrics, storage info, and infrastructure queries",
    tools: [
      "check_services",
      "get_gpu_metrics",
      "get_vllm_models",
      "get_storage_info",
    ],
    icon: "terminal",
  },
  "media-agent": {
    name: "Media Agent",
    description:
      "Search and add TV shows & movies, check downloads, Plex activity",
    tools: [
      "search_tv_shows",
      "get_tv_calendar",
      "get_tv_queue",
      "get_tv_library",
      "add_tv_show",
      "search_movies",
      "get_movie_calendar",
      "get_movie_queue",
      "get_movie_library",
      "add_movie",
      "get_plex_activity",
      "get_watch_history",
      "get_plex_libraries",
    ],
    icon: "film",
  },
  "home-agent": {
    name: "Home Agent",
    description:
      "Smart home control — lights, climate, automations via Home Assistant",
    tools: [
      "get_ha_states",
      "get_entity_state",
      "find_entities",
      "call_ha_service",
      "set_light_brightness",
      "set_climate_temperature",
      "list_automations",
      "trigger_automation",
    ],
    icon: "home",
  },
};

export async function GET() {
  // Try the new /v1/agents endpoint first (dynamic tool introspection)
  try {
    const res = await fetch(`${config.agentServer.url}/v1/agents`, {
      next: { revalidate: 30 },
    });

    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
  } catch {
    // /v1/agents not available — fall through to health-based approach
  }

  // Fallback: use /health + hardcoded metadata
  try {
    const res = await fetch(`${config.agentServer.url}/health`, {
      next: { revalidate: 30 },
    });

    if (!res.ok) {
      throw new Error(`Agent server returned ${res.status}`);
    }

    const data = await res.json();
    const liveAgents: string[] = data.agents ?? [];

    const agents = Object.entries(FALLBACK_METADATA).map(([id, meta]) => ({
      id,
      ...meta,
      status: liveAgents.includes(id) ? "ready" : "unavailable",
    }));

    return NextResponse.json({ agents });
  } catch {
    // Agent server unreachable — return all as unavailable
    const agents = Object.entries(FALLBACK_METADATA).map(([id, meta]) => ({
      id,
      ...meta,
      status: "unavailable",
    }));

    return NextResponse.json({ agents });
  }
}
