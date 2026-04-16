import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";
import { isDashboardFixtureMode } from "@/lib/dashboard-fixtures";
import { getNeo4jAuthHeader, hasNeo4jCredentials } from "@/lib/server-config";

interface Neo4jRow {
  row: unknown[];
  meta: ({ id: number; elementId: string; type: string; deleted: boolean } | null)[];
}

interface Neo4jResponse {
  results: { columns: string[]; data: Neo4jRow[] }[];
  errors: { message: string }[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface GraphLink {
  source: string;
  target: string;
  type: string;
}

export interface GraphPayload {
  nodes: GraphNode[];
  links: GraphLink[];
  labels: string[];
  meta: { nodeCount: number; linkCount: number; limit: number };
}

const FIXTURE_GRAPH_NODES: GraphNode[] = [
  {
    id: "project-athanor",
    label: "Athanor",
    type: "Project",
    properties: { status: "active", owner: "Shaun" },
  },
  {
    id: "topic-command-center",
    label: "Command Center",
    type: "Topic",
    properties: { surface: "/"} ,
  },
  {
    id: "service-agent-server",
    label: "Agent Server",
    type: "Service",
    properties: { node: "foundry", surface: "/agents" },
  },
  {
    id: "service-dashboard",
    label: "Dashboard",
    type: "Service",
    properties: { node: "dev", surface: "/" },
  },
  {
    id: "provider-openai",
    label: "OpenAI",
    type: "Provider",
    properties: { lane: "cloud", status: "verified" },
  },
  {
    id: "task-cutover",
    label: "Runtime Cutover",
    type: "Task",
    properties: { status: "queued", priority: "high" },
  },
];

const FIXTURE_GRAPH_LINKS: GraphLink[] = [
  { source: "project-athanor", target: "topic-command-center", type: "HAS_SURFACE" },
  { source: "project-athanor", target: "service-dashboard", type: "RUNS_ON" },
  { source: "project-athanor", target: "service-agent-server", type: "DEPENDS_ON" },
  { source: "service-dashboard", target: "service-agent-server", type: "PROXIES_TO" },
  { source: "service-agent-server", target: "provider-openai", type: "ROUTES_TO" },
  { source: "project-athanor", target: "task-cutover", type: "TRACKS" },
];

function buildFixtureGraphPayload(limit: number, labelFilter: string): GraphPayload {
  const filteredNodes = labelFilter
    ? FIXTURE_GRAPH_NODES.filter((node) => node.type === labelFilter)
    : FIXTURE_GRAPH_NODES;
  const limitedNodes = filteredNodes.slice(0, limit);
  const nodeIds = new Set(limitedNodes.map((node) => node.id));
  const links = FIXTURE_GRAPH_LINKS.filter(
    (link) => nodeIds.has(link.source) && nodeIds.has(link.target)
  ).slice(0, limit);

  return {
    nodes: limitedNodes,
    links,
    labels: Array.from(new Set(FIXTURE_GRAPH_NODES.map((node) => node.type))).sort(),
    meta: {
      nodeCount: limitedNodes.length,
      linkCount: links.length,
      limit,
    },
  };
}

async function cypher(statement: string): Promise<Neo4jResponse | null> {
  const authHeader = getNeo4jAuthHeader();
  if (!authHeader) return null;

  try {
    const res = await fetch(`${config.neo4j.url}/db/neo4j/tx/commit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: authHeader,
      },
      body: JSON.stringify({
        statements: [{ statement, resultDataContents: ["row"] }],
      }),
      signal: AbortSignal.timeout(10_000),
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const limit = Math.min(Number(searchParams.get("limit") ?? 200), 500);
  const labelFilter = searchParams.get("label") ?? "";

  if (isDashboardFixtureMode()) {
    return NextResponse.json(buildFixtureGraphPayload(limit, labelFilter));
  }

  if (!hasNeo4jCredentials()) {
    return NextResponse.json(
      { error: "Neo4j credentials not configured" },
      { status: 503 }
    );
  }

  // Query returns node properties, labels, element IDs, and relationship type
  let query: string;
  if (labelFilter) {
    query = `MATCH (n:\`${labelFilter}\`)-[r]->(m) RETURN n, r, m, labels(n) as nLabels, labels(m) as mLabels, elementId(n) as nId, elementId(m) as mId, type(r) as rType LIMIT ${limit}`;
  } else {
    query = `MATCH (n)-[r]->(m) RETURN n, r, m, labels(n) as nLabels, labels(m) as mLabels, elementId(n) as nId, elementId(m) as mId, type(r) as rType LIMIT ${limit}`;
  }

  const [result, labelsResult] = await Promise.all([
    cypher(query),
    cypher("CALL db.labels() YIELD label RETURN label ORDER BY label"),
  ]);

  if (!result) {
    return NextResponse.json({ error: "Neo4j query failed" }, { status: 502 });
  }

  if (result.errors.length > 0) {
    return NextResponse.json(
      { error: result.errors[0].message },
      { status: 400 }
    );
  }

  const nodesMap = new Map<string, GraphNode>();
  const links: GraphLink[] = [];

  for (const row of result.results[0]?.data ?? []) {
    const d = row.row;
    // d[0]=sourceProps, d[1]=relProps, d[2]=targetProps,
    // d[3]=nLabels[], d[4]=mLabels[], d[5]=nElementId, d[6]=mElementId, d[7]=rType
    const sourceProps = (d[0] as Record<string, unknown>) ?? {};
    const targetProps = (d[2] as Record<string, unknown>) ?? {};
    const nLabels = (d[3] as string[]) ?? [];
    const mLabels = (d[4] as string[]) ?? [];
    const nId = String(d[5] ?? row.meta[0]?.id ?? "");
    const mId = String(d[6] ?? row.meta[2]?.id ?? "");
    const rType = (d[7] as string) ?? "RELATED_TO";

    if (nId && !nodesMap.has(nId)) {
      nodesMap.set(nId, {
        id: nId,
        label:
          (sourceProps.name as string) ??
          (sourceProps.title as string) ??
          nLabels[0] ??
          nId,
        type: nLabels[0] ?? "Unknown",
        properties: sourceProps,
      });
    }

    if (mId && !nodesMap.has(mId)) {
      nodesMap.set(mId, {
        id: mId,
        label:
          (targetProps.name as string) ??
          (targetProps.title as string) ??
          mLabels[0] ??
          mId,
        type: mLabels[0] ?? "Unknown",
        properties: targetProps,
      });
    }

    if (nId && mId) {
      links.push({ source: nId, target: mId, type: rType });
    }
  }

  const labels = (labelsResult?.results?.[0]?.data ?? []).map(
    (d) => d.row[0] as string
  );

  return NextResponse.json({
    nodes: Array.from(nodesMap.values()),
    links,
    labels,
    meta: {
      nodeCount: nodesMap.size,
      linkCount: links.length,
      limit,
    },
  } satisfies GraphPayload);
}
