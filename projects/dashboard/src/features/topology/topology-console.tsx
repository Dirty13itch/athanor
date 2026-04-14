"use client";

import { useQuery } from "@tanstack/react-query";
import { Bot, Cpu, Layers, RefreshCcw, Server } from "lucide-react";
import { MasterAtlasRelationshipPanel, type MasterAtlasRelationshipMap } from "@/components/master-atlas-relationship-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { StatusDot } from "@/components/status-dot";
import { requestJson } from "@/features/workforce/helpers";
import { formatMiB, formatPercent, formatTemperatureF } from "@/lib/format";
import { liveQueryOptions } from "@/lib/live-updates";
import { queryKeys } from "@/lib/query-client";
import type { GpuSnapshotResponse } from "@/lib/contracts";

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

interface MasterAtlasErrorResponse {
  error: string;
}

function zoneIdForNode(nodeId: string) {
  const canonicalId = canonicalNodeId(nodeId);
  return canonicalId.slice(0, 1).toUpperCase();
}

function canonicalNodeId(nodeId: string) {
  const normalized = nodeId.trim().toLowerCase();
  if (normalized === "node1") return "foundry";
  if (normalized === "node2") return "workshop";
  return normalized;
}

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

function summarizeList(items: string[], limit = 6) {
  const visible = items.slice(0, limit);
  const remaining = Math.max(0, items.length - visible.length);
  return { visible, remaining };
}

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
    <div className="surface-metric space-y-2 rounded-2xl border px-4 py-3">
      <div className="flex items-center justify-between gap-2">
        <p className="truncate text-sm font-medium">{gpu.gpuName}</p>
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
          <span>
            {formatMiB(gpu.memoryUsedMiB)} / {formatMiB(gpu.memoryTotalMiB)}
          </span>
        </div>
        <MiniBar pct={vramRatio * 100} colorClass={vramBarColor(vramRatio)} />
      </div>
    </div>
  );
}

function NodeDigestCard({
  node,
  overviewNode,
  gpuCount,
  modelCount,
  serviceCount,
  harvestableNow,
  reserveFloor,
  harvestTarget,
  preemptibleCeiling,
}: {
  node: NodeDef;
  overviewNode: OverviewNode | undefined;
  gpuCount: number;
  modelCount: number;
  serviceCount: number;
  harvestableNow: number;
  reserveFloor: number;
  harvestTarget: number;
  preemptibleCeiling: number;
}) {
  const tone = nodeHealthTone(overviewNode);
  const harvestState =
    harvestableNow > 0 ? "Harvestable" : preemptibleCeiling > 0 || harvestTarget > 0 ? "Reserve-bound" : "Pinned";
  return (
    <article className="surface-instrument rounded-2xl border px-4 py-4">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <StatusDot tone={tone} pulse={tone === "warning"} />
            <p className="text-base font-medium">{node.name}</p>
          </div>
          <p className="text-sm text-muted-foreground">{node.role}</p>
        </div>
        <Badge variant="outline" className="font-mono text-xs">
          {node.ip}
        </Badge>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Badge variant={harvestableNow > 0 ? "secondary" : "outline"} className="text-[11px]">
          {harvestState}
        </Badge>
        <Badge variant="outline" className="text-[11px]">
          Reserve {reserveFloor}
        </Badge>
        <Badge variant="outline" className="text-[11px]">
          Harvest target {harvestTarget}
        </Badge>
        <Badge variant="outline" className="text-[11px]">
          Preemptible {preemptibleCeiling}
        </Badge>
      </div>
      <div className="mt-4 grid gap-3 text-sm text-muted-foreground sm:grid-cols-3">
        <div>
          <p className="page-eyebrow text-[10px]">Health</p>
          <p className="mt-1 text-foreground">
            {overviewNode ? `${overviewNode.healthyServices}/${overviewNode.totalServices} healthy` : "Awaiting overview"}
          </p>
        </div>
        <div>
          <p className="page-eyebrow text-[10px]">Compute</p>
          <p className="mt-1 text-foreground">{gpuCount} GPU{gpuCount === 1 ? "" : "s"}</p>
          <p className="mt-1 text-xs">{harvestableNow} harvestable now</p>
        </div>
        <div>
          <p className="page-eyebrow text-[10px]">Fabric</p>
          <p className="mt-1 text-foreground">{modelCount} lanes · {serviceCount} services</p>
        </div>
      </div>
    </article>
  );
}

