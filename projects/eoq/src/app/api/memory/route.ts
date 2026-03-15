import { config } from "@/lib/config";
import { EOQ_FIXTURE_MODE } from "@/lib/fixture-mode";
import { addFixtureMemory } from "@/lib/fixtures";

/**
 * Character memory API -- stores interaction memories in Qdrant with
 * typed memory categories, importance scoring, and recency decay.
 *
 * POST: Store a new memory (embeds via LiteLLM, upserts to Qdrant)
 * GET:  Legacy retrieve endpoint (prefer /api/memory/[characterId] instead)
 *
 * Collection: eoq_character_memory
 * Embedding: Qwen3-Embedding (1024 dims) via LiteLLM
 */

export const COLLECTION = "eoq_character_memory";
export const VECTOR_SIZE = 1024;

const VALID_MEMORY_TYPES = new Set([
  "interaction",
  "choice",
  "revelation",
  "combat",
  "relationship_change",
]);

// ---------------------------------------------------------------------------
// POST -- store a new memory
// ---------------------------------------------------------------------------

export async function POST(req: Request) {
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const characterId = typeof body.characterId === "string" ? body.characterId : "";
  const sessionId = typeof body.sessionId === "string" ? body.sessionId : "";
  // Accept both "content" (new) and "text" (legacy) field names
  const content =
    typeof body.content === "string"
      ? body.content
      : typeof body.text === "string"
        ? body.text
        : "";
  const importance = clampImportance(body.importance);
  const memoryType =
    typeof body.memoryType === "string" && VALID_MEMORY_TYPES.has(body.memoryType)
      ? body.memoryType
      : "interaction";
  const metadata =
    typeof body.metadata === "object" && body.metadata !== null
      ? (body.metadata as Record<string, unknown>)
      : {};

  if (!characterId || !content) {
    return Response.json(
      { error: "characterId and content (or text) are required" },
      { status: 400 },
    );
  }

  // ---- Fixture mode ----
  if (EOQ_FIXTURE_MODE) {
    const id = crypto.randomUUID();
    addFixtureMemory({
      characterId,
      text: content,
      timestamp: Date.now(),
      metadata: { sessionId, importance, memoryType, ...metadata },
    });
    return Response.json({ id });
  }

  // ---- Generate embedding ----
  const embedding = await getEmbedding(content);
  if (!embedding) {
    return Response.json({ error: "Embedding generation failed" }, { status: 500 });
  }

  // ---- Ensure collection exists ----
  await ensureCollection();

  // ---- Upsert to Qdrant ----
  const pointId = crypto.randomUUID();
  const timestamp = Date.now();

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
            text: content,
            importance,
            memory_type: memoryType,
            timestamp,
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

// ---------------------------------------------------------------------------
// GET -- legacy retrieve (kept for backwards compat; prefer [characterId] route)
// ---------------------------------------------------------------------------

export async function GET(req: Request) {
  const url = new URL(req.url);
  const characterId = url.searchParams.get("characterId");
  const query = url.searchParams.get("query");
  const limit = parseInt(url.searchParams.get("limit") ?? "5");

  if (!characterId || !query) {
    return Response.json({ error: "characterId and query required" }, { status: 400 });
  }

  // Redirect to the new route internally
  const params = new URLSearchParams({ query, limit: String(limit) });
  const internalUrl = new URL(`/api/memory/${characterId}?${params}`, url.origin);
  return fetch(internalUrl);
}

// ---------------------------------------------------------------------------
// Shared helpers (exported for use by [characterId] route)
// ---------------------------------------------------------------------------

/** Get embedding from LiteLLM */
export async function getEmbedding(text: string): Promise<number[] | null> {
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

/** Ensure the Qdrant collection exists with the right schema */
export async function ensureCollection() {
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

    // Create payload indexes for common filter fields
    const indexFields = ["character_id", "memory_type", "importance"];
    for (const field of indexFields) {
      await fetch(
        `${config.qdrantUrl}/collections/${COLLECTION}/index`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            field_name: field,
            field_schema: field === "importance" ? "integer" : "keyword",
          }),
        },
      ).catch(() => {
        // Index creation is best-effort
      });
    }
  } catch {
    // Collection might already exist
  }
}

/**
 * Compute recency weight: exponential decay over days.
 * Half-life of 7 days -- memories older than ~30 days score < 0.05.
 */
export function recencyWeight(timestampMs: number): number {
  const daysSince = (Date.now() - timestampMs) / 86_400_000;
  return Math.exp(-0.1 * daysSince);
}

function clampImportance(value: unknown): 1 | 2 | 3 | 4 | 5 {
  if (typeof value !== "number") return 2;
  const clamped = Math.round(Math.max(1, Math.min(5, value)));
  return clamped as 1 | 2 | 3 | 4 | 5;
}
