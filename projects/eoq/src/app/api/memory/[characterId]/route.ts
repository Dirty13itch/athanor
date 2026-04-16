import { config } from "@/lib/config";
import { EOQ_FIXTURE_MODE } from "@/lib/fixture-mode";
import { getFixtureMemories } from "@/lib/fixtures";
import {
  COLLECTION,
  getEmbedding,
  ensureCollection,
  recencyWeight,
} from "../route";

/**
 * Character-specific memory retrieval.
 *
 * GET /api/memory/[characterId]?query=...&limit=5
 *   Returns memories filtered by characterId, sorted by adjusted relevance.
 *
 * GET /api/memory/[characterId]?summary=1
 *   Returns a relationship summary (total interactions, sentiment, strength).
 */

interface QdrantPoint {
  id: string;
  score: number;
  payload: Record<string, unknown>;
}

export async function GET(
  req: Request,
  { params }: { params: Promise<{ characterId: string }> },
) {
  const { characterId } = await params;
  const url = new URL(req.url);
  const isSummary = url.searchParams.get("summary") === "1";

  if (isSummary) {
    return handleSummary(characterId);
  }

  return handleQuery(characterId, url);
}

// ---------------------------------------------------------------------------
// Query-based retrieval with recency decay
// ---------------------------------------------------------------------------

async function handleQuery(characterId: string, url: URL) {
  const query = url.searchParams.get("query") ?? "";
  const limit = parseInt(url.searchParams.get("limit") ?? "5");

  if (!query) {
    return Response.json(
      { error: "query parameter is required" },
      { status: 400 },
    );
  }

  // ---- Fixture mode ----
  if (EOQ_FIXTURE_MODE) {
    const memories = getFixtureMemories(characterId)
      .slice(0, limit)
      .map((memory, index) => ({
        text: memory.text,
        timestamp: memory.timestamp,
        score: 0.92 - index * 0.08,
        adjustedScore: (0.92 - index * 0.08) * recencyWeight(memory.timestamp),
        importance: (memory.metadata as Record<string, unknown>)?.importance ?? 2,
        memoryType: (memory.metadata as Record<string, unknown>)?.memoryType ?? "interaction",
        metadata: memory.metadata ?? {},
      }));
    return Response.json({ memories });
  }

  // ---- Embed the query ----
  const embedding = await getEmbedding(query);
  if (!embedding) {
    return Response.json({ memories: [] });
  }

  // ---- Search Qdrant ----
  await ensureCollection();

  // Over-fetch so we can re-rank with recency decay
  const fetchLimit = Math.min(limit * 3, 30);

  const resp = await fetch(
    `${config.qdrantUrl}/collections/${COLLECTION}/points/query`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: embedding,
        limit: fetchLimit,
        filter: {
          must: [
            { key: "character_id", match: { value: characterId } },
          ],
        },
        with_payload: true,
      }),
    },
  );

  if (!resp.ok) {
    return Response.json({ memories: [] });
  }

  const data = await resp.json();
  const points: QdrantPoint[] = data.result?.points ?? [];

  // Re-rank: adjustedScore = similarity * recencyWeight * importanceBoost
  const scored = points
    .map((p) => {
      const timestamp = typeof p.payload.timestamp === "number" ? p.payload.timestamp : Date.now();
      const importance = typeof p.payload.importance === "number" ? p.payload.importance : 2;
      const importanceBoost = 0.7 + (importance / 5) * 0.6; // 0.9 to 1.3
      const recency = recencyWeight(timestamp);
      const adjustedScore = p.score * recency * importanceBoost;

      return {
        text: p.payload.text as string,
        timestamp,
        score: p.score,
        adjustedScore,
        importance,
        memoryType: (p.payload.memory_type as string) ?? "interaction",
        metadata: p.payload,
      };
    })
    .filter((m) => m.score > 0.2) // Floor: drop irrelevant noise
    .sort((a, b) => b.adjustedScore - a.adjustedScore)
    .slice(0, limit);

  return Response.json({ memories: scored });
}

// ---------------------------------------------------------------------------
// Relationship summary
// ---------------------------------------------------------------------------

async function handleSummary(characterId: string) {
  // ---- Fixture mode ----
  if (EOQ_FIXTURE_MODE) {
    const memories = getFixtureMemories(characterId);
    return Response.json({
      summary: {
        characterId,
        totalInteractions: memories.length,
        averageImportance: 3,
        sentiment: 0.4,
        strength: 0.6,
        topMemoryTypes: { interaction: memories.length },
      },
    });
  }

  // ---- Scroll all points for this character ----
  await ensureCollection();

  const allPoints: QdrantPoint[] = [];
  let offset: string | null = null;
  const SCROLL_LIMIT = 100;

  // Paginate through all memories for this character
  for (let i = 0; i < 10; i++) {
    const scrollBody: Record<string, unknown> = {
      filter: {
        must: [{ key: "character_id", match: { value: characterId } }],
      },
      limit: SCROLL_LIMIT,
      with_payload: true,
    };
    if (offset) {
      scrollBody.offset = offset;
    }

    const resp = await fetch(
      `${config.qdrantUrl}/collections/${COLLECTION}/points/scroll`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(scrollBody),
      },
    );

    if (!resp.ok) break;

    const data = await resp.json();
    const points: QdrantPoint[] = data.result?.points ?? [];
    allPoints.push(...points);

    offset = data.result?.next_page_offset ?? null;
    if (!offset || points.length < SCROLL_LIMIT) break;
  }

  if (allPoints.length === 0) {
    return Response.json({
      summary: {
        characterId,
        totalInteractions: 0,
        averageImportance: 0,
        sentiment: 0,
        strength: 0,
        topMemoryTypes: {},
      },
    });
  }

  // ---- Compute summary stats ----
  let importanceSum = 0;
  let weightedSentiment = 0;
  let totalWeight = 0;
  const typeCounts: Record<string, number> = {};

  for (const p of allPoints) {
    const importance = typeof p.payload.importance === "number" ? p.payload.importance : 2;
    const timestamp = typeof p.payload.timestamp === "number" ? p.payload.timestamp : Date.now();
    const memType = typeof p.payload.memory_type === "string" ? p.payload.memory_type : "interaction";

    importanceSum += importance;
    typeCounts[memType] = (typeCounts[memType] ?? 0) + 1;

    // Sentiment estimation: high importance = positive for trust/revelation,
    // negative for combat. Neutral for others.
    const sentimentSign = memType === "combat" ? -1 : memType === "revelation" ? 1 : 0.3;
    const weight = recencyWeight(timestamp) * importance;
    weightedSentiment += sentimentSign * weight;
    totalWeight += weight;
  }

  const avgImportance = importanceSum / allPoints.length;
  const sentiment = totalWeight > 0
    ? Math.max(-1, Math.min(1, weightedSentiment / totalWeight))
    : 0;

  // Strength: combination of interaction count and recency
  const recentCount = allPoints.filter(
    (p) =>
      typeof p.payload.timestamp === "number" &&
      Date.now() - p.payload.timestamp < 7 * 86_400_000,
  ).length;
  const strength = Math.min(
    1,
    (allPoints.length / 50) * 0.5 + (recentCount / 10) * 0.5,
  );

  return Response.json({
    summary: {
      characterId,
      totalInteractions: allPoints.length,
      averageImportance: Math.round(avgImportance * 10) / 10,
      sentiment: Math.round(sentiment * 100) / 100,
      strength: Math.round(strength * 100) / 100,
      topMemoryTypes: typeCounts,
    },
  });
}
