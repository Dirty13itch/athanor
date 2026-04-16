import { config } from "@/lib/config";

const REDIS_URL = `http://${process.env.ATHANOR_VAULT_HOST?.trim() || "192.168.1.203"}:6379`;

/**
 * Video cache lookup — checks Redis for pre-generated I2V videos.
 * The creative-agent generates videos autonomously via the work pipeline
 * and stores them in Redis under athanor:eoq:video_inventory:{queenId}:{stage}.
 *
 * GET /api/video-cache?queen=isolde&stage=defiant
 * Returns: { videoUrl, quality, generatedAt } or { videoUrl: null }
 */
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const queen = searchParams.get("queen");
  const stage = searchParams.get("stage") || "defiant";

  if (!queen) {
    return Response.json({ error: "queen parameter required" }, { status: 400 });
  }

  try {
    // Query Redis via the agent server's Redis proxy (avoids direct Redis connection from Next.js)
    const agentUrl = `http://${process.env.ATHANOR_NODE1_HOST?.trim() || "192.168.1.244"}:9000`;
    const resp = await fetch(`${agentUrl}/api/redis/get`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: `athanor:eoq:video_inventory:${queen}:${stage}` }),
    });

    if (!resp.ok) {
      // Fallback: no cache entry found
      return Response.json({ videoUrl: null });
    }

    const data = await resp.json();
    if (!data.value) {
      return Response.json({ videoUrl: null });
    }

    const entry = typeof data.value === "string" ? JSON.parse(data.value) : data.value;

    return Response.json({
      videoUrl: entry.video_url || null,
      quality: entry.quality || "unknown",
      generatedAt: entry.generated_at || null,
    });
  } catch {
    // Cache miss is not an error — just means no pre-generated video
    return Response.json({ videoUrl: null });
  }
}
