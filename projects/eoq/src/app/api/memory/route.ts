import { config } from "@/lib/config";

/**
 * Character memory API — stores and retrieves interaction memories from Qdrant.
 * Uses the embedding model via LiteLLM to vectorize memory text.
 *
 * POST: Store a new memory
 * GET: Retrieve relevant memories for a character + context
 */

const COLLECTION = "eoq_characters";
const VECTOR_SIZE = 1024;

/** Store a memory about a character interaction */
export async function POST(req: Request) {
  const { characterId, sessionId, text, metadata } = await req.json();

  // Generate embedding
  const embedding = await getEmbedding(text);
  if (!embedding) {
    return Response.json({ error: "Embedding generation failed" }, { status: 500 });
  }

  // Ensure collection exists
  await ensureCollection();

  // Upsert to Qdrant
  const pointId = crypto.randomUUID();
  const resp = await fetch(`${config.qdrantUrl}/collections/${COLLECTION}/points`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      points: [
        {
          id: pointId,
          vector: embedding,
          payload: {
            character_id: characterId,
            session_id: sessionId,
            text,
            timestamp: Date.now(),
            ...metadata,
          },
        },
      ],
    }),
  });

  if (!resp.ok) {
    const error = await resp.text();
    return Response.json({ error }, { status: resp.status });
  }

  return Response.json({ id: pointId });
}

/** Retrieve relevant memories for a character */
export async function GET(req: Request) {
  const url = new URL(req.url);
  const characterId = url.searchParams.get("characterId");
  const query = url.searchParams.get("query");
  const limit = parseInt(url.searchParams.get("limit") ?? "5");

  if (!characterId || !query) {
    return Response.json({ error: "characterId and query required" }, { status: 400 });
  }

  // Generate embedding for the query
  const embedding = await getEmbedding(query);
  if (!embedding) {
    return Response.json({ memories: [] });
  }

  // Search Qdrant
  const resp = await fetch(`${config.qdrantUrl}/collections/${COLLECTION}/points/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: embedding,
      limit,
      filter: {
        must: [
          { key: "character_id", match: { value: characterId } },
        ],
      },
      with_payload: true,
    }),
  });

  if (!resp.ok) {
    return Response.json({ memories: [] });
  }

  const data = await resp.json();
  const memories = (data.result?.points ?? []).map((p: { payload: Record<string, unknown>; score: number }) => ({
    text: p.payload.text,
    timestamp: p.payload.timestamp,
    score: p.score,
    metadata: p.payload,
  }));

  return Response.json({ memories });
}

/** Get embedding from LiteLLM */
async function getEmbedding(text: string): Promise<number[] | null> {
  try {
    const resp = await fetch(`${config.litellmUrl}/v1/embeddings`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${config.litellmKey}`,
      },
      body: JSON.stringify({
        model: "embedding",
        input: text,
      }),
    });

    if (!resp.ok) return null;

    const data = await resp.json();
    return data.data?.[0]?.embedding ?? null;
  } catch {
    return null;
  }
}

/** Ensure the Qdrant collection exists */
async function ensureCollection() {
  try {
    const check = await fetch(`${config.qdrantUrl}/collections/${COLLECTION}`);
    if (check.ok) return;

    await fetch(`${config.qdrantUrl}/collections/${COLLECTION}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        vectors: {
          size: VECTOR_SIZE,
          distance: "Cosine",
        },
      }),
    });
  } catch {
    // Collection might already exist
  }
}
