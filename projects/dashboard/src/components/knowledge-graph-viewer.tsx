"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { Search, X, ZoomIn, ZoomOut, Maximize2, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

// Dynamic import to avoid SSR issues with canvas
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[500px] items-center justify-center">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  ),
});

interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
}

interface GraphLink {
  source: string;
  target: string;
  type: string;
}

interface GraphPayload {
  nodes: GraphNode[];
  links: GraphLink[];
  labels: string[];
  meta: { nodeCount: number; linkCount: number; limit: number };
}

// Deterministic color palette per node type
const TYPE_COLORS: Record<string, string> = {
  Node: "#6366f1",
  Service: "#06b6d4",
  Entity: "#f59e0b",
  Document: "#10b981",
  Topic: "#ec4899",
  Agent: "#8b5cf6",
  Memory: "#14b8a6",
  Project: "#f97316",
  Person: "#ef4444",
  Concept: "#a855f7",
  Task: "#84cc16",
  Tool: "#64748b",
};

function colorForType(type: string): string {
  if (TYPE_COLORS[type]) return TYPE_COLORS[type];
  let hash = 0;
  for (let i = 0; i < type.length; i++) {
    hash = type.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 65%, 55%)`;
}

interface NodeDetails {
  node: GraphNode;
}

export function KnowledgeGraphViewer() {
  const [data, setData] = useState<GraphPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [activeLabel, setActiveLabel] = useState("");
  const [selectedNode, setSelectedNode] = useState<NodeDetails | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(null);

  const fetchGraph = useCallback(async (label?: string) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (label) params.set("label", label);
      params.set("limit", "200");
      const res = await fetch(`/api/neo4j/graph?${params}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error ?? `HTTP ${res.status}`);
      }
      const payload: GraphPayload = await res.json();
      setData(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load graph");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGraph(activeLabel || undefined);
  }, [fetchGraph, activeLabel]);

  const filtered = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    if (!search.trim()) return { nodes: data.nodes, links: data.links };

    const q = search.toLowerCase();
    const matchedIds = new Set(
      data.nodes
        .filter(
          (n) =>
            n.label.toLowerCase().includes(q) ||
            n.type.toLowerCase().includes(q)
        )
        .map((n) => n.id)
    );

    return {
      nodes: data.nodes.filter((n) => matchedIds.has(n.id)),
      links: data.links.filter(
        (l) =>
          matchedIds.has(l.source as string) &&
          matchedIds.has(l.target as string)
      ),
    };
  }, [data, search]);

  const nodeTypes = useMemo(() => {
    if (!data) return [];
    const types = new Map<string, number>();
    for (const node of data.nodes) {
      types.set(node.type, (types.get(node.type) ?? 0) + 1);
    }
    return Array.from(types.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([type, count]) => ({ type, count }));
  }, [data]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleNodeClick = useCallback(
    (node: any) => {
      if (!data) return;
      const graphNode = data.nodes.find((n) => n.id === node.id);
      if (graphNode) {
        setSelectedNode({ node: graphNode });
      }
    },
    [data]
  );

  const handleZoomIn = () => graphRef.current?.zoom(1.5, 300);
  const handleZoomOut = () => graphRef.current?.zoom(0.67, 300);
  const handleFit = () => graphRef.current?.zoomToFit(400, 40);

  return (
    <Card className="surface-panel">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle className="text-lg">Knowledge Graph Explorer</CardTitle>
          <div className="flex items-center gap-2">
            {data && (
              <span className="text-xs text-muted-foreground">
                {data.meta.nodeCount} nodes &middot; {data.meta.linkCount} links
              </span>
            )}
            <Button
              size="icon"
              variant="ghost"
              className="h-7 w-7"
              onClick={handleZoomIn}
              title="Zoom in"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="h-7 w-7"
              onClick={handleZoomOut}
              title="Zoom out"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="h-7 w-7"
              onClick={handleFit}
              title="Fit to view"
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>

        <div className="relative mt-2">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search nodes..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 pl-8 text-sm"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-2 top-2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        {data && data.labels.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            <Badge
              variant={activeLabel === "" ? "default" : "outline"}
              className="cursor-pointer text-[10px]"
              onClick={() => setActiveLabel("")}
            >
              All
            </Badge>
            {data.labels.map((label) => (
              <Badge
                key={label}
                variant={activeLabel === label ? "default" : "outline"}
                className="cursor-pointer text-[10px]"
                onClick={() => setActiveLabel(label)}
              >
                {label}
              </Badge>
            ))}
          </div>
        )}
      </CardHeader>

      <CardContent className="p-0">
        {error && (
          <div className="flex h-[500px] items-center justify-center">
            <div className="text-center">
              <p className="text-sm text-destructive">{error}</p>
              <Button
                size="sm"
                variant="outline"
                className="mt-2"
                onClick={() => fetchGraph(activeLabel || undefined)}
              >
                Retry
              </Button>
            </div>
          </div>
        )}

        {loading && !data && (
          <div className="flex h-[500px] items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {data && !error && (
          <div className="relative" style={{ height: 500 }}>
            <ForceGraph2D
              ref={graphRef}
              graphData={filtered}
              nodeId="id"
              nodeLabel={(node: any) => `${node.label} (${node.type})`}
              nodeColor={(node: any) => {
                if (hoveredNode === node.id) return "#ffffff";
                return colorForType(node.type);
              }}
              nodeRelSize={5}
              nodeCanvasObject={(
                node: any,
                ctx: CanvasRenderingContext2D,
                globalScale: number
              ) => {
                const isHovered = hoveredNode === node.id;
                const isSelected = selectedNode?.node.id === node.id;
                const r = isHovered || isSelected ? 7 : 5;
                const color = colorForType(node.type);

                if (isSelected || isHovered) {
                  ctx.beginPath();
                  ctx.arc(node.x, node.y, r + 3, 0, 2 * Math.PI);
                  ctx.fillStyle = `${color}44`;
                  ctx.fill();
                }

                ctx.beginPath();
                ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
                ctx.fillStyle = color;
                ctx.fill();
                ctx.strokeStyle = isSelected ? "#fff" : `${color}88`;
                ctx.lineWidth = isSelected ? 2 : 0.5;
                ctx.stroke();

                if (globalScale > 1.2) {
                  ctx.font = `${Math.max(10 / globalScale, 2)}px Inter, system-ui, sans-serif`;
                  ctx.textAlign = "center";
                  ctx.textBaseline = "top";
                  ctx.fillStyle = "rgba(255,255,255,0.85)";
                  ctx.fillText(node.label, node.x, node.y + r + 2);
                }
              }}
              linkColor={() => "rgba(255,255,255,0.12)"}
              linkDirectionalArrowLength={3}
              linkDirectionalArrowRelPos={1}
              linkWidth={0.5}
              linkLabel={(link: any) => link.type}
              onNodeClick={handleNodeClick}
              onNodeHover={(node: any) => setHoveredNode(node?.id ?? null)}
              backgroundColor="transparent"
              width={undefined}
              height={500}
              cooldownTicks={60}
              warmupTicks={30}
            />
          </div>
        )}

        <div className="border-t border-border/50 p-4">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <p className="mb-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                Node types
              </p>
              <div className="flex flex-wrap gap-1.5">
                {nodeTypes.map(({ type, count }) => (
                  <span
                    key={type}
                    className="inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[10px]"
                  >
                    <span
                      className="inline-block h-2 w-2 rounded-full"
                      style={{ backgroundColor: colorForType(type) }}
                    />
                    {type}
                    <span className="text-muted-foreground">({count})</span>
                  </span>
                ))}
              </div>
            </div>

            {selectedNode && (
              <div className="flex-1 min-w-[250px] surface-instrument rounded-xl border p-3">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-sm">
                      {selectedNode.node.label}
                    </p>
                    <Badge
                      variant="outline"
                      className="mt-1 text-[10px]"
                      style={{
                        borderColor: colorForType(selectedNode.node.type),
                      }}
                    >
                      {selectedNode.node.type}
                    </Badge>
                  </div>
                  <button
                    onClick={() => setSelectedNode(null)}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
                <div className="mt-2 space-y-1 text-xs text-muted-foreground">
                  {Object.entries(selectedNode.node.properties)
                    .filter(([k]) => !["name", "title"].includes(k))
                    .slice(0, 8)
                    .map(([key, value]) => (
                      <div key={key} className="flex justify-between gap-2">
                        <span className="font-mono text-[10px]">{key}</span>
                        <span className="truncate max-w-[200px] text-right">
                          {typeof value === "object"
                            ? JSON.stringify(value)
                            : String(value ?? "")}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
