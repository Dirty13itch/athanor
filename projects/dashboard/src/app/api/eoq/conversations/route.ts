import { config } from "@/lib/config";
import { isDashboardFixtureMode } from "@/lib/dashboard-fixtures";

interface EoqDialogue {
  id: string;
  queenName: string;
  queenId: string;
  playerInput: string;
  queenResponse: string;
  timestamp: string;
}

export async function GET() {
  if (isDashboardFixtureMode()) {
    return Response.json({ dialogues: [] });
  }

  try {
    // Query Qdrant conversations collection for EoBQ-tagged entries
    const res = await fetch(`${config.qdrant.url}/collections/conversations/points/scroll`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        limit: 20,
        with_payload: true,
        with_vector: false,
        filter: {
          should: [
            { key: "project", match: { value: "eoq" } },
            { key: "source", match: { value: "eoq" } },
            { key: "tags", match: { any: ["eoq", "empire-of-broken-queens"] } },
          ],
        },
      }),
      signal: AbortSignal.timeout(5000),
    });

    if (!res.ok) {
      return Response.json({ dialogues: [] });
    }

    const data = await res.json();
    const points = data.result?.points ?? [];

    const dialogues: EoqDialogue[] = points
      .map((point: { id: string; payload: Record<string, unknown> }) => {
        const p = point.payload;
        return {
          id: String(point.id),
          queenName: (p.queen_name as string) ?? (p.character_name as string) ?? "Unknown",
          queenId: (p.queen_id as string) ?? (p.character_id as string) ?? "",
          playerInput: (p.player_input as string) ?? (p.user_message as string) ?? "",
          queenResponse: (p.queen_response as string) ?? (p.assistant_message as string) ?? "",
          timestamp: (p.timestamp as string) ?? new Date().toISOString(),
        };
      })
      .filter((d: EoqDialogue) => d.playerInput || d.queenResponse)
      .sort((a: EoqDialogue, b: EoqDialogue) => b.timestamp.localeCompare(a.timestamp))
      .slice(0, 10);

    return Response.json({ dialogues });
  } catch {
    return Response.json({ dialogues: [] });
  }
}
