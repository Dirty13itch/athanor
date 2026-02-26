import { NextResponse } from "next/server";

const QDRANT_URL = "http://192.168.1.244:6333";
const COLLECTION = "personal_data";
const NEO4J_URL = "http://192.168.1.203:7474";
const NEO4J_USER = "neo4j";
const NEO4J_PASS = "athanor2026";

interface QdrantCollectionInfo {
  result: {
    points_count: number;
    vectors_count: number;
    segments_count: number;
    status: string;
    config: {
      params: {
        vectors: { size: number; distance: string };
      };
    };
  };
}

interface Neo4jResponse {
  results: { data: { row: (string | number)[] }[] }[];
  errors: { message: string }[];
}

async function getQdrantStats() {
  try {
    const res = await fetch(`${QDRANT_URL}/collections/${COLLECTION}`, {
      signal: AbortSignal.timeout(5000),
      next: { revalidate: 30 },
    });
    if (!res.ok) return null;
    const data: QdrantCollectionInfo = await res.json();
    return {
      points: data.result.points_count,
      vectors: data.result.vectors_count,
      segments: data.result.segments_count,
      status: data.result.status,
      vectorSize: data.result.config?.params?.vectors?.size ?? 0,
      distance: data.result.config?.params?.vectors?.distance ?? "unknown",
    };
  } catch {
    return null;
  }
}

async function neo4jQuery(statement: string): Promise<Neo4jResponse | null> {
  try {
    const res = await fetch(`${NEO4J_URL}/db/neo4j/tx/commit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Basic ${Buffer.from(`${NEO4J_USER}:${NEO4J_PASS}`).toString("base64")}`,
      },
      body: JSON.stringify({ statements: [{ statement }] }),
      signal: AbortSignal.timeout(5000),
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

async function getNeo4jStats() {
  try {
    const [nodeCountRes, relCountRes, labelCountRes, topTopicsRes] = await Promise.all([
      neo4jQuery("MATCH (n) RETURN count(n) as count"),
      neo4jQuery("MATCH ()-[r]->() RETURN count(r) as count"),
      neo4jQuery("CALL db.labels() YIELD label RETURN label, 0 as count"),
      neo4jQuery(
        "MATCH (t:Topic)-[r]-() RETURN t.name as name, count(r) as connections ORDER BY connections DESC LIMIT 5"
      ),
    ]);

    const nodeCount = nodeCountRes?.results?.[0]?.data?.[0]?.row?.[0] ?? 0;
    const relCount = relCountRes?.results?.[0]?.data?.[0]?.row?.[0] ?? 0;
    const labels = (labelCountRes?.results?.[0]?.data ?? []).map((d) => d.row[0] as string);
    const topTopics = (topTopicsRes?.results?.[0]?.data ?? []).map((d) => ({
      name: d.row[0] as string,
      connections: d.row[1] as number,
    }));

    return {
      nodes: nodeCount as number,
      relationships: relCount as number,
      labels,
      topTopics,
    };
  } catch {
    return null;
  }
}

export async function GET() {
  const [qdrant, neo4j] = await Promise.all([getQdrantStats(), getNeo4jStats()]);

  return NextResponse.json({
    qdrant,
    neo4j,
    timestamp: new Date().toISOString(),
  });
}
