import { config } from "@/lib/config";
import { isDashboardFixtureMode } from "@/lib/dashboard-fixtures";

interface MemorySummary {
  characterId: string;
  memoryCount: number;
  lastInteraction: string | null;
  avgImportance: number;
  topMemoryText: string;
}

export async function GET() {
  if (isDashboardFixtureMode()) {
    return Response.json({ memories: [] });
  }

  try {
    // Scroll all points from eoq_character_memory, grouped by character_id
    const res = await fetch(`${config.qdrant.url}/collections/eoq_character_memory/points/scroll`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ limit: 500, with_payload: true, with_vector: false }),
      signal: AbortSignal.timeout(5000),
    });

    if (!res.ok) {
      return Response.json({ memories: [] });
    }

    const data = await res.json();
    const points = data.result?.points ?? [];

    // Group by character_id
    const groups = new Map<string, { importance: number[]; timestamps: string[]; texts: string[] }>();
    for (const point of points) {
      const payload = point.payload ?? {};
      const charId = payload.character_id as string;
      if (!charId) continue;

      const group = groups.get(charId) ?? { importance: [], timestamps: [], texts: [] };
      if (typeof payload.importance === "number") group.importance.push(payload.importance);
      if (typeof payload.timestamp === "string") group.timestamps.push(payload.timestamp);
      if (typeof payload.text === "string") group.texts.push(payload.text);
      groups.set(charId, group);
    }

    const memories: MemorySummary[] = [];
    for (const [characterId, group] of groups) {
      const avgImportance =
        group.importance.length > 0
          ? group.importance.reduce((a, b) => a + b, 0) / group.importance.length
          : 0;
      const sorted = [...group.timestamps].sort().reverse();
      memories.push({
        characterId,
        memoryCount: group.importance.length || group.texts.length,
        lastInteraction: sorted[0] ?? null,
        avgImportance,
        topMemoryText: group.texts[0] ?? "",
      });
    }

    memories.sort((a, b) => b.memoryCount - a.memoryCount);

    return Response.json({ memories });
  } catch {
    return Response.json({ memories: [] });
  }
}