function NodeSection({
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
  const tone = nodeHealthTone(overviewNode);
  const modelAliases = models.map((model) => `${model.alias}:${model.port}`);
  const { visible: visibleServices, remaining: remainingServices } = summarizeList(services, 8);

  return (
    <article className="surface-panel rounded-[28px] border px-5 py-5 sm:px-6">
      <div className="flex flex-col gap-4 border-b border-border/70 pb-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <StatusDot tone={tone} pulse={tone === "warning"} />
            <h3 className="font-heading text-2xl font-medium tracking-[-0.03em]">{node.name}</h3>
            <Badge variant="outline" className="font-mono text-xs">
              {node.ip}
            </Badge>
          </div>
          <p className="max-w-2xl text-sm text-muted-foreground">{node.role}</p>
        </div>
        <div className="grid gap-3 text-sm text-muted-foreground sm:grid-cols-2 lg:min-w-[18rem] lg:grid-cols-1">
          <div className="surface-metric rounded-2xl border px-4 py-3">
            <p className="page-eyebrow text-[10px]">Service posture</p>
            <p className="mt-1 text-foreground">
              {overviewNode ? `${overviewNode.healthyServices}/${overviewNode.totalServices} healthy` : "Overview pending"}
            </p>
            <p className="mt-1 text-xs">
              {overviewNode?.degradedServices ? `${overviewNode.degradedServices} degraded` : "No degraded services reported"}
            </p>
          </div>
          <div className="surface-metric rounded-2xl border px-4 py-3">
            <p className="page-eyebrow text-[10px]">Lane density</p>
            <p className="mt-1 text-foreground">{models.length} model lanes</p>
            <p className="mt-1 text-xs">{services.length} declared services</p>
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="surface-metric rounded-2xl border px-4 py-3">
          <p className="page-eyebrow text-[10px]">GPUs</p>
          <p className="mt-1 text-2xl font-semibold tracking-tight">{gpus.length}</p>
          <p className="mt-1 text-xs text-muted-foreground">Live DCGM-visible slots</p>
        </div>
        <div className="surface-metric rounded-2xl border px-4 py-3">
          <p className="page-eyebrow text-[10px]">Models</p>
          <p className="mt-1 text-2xl font-semibold tracking-tight">{models.length}</p>
          <p className="mt-1 text-xs text-muted-foreground">Inference backends on this node</p>
        </div>
        <div className="surface-metric rounded-2xl border px-4 py-3">
          <p className="page-eyebrow text-[10px]">Healthy services</p>
          <p className="mt-1 text-2xl font-semibold tracking-tight">{overviewNode?.healthyServices ?? "--"}</p>
          <p className="mt-1 text-xs text-muted-foreground">Current overview sample</p>
        </div>
        <div className="surface-metric rounded-2xl border px-4 py-3">
          <p className="page-eyebrow text-[10px]">Degraded</p>
          <p className="mt-1 text-2xl font-semibold tracking-tight">{overviewNode?.degradedServices ?? "--"}</p>
          <p className="mt-1 text-xs text-muted-foreground">Needs operator attention</p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(18rem,0.95fr)]">
        <div className="space-y-4">
          <section className="surface-instrument rounded-2xl border px-4 py-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <p className="page-eyebrow">Compute slots</p>
                <h4 className="mt-1 text-base font-medium">Live GPU posture</h4>
              </div>
              <Badge variant="secondary" className="text-xs">
                {gpus.length > 0 ? `${gpus.length} visible` : "No telemetry"}
              </Badge>
            </div>
            {gpus.length > 0 ? (
              <div className="grid gap-3 lg:grid-cols-2">
                {gpus.map((gpu) => (
                  <GpuSlot key={gpu.id} gpu={gpu} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No DCGM data is available for this node right now.</p>
            )}
          </section>

          <section className="surface-instrument rounded-2xl border px-4 py-4">
            <p className="page-eyebrow">Service coverage</p>
            <h4 className="mt-1 text-base font-medium">Declared operational surface</h4>
            <div className="mt-3 flex flex-wrap gap-2">
              {visibleServices.length > 0 ? (
                <>
                  {visibleServices.map((service) => (
                    <Badge key={service} variant="secondary" className="text-xs font-mono">
                      {service}
                    </Badge>
                  ))}
                  {remainingServices > 0 ? (
                    <Badge variant="outline" className="text-xs">
                      +{remainingServices} more
                    </Badge>
                  ) : null}
                </>
              ) : (
                <p className="text-sm text-muted-foreground">No declared services recorded for this node.</p>
              )}
            </div>
          </section>
        </div>

        <div className="space-y-4">
          <section className="surface-instrument rounded-2xl border px-4 py-4">
            <p className="page-eyebrow">Model lanes</p>
            <h4 className="mt-1 text-base font-medium">Inference entrypoints</h4>
            <div className="mt-3 flex flex-wrap gap-2">
              {modelAliases.length > 0 ? (
                modelAliases.map((alias) => (
                  <Badge key={alias} variant="outline" className="text-xs font-mono">
                    {alias}
                  </Badge>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No inference lanes declared on this node.</p>
              )}
            </div>
          </section>

          <section className="surface-instrument rounded-2xl border px-4 py-4">
            <p className="page-eyebrow">Operator note</p>
            <h4 className="mt-1 text-base font-medium">What this node is for</h4>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              {node.role}. Use this section as the quick-read ledger before jumping into node-specific logs or runtime intervention.
            </p>
          </section>
        </div>
      </div>
    </article>
  );
}

export function TopologyConsole({ nodes, models, nodeServices }: TopologyProps) {
  const gpuQuery = useQuery<GpuSnapshotResponse>({
    queryKey: queryKeys.gpuSnapshot,
    queryFn: () => requestJson("/api/gpu") as Promise<GpuSnapshotResponse>,
    ...liveQueryOptions(15_000),
  });

  const agentsQuery = useQuery<AgentsResponse>({
    queryKey: [...queryKeys.agents, "topology"],
    queryFn: () => requestJson("/api/agents") as Promise<AgentsResponse>,
    ...liveQueryOptions(30_000),
  });

  const overviewQuery = useQuery<OverviewSnapshot>({
    queryKey: [...queryKeys.overview, "topology"],
    queryFn: () => requestJson("/api/overview") as Promise<OverviewSnapshot>,
    ...liveQueryOptions(15_000),
  });

  const atlasQuery = useQuery<MasterAtlasRelationshipMap | MasterAtlasErrorResponse>({
    queryKey: [...queryKeys.systemMap, "master-atlas"],
    queryFn: () => requestJson("/api/master-atlas") as Promise<MasterAtlasRelationshipMap | MasterAtlasErrorResponse>,
    ...liveQueryOptions(30_000),
  });

  const gpuData = gpuQuery.data;
  const agents = agentsQuery.data?.agents ?? [];
  const overviewNodes = overviewQuery.data?.nodes ?? [];
  const atlasMap = atlasQuery.data && !("error" in atlasQuery.data) ? atlasQuery.data : null;

  const totalGpus = gpuData?.gpus.length ?? 0;
  const activeModels = models.length;
  const readyAgents = agents.filter((agent) => agent.status === "ready").length;
  const busyAgents = agents.filter((agent) => agent.status === "busy").length;
  const degradedAgents = agents.filter((agent) => agent.status !== "ready" && agent.status !== "busy").length;
  const stableNodes = overviewNodes.filter((node) => node.degradedServices === 0).length;
  const healthyServices = overviewNodes.reduce((sum, node) => sum + node.healthyServices, 0);
  const totalServices = overviewNodes.reduce((sum, node) => sum + node.totalServices, 0);
  const atlasTurnoverStatus = atlasMap?.turnover_readiness?.autonomous_turnover_status ?? null;
  const atlasProviderGate = atlasMap?.turnover_readiness?.provider_gate_state ?? null;
  const atlasWorkEconomy = atlasMap?.turnover_readiness?.work_economy_status ?? null;
  const atlasNextGate = atlasMap?.turnover_readiness?.next_gate ?? null;
  const atlasTopTask = atlasMap?.turnover_readiness?.top_dispatchable_autonomous_task_title ?? null;
  const atlasQueueCount = atlasMap?.autonomous_queue_summary?.queue_count ?? null;
  const atlasDispatchableCount = atlasMap?.autonomous_queue_summary?.dispatchable_queue_count ?? null;
  const atlasApprovalHeldCount = atlasMap?.autonomous_queue_summary?.blocked_queue_count ?? null;
  const atlasNodeCapacity = atlasMap?.node_capacity ?? [];
  const atlasNodeCapacityById = new Map(
    atlasNodeCapacity.flatMap((entry) => {
      const canonicalId = canonicalNodeId(entry.node_id);
      return [
        [canonicalId, entry] as const,
        [entry.node_id, entry] as const,
      ];
    })
  );
  const atlasDispatchLanes = atlasMap?.dispatch_lanes ?? [];
  const atlasLocalCompute = atlasMap?.quota_posture?.local_compute_capacity ?? null;
  const harvestableLaneSlots = atlasDispatchLanes.reduce((sum, lane) => sum + lane.harvestable_parallel_slots, 0);
  const reservedLaneSlots = atlasDispatchLanes.reduce((sum, lane) => sum + lane.reserved_parallel_slots, 0);
  const maxLaneSlots = atlasDispatchLanes.reduce((sum, lane) => sum + lane.max_parallel_slots, 0);
  const harvestableSlotCount = atlasLocalCompute?.harvestable_scheduler_slot_count ?? 0;
  const schedulerSlotCount = atlasLocalCompute?.scheduler_slot_count ?? 0;
  const schedulerQueueDepth = atlasLocalCompute?.scheduler_queue_depth ?? 0;
  const harvestableZoneCount = Object.values(atlasLocalCompute?.harvestable_by_zone ?? {}).filter((count) => count > 0).length;
  const isFetching = gpuQuery.isFetching || agentsQuery.isFetching || overviewQuery.isFetching || atlasQuery.isFetching;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Core"
        title="System Topology"
        description="Cluster nodes, compute posture, model lanes, and agent fabric. Start here when you need the shape of the system before drilling into a runtime or policy surface."
        actions={
          <Button
            variant="outline"
            onClick={() => {
              void gpuQuery.refetch();
              void agentsQuery.refetch();
              void overviewQuery.refetch();
              void atlasQuery.refetch();
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
            detail={nodes.map((node) => node.name).join(", ")}
            icon={<Server className="h-5 w-5" />}
          />
          <StatCard
            label="GPUs"
            value={totalGpus > 0 ? `${totalGpus}` : "--"}
            detail="Live DCGM and Prometheus surface"
            icon={<Cpu className="h-5 w-5" />}
          />
          <StatCard
            label="Model lanes"
            value={`${activeModels}`}
            detail={models.map((model) => model.alias).slice(0, 4).join(", ")}
            icon={<Layers className="h-5 w-5" />}
          />
          <StatCard
            label="Agents"
            value={agents.length > 0 ? `${readyAgents}/${agents.length}` : "--"}
            detail="Ready agents on the orchestration surface"
            icon={<Bot className="h-5 w-5" />}
            tone={agents.length > 0 && readyAgents === agents.length ? "success" : agents.length > 0 ? "warning" : undefined}
          />
        </div>
      </PageHeader>

      <section className="surface-panel rounded-[30px] border px-5 py-5 sm:px-6">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="page-eyebrow">Topology spine</p>
            <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">
              Operational shape before inventory
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              Use this strip as the first pass: stable nodes, service coverage, agent readiness, and the current atlas control posture in one read.
            </p>
          </div>
          <div className="surface-instrument rounded-2xl border px-4 py-3 lg:min-w-[20rem]">
            <p className="page-eyebrow text-[10px]">Control posture</p>
            <p className="mt-1 text-sm font-medium text-foreground">
              {atlasTurnoverStatus ?? "Atlas unavailable"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {atlasProviderGate ?? "unknown"} · {atlasWorkEconomy ?? "unknown"}
              {atlasNextGate ? ` · next gate ${atlasNextGate}` : ""}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              {atlasTopTask ? `Top task: ${atlasTopTask}` : "No top dispatchable task is currently recorded."}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              {atlasDispatchableCount ?? 0} dispatchable of {atlasQueueCount ?? 0} total
              {atlasApprovalHeldCount ? ` · ${atlasApprovalHeldCount} approval held` : ""}
            </p>
          </div>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="surface-metric rounded-2xl border px-4 py-3">
            <p className="page-eyebrow text-[10px]">Stable nodes</p>
            <p className="mt-1 text-2xl font-semibold tracking-tight">{stableNodes}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {overviewNodes.length > 0 ? `${overviewNodes.length - stableNodes} need attention` : "Awaiting overview"}
            </p>
          </div>
          <div className="surface-metric rounded-2xl border px-4 py-3">
            <p className="page-eyebrow text-[10px]">Service coverage</p>
            <p className="mt-1 text-2xl font-semibold tracking-tight">{healthyServices}/{totalServices || "--"}</p>
            <p className="mt-1 text-xs text-muted-foreground">Healthy versus total declared services</p>
          </div>
          <div className="surface-metric rounded-2xl border px-4 py-3">
            <p className="page-eyebrow text-[10px]">Compute slots</p>
            <p className="mt-1 text-2xl font-semibold tracking-tight">{totalGpus}</p>
            <p className="mt-1 text-xs text-muted-foreground">Live DCGM-visible slots across the fabric</p>
          </div>
          <div className="surface-metric rounded-2xl border px-4 py-3">
            <p className="page-eyebrow text-[10px]">Agent readiness</p>
            <p className="mt-1 text-2xl font-semibold tracking-tight">{readyAgents}/{agents.length || "--"}</p>
            <p className="mt-1 text-xs text-muted-foreground">{busyAgents} busy, {degradedAgents} attention</p>
          </div>
        </div>
        <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(18rem,0.85fr)]">
          <section className="surface-instrument rounded-2xl border px-4 py-4">
            <p className="page-eyebrow">Harvestable truth</p>
            <h3 className="mt-1 text-base font-medium">Live local compute economy</h3>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              This shows how much local compute is actually harvestable right now, and which lanes are still reserve-bound.
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="surface-metric rounded-2xl border px-4 py-3">
                <p className="page-eyebrow text-[10px]">Harvestable now</p>
                <p className="mt-1 text-2xl font-semibold tracking-tight">
                  {harvestableSlotCount}/{schedulerSlotCount || "--"}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">Scheduler slots currently open for harvest</p>
              </div>
              <div className="surface-metric rounded-2xl border px-4 py-3">
                <p className="page-eyebrow text-[10px]">Lane budget</p>
                <p className="mt-1 text-2xl font-semibold tracking-tight">
                  {harvestableLaneSlots}/{maxLaneSlots || "--"}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">{reservedLaneSlots} reserved floor still protected</p>
              </div>
              <div className="surface-metric rounded-2xl border px-4 py-3">
                <p className="page-eyebrow text-[10px]">Open zones</p>
                <p className="mt-1 text-2xl font-semibold tracking-tight">{harvestableZoneCount}</p>
                <p className="mt-1 text-xs text-muted-foreground">Zones with live harvestable capacity</p>
              </div>
              <div className="surface-metric rounded-2xl border px-4 py-3">
                <p className="page-eyebrow text-[10px]">Scheduler queue</p>
                <p className="mt-1 text-2xl font-semibold tracking-tight">{schedulerQueueDepth}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {schedulerQueueDepth > 0 ? "Queued demand is already present" : "Idle window is open right now"}
                </p>
              </div>
            </div>
            {atlasLocalCompute?.open_harvest_slot_target_ids?.length ? (
              <div className="mt-4 flex flex-wrap gap-2">
                {atlasLocalCompute.open_harvest_slot_target_ids.map((slotTargetId) => (
                  <Badge key={slotTargetId} variant="outline" className="text-[11px]">
                    {slotTargetId}
                  </Badge>
                ))}
              </div>
            ) : null}
          </section>

          <section className="surface-instrument rounded-2xl border px-4 py-4">
            <p className="page-eyebrow">Dispatch lanes</p>
            <h3 className="mt-1 text-base font-medium">Reserve and harvest posture</h3>
            <div className="mt-4 space-y-2">
              {atlasDispatchLanes.length > 0 ? (
                atlasDispatchLanes.slice(0, 6).map((lane) => {
                  const reserveBound = lane.harvestable_parallel_slots <= 0;
                  return (
                    <div key={lane.lane_id} className="surface-metric rounded-2xl border px-4 py-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-medium">{lane.provider_id}</p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {lane.reserve_class.replaceAll("_", " ")}
                          </p>
                        </div>
                        <Badge variant={reserveBound ? "outline" : "secondary"} className="text-[11px]">
                          {reserveBound ? "Reserve-bound" : "Harvestable"}
                        </Badge>
                      </div>
                      <p className="mt-2 text-xs text-muted-foreground">
                        {lane.harvestable_parallel_slots} harvestable · {lane.reserved_parallel_slots} reserved · {lane.max_parallel_slots} max
                      </p>
                    </div>
                  );
                })
              ) : (
                <p className="text-sm text-muted-foreground">Dispatch-lane posture will appear when the atlas feed is available.</p>
              )}
            </div>
          </section>
        </div>
      </section>

      <section className="surface-panel rounded-[30px] border px-5 py-5 sm:px-6">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="page-eyebrow">Cluster Ledger</p>
            <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">Node posture at a glance</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              Scan node health, compute density, and service coverage before you drill into the deeper control surfaces.
            </p>
          </div>
        </div>
        <div className="mt-5 grid gap-3 lg:grid-cols-2 2xl:grid-cols-4">
          {nodes.map((node) => {
            const nodeGpus = (gpuData?.gpus ?? []).filter((gpu) => {
              const gpuNode = gpu.node?.toLowerCase() ?? "";
              return gpuNode === node.id || gpuNode.startsWith(node.name.toLowerCase());
            });
            const nodeOverview = overviewNodes.find((overviewNode) => overviewNode.id === node.id || overviewNode.name.toLowerCase() === node.id);
            const nodeModels = models.filter((model) => model.nodeId === node.id);
            const services = nodeServices[node.id] ?? [];

            return (
              <NodeDigestCard
                key={node.id}
                node={node}
                overviewNode={nodeOverview}
                gpuCount={nodeGpus.length}
                modelCount={nodeModels.length}
                serviceCount={services.length}
                harvestableNow={atlasLocalCompute?.harvestable_by_zone?.[zoneIdForNode(node.id)] ?? 0}
                reserveFloor={
                  atlasNodeCapacityById.get(canonicalNodeId(node.id))?.utilization_targets
                    ?.interactive_reserve_floor_gpu_slots ?? 0
                }
                harvestTarget={
                  atlasNodeCapacityById.get(canonicalNodeId(node.id))?.utilization_targets
                    ?.background_harvest_target_gpu_slots ?? 0
                }
                preemptibleCeiling={
                  atlasNodeCapacityById.get(canonicalNodeId(node.id))?.utilization_targets
                    ?.max_noncritical_preemptible_gpu_slots ?? 0
                }
              />
            );
          })}
        </div>
      </section>

      <div className="grid gap-6 2xl:grid-cols-[minmax(0,1.45fr)_minmax(21rem,0.85fr)]">
        <section className="space-y-4">
          <div>
            <p className="page-eyebrow">Execution Fabric</p>
            <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">Node details</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              Each node keeps the same scan order: posture first, then compute slots, then service and model coverage.
            </p>
          </div>
          <div className="space-y-4">
            {nodes.map((node) => {
              const nodeGpus = (gpuData?.gpus ?? []).filter((gpu) => {
                const gpuNode = gpu.node?.toLowerCase() ?? "";
                return gpuNode === node.id || gpuNode.startsWith(node.name.toLowerCase());
              });
              const nodeOverview = overviewNodes.find((overviewNode) => overviewNode.id === node.id || overviewNode.name.toLowerCase() === node.id);
              const nodeModels = models.filter((model) => model.nodeId === node.id);
              return (
                <NodeSection
                  key={node.id}
                  node={node}
                  gpus={nodeGpus}
                  overviewNode={nodeOverview}
                  models={nodeModels}
                  services={nodeServices[node.id] ?? []}
                />
              );
            })}
          </div>
        </section>

        <section className="space-y-4">
          <div>
            <p className="page-eyebrow">Agent Fabric</p>
            <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">Orchestration layer</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Use this panel for the agent-side read before you jump into approvals, routing, or runtime intervention.
            </p>
          </div>
          <div className="surface-panel rounded-[28px] border px-5 py-5 sm:px-6">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="surface-metric rounded-2xl border px-4 py-3">
                <p className="page-eyebrow text-[10px]">Ready</p>
                <p className="mt-1 text-2xl font-semibold tracking-tight">{readyAgents}</p>
                <p className="mt-1 text-xs text-muted-foreground">Agents ready to work</p>
              </div>
              <div className="surface-metric rounded-2xl border px-4 py-3">
                <p className="page-eyebrow text-[10px]">Busy</p>
                <p className="mt-1 text-2xl font-semibold tracking-tight">{busyAgents}</p>
                <p className="mt-1 text-xs text-muted-foreground">Agents in active execution</p>
              </div>
              <div className="surface-metric rounded-2xl border px-4 py-3">
                <p className="page-eyebrow text-[10px]">Attention</p>
                <p className="mt-1 text-2xl font-semibold tracking-tight">{degradedAgents}</p>
                <p className="mt-1 text-xs text-muted-foreground">Non-ready agent surfaces</p>
              </div>
            </div>

            <div className="mt-5 space-y-2">
              {agentsQuery.isError ? (
                <EmptyState
                  title="No agent data"
                  description="Agent metadata will appear once FOUNDRY:9000 responds again."
                  className="py-6"
                />
              ) : agents.length > 0 ? (
                agents.map((agent) => (
                  <div
                    key={agent.id}
                    className="surface-instrument flex items-start gap-3 rounded-2xl border px-4 py-3"
                  >
                    <StatusDot tone={agentStatusTone(agent.status)} pulse={agent.status === "busy"} />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-medium">{agent.name}</p>
                        <Badge variant="outline" className="text-xs">
                          {agent.status}
                        </Badge>
                      </div>
                      <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{agent.description}</p>
                    </div>
                  </div>
                ))
              ) : (
                <EmptyState
                  title="No agent data"
                  description="The orchestration surface has not returned any agent metadata yet."
                  className="py-6"
                />
              )}
            </div>
          </div>
        </section>
      </div>

      <section className="space-y-4">
        <div>
            <p className="page-eyebrow">Control Relationships</p>
            <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">Authority and system map</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              This is the deeper control-plane view. It belongs below the node ledger so the page reads from operational posture into structural truth.
            </p>
          </div>
        {atlasMap ? (
          <MasterAtlasRelationshipPanel map={atlasMap} />
        ) : (
          <div className="surface-panel rounded-[28px] border px-5 py-5 sm:px-6">
            <EmptyState
              title="Control map unavailable"
              description="The master atlas relationship panel will appear when the compiled atlas is reachable."
              className="py-6"
            />
          </div>
        )}
      </section>
    </div>
  );
}
