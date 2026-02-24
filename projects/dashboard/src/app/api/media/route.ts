import { config } from "@/lib/config";

export async function GET() {
  try {
    const res = await fetch(`${config.agentServer.url}/v1/status/media`, {
      signal: AbortSignal.timeout(10000),
      next: { revalidate: 0 },
    });
    if (!res.ok) {
      return Response.json({ error: "Agent server returned error" }, { status: res.status });
    }
    const data = await res.json();
    return Response.json(data);
  } catch {
    return Response.json({
      plex_activity: {},
      sonarr_queue: [],
      radarr_queue: [],
      tv_upcoming: [],
      movie_upcoming: [],
      tv_library: {},
      movie_library: {},
      watch_history: [],
    });
  }
}
