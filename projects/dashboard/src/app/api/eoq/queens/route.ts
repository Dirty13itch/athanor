import { config } from "@/lib/config";
import { isDashboardFixtureMode } from "@/lib/dashboard-fixtures";
import queensData from "@/data/eoq-queens.json";

export async function GET() {
  const queens = queensData.queens;

  if (isDashboardFixtureMode()) {
    return Response.json({
      queens: queens.map((q) => ({ ...q, relationships: [] })),
      archetypeColors: queensData.archetypeColors,
    });
  }

  // Enrich with Neo4j relationships
  const enriched = await Promise.all(
    queens.map(async (queen) => {
      try {
        const body = JSON.stringify({
          statements: [
            {
              statement: `MATCH (c:Character {name: $name})-[r:RELATIONSHIP]->(other:Character) RETURN other.name AS target, r.type AS type LIMIT 10`,
              parameters: { name: queen.name },
            },
          ],
        });
        const res = await fetch(`${config.neo4j.url}/db/neo4j/tx/commit`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: "Basic " + btoa("neo4j:neo4j") },
          body,
          signal: AbortSignal.timeout(3000),
        });
        if (!res.ok) return { ...queen, relationships: [] };
        const data = await res.json();
        const rows = data.results?.[0]?.data ?? [];
        const relationships = rows.map((r: { row: string[] }) => ({
          target: r.row[0],
          type: r.row[1],
        }));
        return { ...queen, relationships };
      } catch {
        return { ...queen, relationships: [] };
      }
    })
  );

  return Response.json({
    queens: enriched,
    archetypeColors: queensData.archetypeColors,
  });
}
