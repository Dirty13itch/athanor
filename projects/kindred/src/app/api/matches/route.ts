import { config } from "@/lib/config";

/**
 * POST /api/matches
 *
 * Find users with similar passions using vector similarity search.
 * Takes a user's passion embeddings and finds nearest neighbors in Qdrant.
 *
 * Body: { userId: string, passions: { categoryPath: string, intensity: number }[], limit?: number }
 * Returns: { matches: PassionMatch[] }
 */

const COLLECTION = "kindred_passions";
const VECTOR_SIZE = 1024;

interface PassionMatch {
  userId: string;
  displayName: string;
  sharedPassions: {
    categoryPath: string;
    depthMatch: number;
    yourIntensity: number;
    theirIntensity: number;
  }[];
  matchScore: number;
}

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  if (!body || typeof body.userId !== "string" || !Array.isArray(body.passions)) {
    return Response.json({ error: "userId and passions array required" }, { status: 400 });
  }

  const { userId, passions, limit = 10 } = body as {
    userId: string;
    passions: { categoryPath: string; intensity: number }[];
    limit?: number;
  };

  if (passions.length === 0) {
    return Response.json({ matches: [] });
  }

  // Ensure collection exists
  await ensureCollection();

  // Get embeddings for the user's passions
  const passionTexts = passions.map((p) => {
    const parts = p.categoryPath.split("/");
    // Weight deeper categories higher in the embedding
    return `Passionate about ${parts.join(" > ")} (intensity: ${p.intensity.toFixed(1)})`;
  });

  // Create a combined passion profile embedding
  const profileText = passionTexts.join(". ");
  const embedding = await getEmbedding(profileText);
  if (!embedding) {
    return Response.json({ error: "Embedding generation failed" }, { status: 500 });
  }

  // Search Qdrant for similar passion profiles, excluding self
  try {
    const searchResp = await fetch(
      `${config.qdrantUrl}/collections/${COLLECTION}/points/query`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: embedding,
          limit: limit + 1, // +1 to exclude self
          filter: {
            must_not: [{ key: "user_id", match: { value: userId } }],
          },
          with_payload: true,
        }),
      },
    );

    if (!searchResp.ok) {
      return Response.json({ matches: [] });
    }

    const searchData = await searchResp.json();
    const points = searchData.result?.points ?? [];

    const matches: PassionMatch[] = points.slice(0, limit).map(
      (point: {
        score: number;
        payload: {
          user_id: string;
          display_name: string;
          passions: { categoryPath: string; intensity: number }[];
        };
      }) => {
        const theirPassions = point.payload.passions ?? [];

        // Find shared passions by comparing category path prefixes
        const shared = passions
          .map((myPassion) => {
            const best = theirPassions
              .map((theirPassion) => ({
                passion: theirPassion,
                depth: sharedPathDepth(myPassion.categoryPath, theirPassion.categoryPath),
              }))
              .filter((m) => m.depth > 0)
              .sort((a, b) => b.depth - a.depth)[0];

            if (!best) return null;
            return {
              categoryPath: myPassion.categoryPath,
              depthMatch: best.depth,
              yourIntensity: myPassion.intensity,
              theirIntensity: best.passion.intensity,
            };
          })
          .filter(Boolean) as PassionMatch["sharedPassions"];

        return {
          userId: point.payload.user_id,
          displayName: point.payload.display_name,
          sharedPassions: shared,
          matchScore: point.score,
        };
      },
    );

    return Response.json({ matches });
  } catch (err) {
    console.error("Match search failed:", err);
    return Response.json({ matches: [] });
  }
}

/** Store a user's passion profile in Qdrant for matching */
export async function PUT(req: Request) {
  const body = await req.json().catch(() => null);
  if (
    !body ||
    typeof body.userId !== "string" ||
    typeof body.displayName !== "string" ||
    !Array.isArray(body.passions)
  ) {
    return Response.json(
      { error: "userId, displayName, and passions required" },
      { status: 400 },
    );
  }

  await ensureCollection();

  const profileText = body.passions
    .map((p: { categoryPath: string; intensity: number }) => {
      const parts = p.categoryPath.split("/");
      return `Passionate about ${parts.join(" > ")} (intensity: ${p.intensity.toFixed(1)})`;
    })
    .join(". ");

  const embedding = await getEmbedding(profileText);
  if (!embedding) {
    return Response.json({ error: "Embedding failed" }, { status: 500 });
  }

  const resp = await fetch(`${config.qdrantUrl}/collections/${COLLECTION}/points`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      points: [
        {
          id: body.userId,
          vector: embedding,
          payload: {
            user_id: body.userId,
            display_name: body.displayName,
            passions: body.passions,
            updated_at: new Date().toISOString(),
          },
        },
      ],
    }),
  });

  if (!resp.ok) {
    return Response.json({ error: "Failed to store profile" }, { status: 500 });
  }

  return Response.json({ stored: true, userId: body.userId });
}

// --- Helpers ---

/** Count shared depth between two category paths */
function sharedPathDepth(a: string, b: string): number {
  const partsA = a.split("/");
  const partsB = b.split("/");
  let depth = 0;
  for (let i = 0; i < Math.min(partsA.length, partsB.length); i++) {
    if (partsA[i].toLowerCase() === partsB[i].toLowerCase()) {
      depth++;
    } else {
      break;
    }
  }
  return depth;
}

async function getEmbedding(text: string): Promise<number[] | null> {
  try {
    const resp = await fetch(`${config.litellmUrl}/v1/embeddings`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${config.litellmKey}`,
      },
      body: JSON.stringify({ model: "embedding", input: text }),
    });
    if (!resp.ok) return null;
    const data = await resp.json();
    return data.data?.[0]?.embedding ?? null;
  } catch {
    return null;
  }
}

async function ensureCollection() {
  try {
    const check = await fetch(`${config.qdrantUrl}/collections/${COLLECTION}`);
    if (check.ok) return;

    await fetch(`${config.qdrantUrl}/collections/${COLLECTION}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        vectors: { size: VECTOR_SIZE, distance: "Cosine" },
      }),
    });

    await fetch(`${config.qdrantUrl}/collections/${COLLECTION}/index`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        field_name: "user_id",
        field_schema: "keyword",
      }),
    }).catch(() => {});
  } catch {
    // Collection might already exist
  }
}
