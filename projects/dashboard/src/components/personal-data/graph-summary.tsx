import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { config } from "@/lib/config";
import { getNeo4jAuthHeader } from "@/lib/server-config";

interface Neo4jResponse {
  results: { data: { row: (string | number)[] }[] }[];
  errors: { message: string }[];
}

async function cypher(statement: string): Promise<Neo4jResponse | null> {
  try {
    const authHeader = getNeo4jAuthHeader();
    if (!authHeader) {
      return null;
    }

    const res = await fetch(`${config.neo4j.url}/db/neo4j/tx/commit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: authHeader,
      },
      body: JSON.stringify({ statements: [{ statement }] }),
      signal: AbortSignal.timeout(5000),
      next: { revalidate: 120 },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function GraphSummary() {
  const [nodeCountRes, relCountRes, labelsRes, topTopicsRes] = await Promise.all([
    cypher("MATCH (n) RETURN count(n) as count"),
    cypher("MATCH ()-[r]->() RETURN count(r) as count"),
    cypher("CALL db.labels() YIELD label RETURN label ORDER BY label"),
    cypher(
      "MATCH (t:Topic)-[r]-() RETURN t.name as name, count(r) as connections ORDER BY connections DESC LIMIT 5"
    ),
  ]);

  const nodeCount = (nodeCountRes?.results?.[0]?.data?.[0]?.row?.[0] as number) ?? 0;
  const relCount = (relCountRes?.results?.[0]?.data?.[0]?.row?.[0] as number) ?? 0;
  const labels = (labelsRes?.results?.[0]?.data ?? []).map((d) => d.row[0] as string);
  const topTopics = (topTopicsRes?.results?.[0]?.data ?? []).map((d) => ({
    name: d.row[0] as string,
    connections: d.row[1] as number,
  }));

  const offline = nodeCount === 0 && relCount === 0 && labels.length === 0;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Knowledge Graph</CardTitle>
          <Badge variant={offline ? "destructive" : "outline"} className="text-[10px]">
            {offline ? "Offline" : "Neo4j"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Stat bar */}
        <div className="flex items-center gap-6">
          <StatItem label="Nodes" value={nodeCount} />
          <StatItem label="Relationships" value={relCount} />
          <StatItem label="Labels" value={labels.length} />
        </div>

        {/* Labels */}
        {labels.length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">Node Labels</p>
            <div className="flex flex-wrap gap-1">
              {labels.map((label) => (
                <Badge key={label} variant="outline" className="text-[10px] font-mono">
                  {label}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Top topics */}
        {topTopics.length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">Most Connected Topics</p>
            <div className="space-y-1.5">
              {topTopics.map((topic) => (
                <div key={topic.name} className="flex items-center justify-between">
                  <span className="text-xs truncate">{topic.name}</span>
                  <span className="text-xs text-muted-foreground font-mono">
                    {topic.connections} links
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function StatItem({ label, value }: { label: string; value: number }) {
  return (
    <div className="space-y-0.5">
      <p className="text-xl font-semibold">{value.toLocaleString()}</p>
      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{label}</p>
    </div>
  );
}
