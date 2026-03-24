"use client";

import { useQuery } from "@tanstack/react-query";
import { RefreshCcw, Server, Cpu, Bot, Layers } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { StatusDot } from "@/components/status-dot";
import { requestJson } from "@/features/workforce/helpers";
import { formatMiB, formatPercent, formatTemperatureF } from "@/lib/format";
import { liveQueryOptions } from "@/lib/live-updates";
import { queryKeys } from "@/lib/query-client";
import type { GpuSnapshotResponse } from "@/lib/contracts";

// ─── Topology types (props from server) ─────────────────────────────────────

interface NodeDef {
  id: string;
  name: string;
  ip: string;
  role: string;
}

interface ModelDef {
  nodeId: string;
  name: string;
  alias: string;
  port: number;
  description: string;
}

export interface TopologyProps {
  nodes: NodeDef[];
  models: ModelDef[];
  nodeServices: Record<string, string[]>;
}

// ─── API types (minimal) ────────────────────────────────────────────────────

interface AgentInfo {
  id: string;
  name: string;
  status: string;
  description: string;
}

interface AgentsResponse {
  agents: AgentInfo[];
}

interface OverviewNode {
  id: string;
  name: string;
  healthyServices: number;
  totalServices: number;
  degradedServices: number;
}

interface OverviewSnapshot {
  nodes: OverviewNode[];
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function nodeHealthTone(node: OverviewNode | undefined): "healthy" | "warning" | "danger" | "muted" {
  if (!node) return "muted";
  if (node.degradedServices > 0) return "warning";
  return "healthy";
}

function agentStatusTone(status: string): "healthy" | "warning" | "danger" | "muted" {
  if (status === "ready") return "healthy";
  if (status === "busy" || status === "degraded") return "warning";
  if (status === "error" || status === "failed") return "danger";
  return "muted";
}

function utilBarColor(pct: number | null): string {
  if (pct === null) return "bg-border/50";
  if (pct >= 85) return "bg-[color:var(--signal-danger)]";
  if (pct >= 60) return "bg-[color:var(--signal-warning)]";
  return "bg-[color:var(--signal-success)]";
}

function vramBarColor(ratio: number): string {
  if (ratio >= 0.9) return "bg-[color:var(--signal-danger)]";
  if (ratio >= 0.7) return "bg-[color:var(--signal-warning)]";
  return "bg-[color:var(--signal-success)]";
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function MiniBar({ pct, colorClass }: { pct: number; colorClass: string }) {
  return (
    <div className="h-1.5 w-full rounded-full bg-border/30">
      <div
        className={`h-1.5 rounded-full transition-all ${colorClass}`}
        style={{ width: `${Math.min(pct, 100)}%` }}
      />
    </div>
  );
}

function GpuSlot({ gpu }: { gpu: GpuSnapshotResponse["gpus"][number] }) {
  const vramUsed = gpu.memoryUsedMiB ?? 0;
  const vramTotal = gpu.memoryTotalMiB ?? 1;
  const vramRatio = vramUsed / vramTotal;
  const utilPct = gpu.utilization ?? 0;

  return (
    <div className="surface-metric rounded-xl border p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium truncate">{gpu.gpuName}</p>
        <Badge variant="outline" className="shrink-0 text-xs tabular-nums">
          {formatTemperatureF(gpu.temperatureC)}
        </Badge>
      </div>
      <div className="space-y-1">
        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
          <span>Util</span>
          <span>{formatPercent(gpu.utilization, 0)}</span>
        </div>
        <MiniBar pct={utilPct} colorClass={utilBarColor(gpu.utilization)} />
      </div>
      <div className="space-y-1">
        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
          <span>VRAM</span>
          <span>{formatMiB(gpu.memoryUsedMiB)} / {formatMiB(gpu.memoryTotalMiB)}</span>
        </div>
        <MiniBar pct={vramRatio * 100} colorClass={vramBarColor(vramRatio)} />
      </div>
    </div>
  );
}

function ModelRow({ model }: { model: ModelDef }) {
  return (
    <div className="surface-instrument flex items-center justify-between rounded-xl border px-3 py-2 gap-3">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium truncate">{model.name}</p>
        <p className="text-[11px] text-muted-foreground">:{model.port}</p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Badge variant="secondary" className="text-xs font-mono">{model.alias}</Badge>
      </div>
    </div>
  );
}

function NodeCard({
  node,
  gpus,
  overviewNode,
  models,
  services,
}: {
  node: NodeDef;
  gpus: GpuSnapshotResponse["gpus"];
  overviewNode: OverviewNode | undefined;
  models: ModelDef[];
  services: string[];
}) {
  const nodeModels = models.filter((m) => m.nodeId === node.id);
  const nodeServices = services;
  const tone = nodeHealthTone(overviewNode);

  return (
    <Card className="surface-panel">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <StatusDot tone={tone} pulse={tone === "warning"} />
              <CardTitle className="text-lg">{node.name}</CardTitle>
              <Badge variant="outline" className="font-mono text-xs">{node.ip}</Badge>
            </div>
            <CardDescription className="mt-1">{node.role}</CardDescription>
          </div>
          {overviewNode && (
            <Badge
              variant="outline"
              className="shrink-0 text-xs"
              data-tone={overviewNode.degradedServices > 0 ? "warning" : "success"}
            >
              {overviewNode.healthyServices}/{overviewNode.totalServices} healthy
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* GPU slots */}
        {gpus.length > 0 ? (
          <div>
            <p className="mb-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">GPUs</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {gpus.map((gpu) => (
                <GpuSlot key={gpu.id} gpu={gpu} />
              ))}
            </div>
          </div>
        ) : (
          <div>
            <p className="mb-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">GPUs</p>
            <p className="text-sm text-muted-foreground">No DCGM data available.</p>
          </div>
        )}

        {/* Models */}
        {nodeModels.length > 0 && (
          <div>
            <p className="mb-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Models</p>
            <div className="space-y-1.5">
              {nodeModels.map((model) => (
                <ModelRow key={`${model.nodeId}-${model.port}`} model={model} />
              ))}
            </div>
          </div>
        )}

        {/* Services */}
        <div>
          <p className="mb-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            Services ({nodeServices.length})
          </p>
          <div className="flex flex-wrap gap-1.5">
            {nodeServices.map((svc) => (
              <Badge key={svc} variant="secondary" className="text-xs font-mono">{svc}</Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Main console ────────────────────────────────────────────────────────────

export function TopologyConsole({ nodes, models, nodeServices }: TopologyProps) {
  const gpuQuery = useQuery<GpuSnapshotResponse>({
    queryKey: queryKeys.gpuSnapshot,
    queryFn: () => requestJson("/api/gpu") as Promise<GpuSnapshotResponse>,
    ...liveQueryOptions(15_000),
  });

  const agentsQuery = useQuery<AgentsResponse>({
    queryKey: [...queryKeys.agents, "topology"],
    queryFn: () => requestJson("/api/agents/proxy?path=/v1/agents") as Promise<AgentsResponse>,
    ...liveQueryOptions(30_000),
  });

  const overviewQuery = useQuery<OverviewSnapshot>({
    queryKey: [...queryKeys.overview, "topology"],
    queryFn: () => requestJson("/api/overview") as Promise<OverviewSnapshot>,
    ...liveQueryOptions(15_000),
  });

  const gpuData = gpuQuery.data;
  const agents = agentsQuery.data?.agents ?? [];
  const overviewNodes = overviewQuery.data?.nodes ?? [];

  const totalGpus = gpuData?.gpus.length ?? 0;
  const activeModels = models.length;
  const readyAgents = agents.filter((a) => a.status === "ready").length;

  const isFetching = gpuQuery.isFetching || agentsQuery.isFetching || overviewQuery.isFetching;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Core"
        title="System Topology"
        description="Live view of the 4-node Athanor cluster — hardware, inference models, and agent layer."
        actions={
          <Button
            variant="outline"
            onClick={() => {
              void gpuQuery.refetch();
              void agentsQuery.refetch();
              void overviewQuery.refetch();
            }}
            disabled={isFetching}
          >
            <RefreshCcw className={`mr-2 h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Nodes"
            value={`${nodes.length}`}
            detail={nodes.map((n) => n.name).join(", ")}
            icon={<Server className="h-5 w-5" />}
          />
          <StatCard
            label="GPUs"
            value={totalGpus > 0 ? `${totalGpus}` : "—"}
            detail="Discovered via DCGM / Prometheus"
            icon={<Cpu className="h-5 w-5" />}
          />
          <StatCard
            label="Active models"
            value={`${activeModels}`}
            detail={models.map((m) => m.alias).slice(0, 4).join(", ")}
            icon={<Layers className="h-5 w-5" />}
          />
          <StatCard
            label="Agents"
            value={agents.length > 0 ? `${readyAgents}/${agents.length}` : "—"}
            detail="Ready / total on FOUNDRY:9000"
            icon={<Bot className="h-5 w-5" />}
            tone={agents.length > 0 && readyAgents === agents.length ? "success" : agents.length > 0 ? "warning" : undefined}
          />
        </div>
      </PageHeader>

      {/* Node cards */}
      <div className="grid gap-6 xl:grid-cols-2">
        {nodes.map((node) => {
          const nodeGpus = (gpuData?.gpus ?? []).filter((gpu) => {
            const gpuNode = gpu.node?.toLowerCase() ?? "";
            return gpuNode === node.id || gpuNode.startsWith(node.name.toLowerCase());
          });
          const overviewNode = overviewNodes.find((n) => n.id === node.id || n.name.toLowerCase() === node.id);
          return (
            <NodeCard
              key={node.id}
              node={node}
              gpus={nodeGpus}
              overviewNode={overviewNode}
              models={models}
              services={nodeServices[node.id] ?? []}
            />
          );
        })}
      </div>

      {/* Agent layer */}
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Agent Layer</CardTitle>
          <CardDescription>
            9 agents on FOUNDRY:9000 — LangGraph + FastAPI orchestration.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {agentsQuery.isError ? (
            <p className="text-sm text-muted-foreground">Agent data unavailable — FOUNDRY:9000 may be unreachable.</p>
          ) : agents.length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {agents.map((agent) => (
                <div
                  key={agent.id}
                  className="surface-instrument flex items-start gap-3 rounded-xl border p-3"
                >
                  <StatusDot tone={agentStatusTone(agent.status)} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{agent.name}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">{agent.description}</p>
                  </div>
                  <Badge
                    variant="outline"
                    className="shrink-0 text-xs"
                    data-tone={agent.status === "ready" ? "success" : agent.status === "busy" ? "warning" : undefined}
                  >
                    {agent.status}
                  </Badge>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No agent data"
              description="Agent metadata will appear once FOUNDRY:9000 responds."
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
