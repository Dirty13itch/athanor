import { config } from "@/lib/config";

export async function GET() {
  try {
    const res = await fetch(`${config.stash.url}/graphql`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: `{
          stats {
            scene_count
            image_count
            gallery_count
            performer_count
            studio_count
            tag_count
            total_o_count
            total_play_duration
            total_play_count
            scenes_duration
            scenes_size
          }
        }`,
      }),
      signal: AbortSignal.timeout(5000),
    });

    if (!res.ok) {
      return Response.json({ stats: null });
    }

    const data = await res.json();
    return Response.json({ stats: data.data?.stats ?? null });
  } catch {
    return Response.json({ stats: null });
  }
}
