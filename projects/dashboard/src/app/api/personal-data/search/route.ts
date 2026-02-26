import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

const QDRANT_URL = "http://192.168.1.244:6333";
const COLLECTION = "personal_data";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const query = body.query as string;
    const limit = Math.min(body.limit ?? 20, 50);

    if (!query || typeof query !== "string" || query.trim().length === 0) {
      return NextResponse.json({ error: "query is required" }, { status: 400 });
    }

    // Get embedding from LiteLLM
    const embeddingRes = await fetch(`${config.litellm.url}/v1/embeddings`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${config.litellm.apiKey}`,
      },
      body: JSON.stringify({
        model: "embedding",
        input: query.trim(),
      }),
      signal: AbortSignal.timeout(10000),
    });

    if (!embeddingRes.ok) {
      const errText = await embeddingRes.text().catch(() => "unknown");
      return NextResponse.json(
        { error: `Embedding request failed: ${embeddingRes.status}`, detail: errText },
        { status: 502 }
      );
    }

    const embeddingData = await embeddingRes.json();
    const vector = embeddingData.data?.[0]?.embedding;

    if (!vector || !Array.isArray(vector)) {
      return NextResponse.json(
        { error: "Invalid embedding response" },
        { status: 502 }
      );
    }

    // Search Qdrant
    const searchRes = await fetch(`${QDRANT_URL}/collections/${COLLECTION}/points/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        vector,
        limit,
        with_payload: true,
        with_vector: false,
      }),
      signal: AbortSignal.timeout(5000),
    });

    if (!searchRes.ok) {
      return NextResponse.json(
        { error: `Qdrant search failed: ${searchRes.status}` },
        { status: 502 }
      );
    }

    const searchData = await searchRes.json();
    const results = (searchData.result ?? []).map(
      (point: { id: string | number; score: number; payload: Record<string, unknown> }) => ({
        id: point.id,
        score: point.score,
        ...point.payload,
      })
    );

    return NextResponse.json({ results, count: results.length });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
