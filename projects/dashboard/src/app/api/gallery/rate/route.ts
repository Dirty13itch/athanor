import { NextRequest } from "next/server";

/**
 * POST /api/gallery/rate — Submit a rating for an image.
 *
 * Body: { imageId, rating, approved, flagged, notes? }
 *
 * Currently stores in localStorage on the client side (no agent server route yet).
 * This endpoint validates and echoes back the rating for future agent-server persistence.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { imageId, rating, approved, flagged, notes } = body as {
      imageId: string;
      rating: number;
      approved: boolean;
      flagged: boolean;
      notes?: string;
    };

    if (!imageId || typeof imageId !== "string") {
      return Response.json({ error: "imageId is required" }, { status: 400 });
    }

    if (typeof rating !== "number" || rating < 0 || rating > 5) {
      return Response.json({ error: "rating must be 0-5" }, { status: 400 });
    }

    // TODO: Persist to agent server when POST foundry:9000/v1/gallery/ratings is available
    // const agentUrl = process.env.AGENT_SERVER_URL ?? "http://foundry:9000";
    // const token = process.env.ATHANOR_AGENT_API_TOKEN;
    // await fetch(`${agentUrl}/v1/gallery/ratings`, {
    //   method: "POST",
    //   headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    //   body: JSON.stringify({ imageId, rating, approved, flagged, notes }),
    // });

    return Response.json({
      ok: true,
      imageId,
      rating,
      approved,
      flagged,
      notes: notes ?? null,
      timestamp: new Date().toISOString(),
    });
  } catch (err) {
    return Response.json(
      { error: err instanceof Error ? err.message : "Failed to submit rating" },
      { status: 500 }
    );
  }
}
