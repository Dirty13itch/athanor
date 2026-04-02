"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowUpRight,
  Bot,
  ChevronDown,
  Clock3,
  ExternalLink,
  FolderKanban,
  Gauge,
  History,
  Layers,
  Radio,
  Shield,
  Sparkles,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AgentCrewBar } from "@/components/agent-crew-bar";
import { DailyBriefing } from "@/components/daily-briefing";
import { LensTabs } from "@/components/lens-tabs";
import { MediaGlance } from "@/components/media-glance";
import { RightNowCard } from "@/components/right-now-card";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { GovernorCard } from "@/components/governor-card";
import { JudgePlaneCard } from "@/components/judge-plane-card";
import { LiveBadge } from "@/components/live-badge";
import { MetricChart } from "@/components/metric-chart";
import { ModelGovernanceCard } from "@/components/model-governance-card";
import { OperationsReadinessCard } from "@/components/operations-readiness-card";
import { PageHeader } from "@/components/page-header";
import { ProvingGroundCard } from "@/components/proving-ground-card";
import { SmartStack } from "@/components/smart-stack";
import { StatusDot } from "@/components/status-dot";
import { SystemMapCard } from "@/components/system-map-card";
import { SubscriptionBurn } from "@/components/subscription-burn";
import { SystemPulse } from "@/components/system-pulse";
import { UnifiedStream } from "@/components/unified-stream";
import { WorkPlan } from "@/components/work-plan";
import { getOverview } from "@/lib/api";
import {
  type OverviewSnapshot,
} from "@/lib/contracts";
import { compactText, formatLatency, formatPercent, formatRelativeTime, formatTimestamp } from "@/lib/format";
import { formatTemperatureF } from "@/lib/format";
import { LIVE_REFRESH_INTERVALS, liveQueryOptions } from "@/lib/live-updates";
import { useOperatorContext } from "@/lib/operator-context";
import { queryKeys } from "@/lib/query-client";
import { useLens } from "@/hooks/use-lens";
import { useSystemStream } from "@/hooks/use-system-stream";
import type { SectionId } from "@/lib/lens";
import { cn } from "@/lib/utils";
import { QueenRosterCard } from "@/components/eoq/queen-roster-card";
import { RecentDialogueCard } from "@/components/eoq/recent-dialogue-card";
import { GenerationGalleryCard } from "@/components/eoq/generation-gallery-card";
import { CharacterMemoryCard } from "@/components/eoq/character-memory-card";
import { GameStatsCard } from "@/components/eoq/game-stats-card";

/* ═══════════════════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════════════════ */

function buildTrendData(snapshot: OverviewSnapshot) {
  const map = new Map<string, { timestamp: string; services: number | null; gpu: number | null }>();

  for (const point of snapshot.serviceTrend) {
    map.set(point.timestamp, {
      timestamp: point.timestamp,
      services: point.value,
      gpu: null,
    });
  }

  for (const point of snapshot.gpuTrend) {
    const current = map.get(point.timestamp) ?? {
      timestamp: point.timestamp,
      services: null,
      gpu: null,
    };
    current.gpu = point.value;
    map.set(point.timestamp, current);
  }

  return Array.from(map.values()).sort((left, right) => left.timestamp.localeCompare(right.timestamp));
}

function formatProjectStatus(status: string) {
  return status.replace(/_/g, " ");
}

function isActiveProject(status: string) {
  return ["active", "active_development", "operational", "planning"].includes(status);
}

/** Maps command center card groups to lens section IDs. */
const CARD_SECTION_MAP: Record<string, SectionId[]> = {
  operationalRow: ["briefing", "watches", "smartstack", "stream", "workplan"],
  priorityLane: ["pulse"],
  recentContext: ["links"],
  workforceRow: ["workloads", "crew"],
  projectPlatform: ["links"],
  intelligenceRow: ["digest"],
  clusterPosture: ["gpus"],
  inferenceRow: ["links", "digest"],
  eoqContent: ["eoq-content"],
};

function isCardVisible(cardGroup: string, sections: SectionId[]): boolean {
  const mapped = CARD_SECTION_MAP[cardGroup];
  if (!mapped) return true;
  return mapped.some((s) => sections.includes(s));
}

/* ═══════════════════════════════════════════════════════════════════
   Inline sub-components
   ═══════════════════════════════════════════════════════════════════ */

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="surface-instrument rounded-xl border p-2 sm:p-2.5">
      <p className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground sm:text-[11px] sm:tracking-[0.18em]">{label}</p>
      <p className="mt-0.5 text-xs font-semibold sm:mt-1 sm:text-sm">{value}</p>
    </div>
  );
}

/** GPU utilization bar — thin horizontal fill with transition. */
function GpuBar({ value }: { value: number | null }) {
  const pct = value ?? 0;
  const color =
    pct >= 80
      ? "bg-[color:var(--signal-warning)]"
      : pct >= 1
        ? "bg-[color:var(--signal-success)]"
        : "bg-muted-foreground/30";
  return (
    <div className="h-1.5 w-full rounded-full bg-muted/40">
      <div
        className={cn("h-full rounded-full transition-all duration-700", color)}
        style={{ width: `${Math.min(pct, 100)}%` }}
      />
    </div>
  );
}

/** Node grid — stacked on mobile, 2x2 on sm+. */
function NodeGrid({ nodes }: { nodes: OverviewSnapshot["nodes"] }) {
  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      {nodes.map((node) => (
        <Link
          key={node.id}
          href={`/services?node=${node.id}`}
          className="surface-metric group flex flex-col gap-1.5 rounded-xl border p-2.5 sm:p-3 transition hover:bg-accent/60 min-h-[44px]"
        >
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <StatusDot
                tone={node.degradedServices > 0 ? "danger" : node.warningServices > 0 ? "warning" : "healthy"}
                pulse={node.degradedServices > 0 || node.warningServices > 0}
              />
              <span className="text-xs font-semibold truncate sm:text-sm">{node.name}</span>
            </div>
            <span className="font-mono text-[10px] text-muted-foreground shrink-0">{node.ip}</span>
          </div>
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span>
              {node.warningServices > 0 || node.degradedServices > 0
                ? `${node.healthyServices} ok · ${node.warningServices} warn · ${node.degradedServices} deg`
                : `${node.healthyServices}/${node.totalServices} svc`}
            </span>
            <span>{formatPercent(node.gpuUtilization, 0)} GPU</span>
          </div>
          <GpuBar value={node.gpuUtilization} />
        </Link>
      ))}
    </div>
  );
}

/** Inline metric pill for the command surface header row. */
function InlineMetric({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "success" | "warning" | "danger";
}) {
  const toneColor: Record<string, string> = {
    default: "text-foreground",
    success: "text-[color:var(--signal-success)]",
    warning: "text-[color:var(--signal-warning)]",
    danger: "text-[color:var(--signal-danger)]",
  };
  return (
    <div className="flex flex-col items-center gap-0.5 px-2 py-1.5 sm:px-3 sm:py-2">
      <span className={cn("text-base font-bold tabular-nums tracking-tight sm:text-lg", toneColor[tone])} data-volatile="true">
        {value}
      </span>
      <span className="text-[9px] uppercase tracking-[0.15em] text-muted-foreground sm:text-[10px] sm:tracking-[0.2em]">{label}</span>
    </div>
  );
}

/** Collapsible section for Zone 4 deep dive areas. */
function DeepDiveSection({
  title,
  icon,
  defaultOpen = false,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  return (
    <details className="group" open={defaultOpen || undefined}>
      <summary className="surface-panel flex cursor-pointer items-center gap-2.5 rounded-2xl border px-3 py-3 sm:gap-3 sm:px-5 sm:py-4 transition hover:bg-accent/60 list-none [&::-webkit-details-marker]:hidden min-h-[44px]">
        <span className="text-muted-foreground">{icon}</span>
        <span className="text-xs font-semibold tracking-tight sm:text-sm">{title}</span>
        <ChevronDown className="ml-auto h-4 w-4 text-muted-foreground transition-transform group-open:rotate-180" />
      </summary>
      <div className="mt-3 space-y-4">{children}</div>
    </details>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   Main export
   ═══════════════════════════════════════════════════════════════════ */

export function CommandCenter({ initialSnapshot }: { initialSnapshot: OverviewSnapshot }) {
  const { config: lensConfig } = useLens();
  const show = (group: string) => isCardVisible(group, lensConfig.sections);
  const [agentFilter, setAgentFilter] = useState<string | null>(null);
  const { data: stream } = useSystemStream();
  const { recentContext } = useOperatorContext();

  const overviewQuery = useQuery({
    queryKey: queryKeys.overview,
    queryFn: getOverview,
    initialData: initialSnapshot,
    ...liveQueryOptions(LIVE_REFRESH_INTERVALS.overview),
  });

  if (overviewQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Operations"
          title="Command Center"
          description="The overview snapshot failed to load."
        />
        <ErrorPanel
          description={
            overviewQuery.error instanceof Error
              ? overviewQuery.error.message
              : "Failed to load overview data."
          }
        />
      </div>
    );
  }

  const snapshot = overviewQuery.data ?? initialSnapshot;
  const trendData = buildTrendData(snapshot);

  /* Derive live stats from SSE when available, fall back to snapshot */
  const sseServicesUp = stream?.services.up ?? snapshot.summary.healthyServices;
  const sseServicesTotal = stream?.services.total ?? snapshot.summary.totalServices;
  const sseServicesDown = stream?.services.down ?? [];
  const degradedServices = snapshot.summary.degradedServices;
  const warningServices = snapshot.summary.warningServices;
  const sseAgentCount = stream?.agents.count ?? snapshot.summary.readyAgents;
  const sseTasksToday = stream?.tasks?.by_status.completed ?? snapshot.workforce.summary.completedTasks;
  const sseRunning = stream?.tasks?.currently_running ?? snapshot.workforce.summary.runningTasks;
  const sseGpuAvg =
    stream && stream.gpus.length > 0
      ? Math.round(stream.gpus.reduce((sum, g) => sum + g.utilization, 0) / stream.gpus.length)
      : snapshot.summary.averageGpuUtilization;

  return (
    <div className="space-y-3 sm:space-y-4 lg:space-y-5">
      {/* ═══ ZONE 1: Status Bar (sticky) ═══ */}
      <SystemPulse sticky />

      {/* ═══ ZONE 2: Command Surface ═══ */}
      <div className="surface-hero rounded-2xl border p-3 sm:p-4 md:p-6">
        {/* Header row: title + lens tabs + live badge */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
            <h1 className="text-lg font-bold tracking-tight sm:text-xl md:text-2xl">Athanor Command Center</h1>
            <LensTabs />
          </div>
          <LiveBadge updatedAt={snapshot.generatedAt} intervalMs={LIVE_REFRESH_INTERVALS.overview} />
        </div>

        {/* Metric strip — 4 key numbers, grid on mobile, flex row on sm+ */}
        <div className="mt-3 grid grid-cols-2 items-stretch gap-px rounded-xl border surface-instrument overflow-hidden sm:mt-4 sm:flex sm:flex-wrap sm:justify-center">
          <InlineMetric
            label="Services"
            value={`${sseServicesUp}/${sseServicesTotal}`}
            tone={degradedServices > 0 ? "danger" : warningServices > 0 || sseServicesDown.length > 0 ? "warning" : "success"}
          />
          <div className="hidden w-px self-stretch bg-border/40 sm:block" />
          <InlineMetric
            label="Agents"
            value={`${sseAgentCount}`}
            tone={sseAgentCount > 0 ? "success" : "warning"}
          />
          <div className="hidden w-px self-stretch bg-border/40 sm:block" />
          <InlineMetric
            label="GPU avg"
            value={formatPercent(sseGpuAvg, 0)}
            tone={sseGpuAvg !== null && sseGpuAvg >= 80 ? "warning" : "success"}
          />
          <div className="hidden w-px self-stretch bg-border/40 sm:block" />
          <InlineMetric
            label="Tasks"
            value={`${sseTasksToday}`}
            tone={sseRunning > 0 ? "success" : "default"}
          />
        </div>

        <div className="mt-4 grid gap-4 sm:mt-5 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="surface-panel rounded-2xl border p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge>Canonical front door</Badge>
              <Badge variant={degradedServices > 0 ? "destructive" : "outline"}>
                {degradedServices > 0 ? "attention required" : "stable posture"}
              </Badge>
            </div>
            <p className="mt-3 text-xl font-semibold tracking-tight">One portal, then deep links.</p>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              Use the command center for posture, approvals, autonomy blockers, drift, and internal
              operating loops. Jump out only when a specialist tool is the right surface.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button asChild size="sm">
                <Link href="/catalog">Open launchpad</Link>
              </Button>
              <Button asChild size="sm" variant="outline">
                <Link href="/services?status=degraded">View incidents</Link>
              </Button>
              <Button asChild size="sm" variant="outline">
                <Link href="/operator">Operator controls</Link>
              </Button>
            </div>
          </div>

          <div className="grid gap-2 sm:grid-cols-2">
            {snapshot.externalTools.slice(0, 4).map((tool) => (
              <a
                key={tool.id}
                href={tool.url}
                target="_blank"
                rel="noopener noreferrer"
                className="surface-tile flex min-h-[44px] items-start justify-between gap-3 rounded-xl border p-3 transition hover:bg-accent/60"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium">{tool.label}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{compactText(tool.description, 84)}</p>
                </div>
                <ExternalLink className="h-4 w-4 shrink-0 text-muted-foreground" />
              </a>
            ))}
          </div>
        </div>

        {/* Main command surface: left = Right Now, right = Nodes + Agents */}
        <div className="mt-4 grid gap-4 sm:mt-5 sm:gap-5 lg:grid-cols-[1.4fr_1fr]">
          {/* Left column: Right Now + alerts */}
          <div className="space-y-4">
            <RightNowCard snapshot={snapshot} />

            {/* Degraded alerts inline — pulsing red */}
            {snapshot.alerts.filter((a) => a.tone === "degraded").length > 0 && (
              <div className="space-y-2">
                {snapshot.alerts
                  .filter((a) => a.tone === "degraded")
                  .map((alert) => (
                    <Link
                      key={alert.id}
                      href={alert.href}
                      className="surface-tile flex items-center gap-2.5 rounded-xl border border-[color:var(--signal-danger)]/20 p-2.5 sm:gap-3 sm:p-3 transition hover:bg-accent/60 min-h-[44px]"
                    >
                      <StatusDot tone="danger" pulse className="shrink-0" />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium">{alert.title}</p>
                        <p className="mt-0.5 text-xs text-muted-foreground">{alert.description}</p>
                      </div>
                      <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                    </Link>
                  ))}
              </div>
            )}
          </div>

          {/* Right column: node grid + agent crew */}
          <div className="space-y-4">
            <NodeGrid nodes={snapshot.nodes} />
            <AgentCrewBar onAgentFilter={setAgentFilter} />
          </div>
        </div>
      </div>

      {/* ═══ EoBQ Content (lens-gated) ═══ */}
      {show("eoqContent") && (
        <div className="space-y-4">
          <QueenRosterCard />
          <GameStatsCard />
          <div className="grid gap-3 sm:gap-4 md:grid-cols-2">
            <RecentDialogueCard />
            <GenerationGalleryCard />
          </div>
          <CharacterMemoryCard />
        </div>
      )}

      {/* ═══ ZONE 3: Operational Grid ═══ */}
      <div className="grid gap-3 sm:gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* Column 1: Activity Stream */}
        <Card className="surface-panel">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Radio className="h-4 w-4 text-primary" />
              Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <UnifiedStream limit={8} showFilters agentFilter={agentFilter} />
          </CardContent>
        </Card>

        {/* Column 2: Work Plan + Goals stacked */}
        <div className="space-y-4">
          <WorkPlan />
          <SmartStack />
        </div>

        {/* Column 3: Media + Furnace + Briefing stacked */}
        <div className="space-y-4">
          <MediaGlance />
          <SubscriptionBurn />
          <DailyBriefing />
        </div>
      </div>

      {/* Quick actions bar */}
      <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
        <Button asChild variant="outline" size="sm">
          <Link href="/services?status=degraded">Incidents</Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link href="/backlog">Backlog</Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link href="/gallery">Gallery</Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link href="/chat">Chat</Link>
        </Button>
        <Button asChild size="sm">
          <Link href="/agents">Agents</Link>
        </Button>
      </div>

      {/* ═══ ZONE 4: Deep Dive (collapsible) ═══ */}

      {/* Projects */}
      {show("projectPlatform") && (
        <DeepDiveSection title="Projects" icon={<FolderKanban className="h-4 w-4" />} defaultOpen>
          <div className="grid gap-3 sm:gap-4 lg:grid-cols-2">
            <div className="space-y-3">
              {snapshot.projects.map((project) => (
                <div key={project.id} className="surface-tile rounded-2xl border p-3 sm:p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium">{project.name}</p>
                        {project.firstClass ? <Badge>First-class</Badge> : null}
                        <Badge variant="outline">{project.kind}</Badge>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{project.headline}</p>
                    </div>
                    <Badge variant={isActiveProject(project.status) ? "outline" : "secondary"}>
                      {formatProjectStatus(project.status)}
                    </Badge>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    <Badge variant="secondary">{project.needsCount} open needs</Badge>
                    <Badge variant="secondary">{project.agents.length} agents</Badge>
                    <Badge variant="secondary">lens: {project.lens}</Badge>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    {project.operatorChain.map((operator) => (
                      <span
                        key={operator}
                        className="surface-metric rounded-full border px-2 py-1"
                      >
                        {operator}
                      </span>
                    ))}
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button asChild size="sm" variant="outline">
                      <Link href={project.primaryRoute}>Open workspace</Link>
                    </Button>
                    {project.externalUrl ? (
                      <Button asChild size="sm" variant="ghost">
                        <a href={project.externalUrl} target="_blank" rel="noopener noreferrer">
                          Open app
                        </a>
                      </Button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
            <SystemMapCard />
          </div>
        </DeepDiveSection>
      )}

      {/* Cluster Posture */}
      {show("clusterPosture") && (
        <DeepDiveSection title="Cluster Posture" icon={<Gauge className="h-4 w-4" />}>
          <div className="grid gap-3 sm:gap-4 lg:grid-cols-[1.5fr_1fr]">
            <Card className="surface-instrument">
              <CardHeader>
                <CardTitle className="text-lg">Availability & GPU trend</CardTitle>
                <CardDescription>Service availability and GPU load over the history window.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <MetricChart
                  data={trendData}
                  series={[
                    { dataKey: "services", label: "Service availability", color: "var(--chart-1)" },
                    { dataKey: "gpu", label: "GPU utilization", color: "var(--chart-2)" },
                  ]}
                  mode="line"
                  valueSuffix="%"
                />
                <div className="grid gap-3 sm:gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {snapshot.nodes.map((node) => (
                    <div key={node.id} className="surface-tile rounded-2xl border p-3 sm:p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-lg font-semibold">{node.name}</p>
                          <p className="font-mono text-xs text-muted-foreground">{node.ip}</p>
                        </div>
                        <StatusDot
                          tone={node.degradedServices > 0 ? "danger" : node.warningServices > 0 ? "warning" : "healthy"}
                          pulse={node.degradedServices > 0 || node.warningServices > 0}
                        />
                      </div>
                      <p className="mt-3 text-sm text-muted-foreground">{node.role}</p>
                      <div className="mt-4 grid gap-2 text-sm">
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground">Services</span>
                          <span>{node.healthyServices} ok / {node.warningServices + node.degradedServices} watch</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground">Latency</span>
                          <span>{formatLatency(node.averageLatencyMs)}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground">GPU load</span>
                          <span>{formatPercent(node.gpuUtilization, 0)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="surface-instrument">
              <CardHeader>
                <CardTitle className="text-lg">GPU hotspots</CardTitle>
                <CardDescription>Cards under the highest current demand.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {snapshot.hotspots.length > 0 ? (
                  snapshot.hotspots.map((gpu) => (
                    <Link
                      key={gpu.id}
                      href={`/gpu?highlight=${encodeURIComponent(gpu.id)}`}
                      className="surface-tile block rounded-2xl border p-3 sm:p-4 transition hover:bg-accent/60"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="font-medium">{gpu.gpuName}</p>
                          <p className="mt-1 text-sm text-muted-foreground">{gpu.node}</p>
                        </div>
                        <Badge variant="outline">{formatPercent(gpu.utilization, 0)}</Badge>
                      </div>
                      <div className="mt-2 grid grid-cols-3 gap-1.5 text-xs sm:mt-3 sm:gap-2 sm:text-sm">
                        <Metric label="Temp" value={formatTemperatureF(gpu.temperatureC)} />
                        <Metric label="Power" value={gpu.powerW === null ? "--" : `${Math.round(gpu.powerW)}W`} />
                        <Metric
                          label="VRAM"
                          value={
                            gpu.memoryTotalMiB
                              ? formatPercent(((gpu.memoryUsedMiB ?? 0) / gpu.memoryTotalMiB) * 100, 0)
                              : "--"
                          }
                        />
                      </div>
                    </Link>
                  ))
                ) : (
                  <EmptyState
                    title="No GPU telemetry"
                    description="Prometheus did not return any active GPU metrics for the overview snapshot."
                  />
                )}
              </CardContent>
            </Card>
          </div>
        </DeepDiveSection>
      )}

      {/* Inference */}
      {show("inferenceRow") && (
        <DeepDiveSection title="Inference & Agent Capabilities" icon={<Layers className="h-4 w-4" />}>
          <div className="grid gap-3 sm:gap-4 md:grid-cols-2 xl:grid-cols-[1.15fr_1fr_1fr]">
            <Card className="surface-instrument">
              <CardHeader>
                <CardTitle className="text-lg">Inference posture</CardTitle>
                <CardDescription>Reachable backends, model inventory, and active launch paths.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {snapshot.backends.map((backend) => (
                  <div key={backend.id} className="surface-tile rounded-2xl border p-3 sm:p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <StatusDot tone={backend.reachable ? "healthy" : "danger"} pulse={!backend.reachable} />
                          <p className="font-medium">{backend.name}</p>
                        </div>
                        <p className="mt-1 text-sm text-muted-foreground">{backend.description}</p>
                      </div>
                      <Badge variant={backend.reachable ? "outline" : "destructive"}>
                        {backend.reachable ? `${backend.modelCount} models` : "offline"}
                      </Badge>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {backend.models.slice(0, 4).map((model) => (
                        <Badge key={model} variant="secondary" className="max-w-full truncate">
                          {model.replace(/^\/models\//, "")}
                        </Badge>
                      ))}
                      {backend.models.length > 4 ? (
                        <Badge variant="secondary">+{backend.models.length - 4} more</Badge>
                      ) : null}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card className="surface-panel">
              <CardHeader>
                <CardTitle className="text-lg">Agent capabilities</CardTitle>
                <CardDescription>Live agent roster and exposed tool counts.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {snapshot.agents.length > 0 ? (
                  snapshot.agents.map((agent) => (
                    <Link
                      key={agent.id}
                      href={`/agents?agent=${agent.id}`}
                      className="surface-tile block rounded-2xl border p-3 sm:p-4 transition hover:bg-accent/60"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate font-medium">{agent.name}</p>
                          <p className="mt-1 text-sm text-muted-foreground">{agent.description}</p>
                        </div>
                        <Badge variant={agent.status === "ready" ? "outline" : "secondary"}>
                          {agent.status}
                        </Badge>
                      </div>
                      <p className="mt-3 text-xs text-muted-foreground">{agent.tools.length} tools</p>
                    </Link>
                  ))
                ) : (
                  <EmptyState
                    title="No agent metadata"
                    description="The live agent roster could not be loaded into the overview snapshot."
                  />
                )}
              </CardContent>
            </Card>

            <Card className="surface-panel">
              <CardHeader>
                <CardTitle className="text-lg">Launchpad</CardTitle>
                <CardDescription>External tools and quick paths.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {snapshot.externalTools.map((tool) => (
                  <a
                    key={tool.id}
                    href={tool.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="surface-tile flex items-center justify-between rounded-2xl border p-3 sm:p-4 transition hover:bg-accent/60"
                  >
                    <div>
                      <p className="font-medium">{tool.label}</p>
                      <p className="text-sm text-muted-foreground">{tool.description}</p>
                    </div>
                    <ExternalLink className="h-4 w-4 text-muted-foreground" />
                  </a>
                ))}

                <div className="surface-tile rounded-2xl border p-3 sm:p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Snapshot time</p>
                  <p className="mt-2 font-medium" data-volatile="true">
                    {formatTimestamp(snapshot.generatedAt)}
                  </p>
                  <div className="mt-3 flex items-center gap-3 text-sm text-muted-foreground" data-volatile="true">
                    <Clock3 className="h-4 w-4" />
                    <span>{formatRelativeTime(snapshot.generatedAt)}</span>
                  </div>
                </div>

                <div className="surface-tile rounded-2xl border p-3 sm:p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Quick links</p>
                  <div className="mt-3 space-y-2">
                    <Link href="/chat" className="flex items-center justify-between rounded-xl px-2 py-2 text-sm hover:bg-accent">
                      Direct model chat
                      <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
                    </Link>
                    <Link href="/gpu" className="flex items-center justify-between rounded-xl px-2 py-2 text-sm hover:bg-accent">
                      GPU deep dive
                      <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
                    </Link>
                    <Link href="/services" className="flex items-center justify-between rounded-xl px-2 py-2 text-sm hover:bg-accent">
                      Service control surface
                      <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
                    </Link>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </DeepDiveSection>
      )}

      {/* Priority Lane + Recent Context */}
      {show("priorityLane") && (
        <DeepDiveSection title="Priority Lane & Recent Context" icon={<Sparkles className="h-4 w-4" />}>
          <div className="grid gap-3 sm:gap-4 lg:grid-cols-[1.35fr_1fr]">
            <Card className="surface-hero">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Zap className="h-5 w-5 text-primary" />
                  Incidents & attention
                </CardTitle>
                <CardDescription>Live attention areas across the cluster.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {snapshot.alerts.map((alert) => (
                  <Link
                    key={alert.id}
                    href={alert.href}
                    className="surface-tile flex items-start gap-3 rounded-2xl border p-3 sm:p-4 transition hover:bg-accent/60"
                  >
                    <StatusDot
                      tone={
                        alert.tone === "healthy"
                          ? "healthy"
                          : alert.tone === "degraded"
                            ? "danger"
                            : alert.tone
                      }
                      pulse={alert.tone === "degraded"}
                      className="mt-1"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="font-medium">{alert.title}</p>
                      <p className="mt-1 text-sm text-muted-foreground">{alert.description}</p>
                    </div>
                    <ArrowUpRight className="mt-1 h-4 w-4 text-muted-foreground" />
                  </Link>
                ))}
              </CardContent>
            </Card>

            <Card className="surface-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <History className="h-5 w-5 text-primary" />
                  Recent operator context
                </CardTitle>
                <CardDescription>Server-backed sessions and threads you touched most recently.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {recentContext.length > 0 ? (
                  recentContext.slice(0, 5).map((item) => (
                    <Link
                      key={item.id}
                      href={item.route}
                      className="surface-tile block rounded-2xl border p-3 sm:p-4 transition hover:bg-accent/60"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate font-medium">{item.title}</p>
                          <p className="mt-1 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                            {item.type === "direct_chat_session" ? "model session" : "agent thread"}
                          </p>
                        </div>
                        <Badge variant="outline" data-volatile="true">
                          {formatRelativeTime(item.updatedAt)}
                        </Badge>
                      </div>
                    </Link>
                  ))
                ) : (
                  <EmptyState
                    title="No recent sessions yet"
                    description="Recent direct-chat sessions and agent threads will appear here once you start working through the console."
                  />
                )}
              </CardContent>
            </Card>
          </div>
        </DeepDiveSection>
      )}

      {/* Workforce */}
      {show("workforceRow") && (
        <DeepDiveSection title="Workforce Pulse" icon={<Bot className="h-4 w-4" />}>
          <div className="grid gap-3 sm:gap-4 md:grid-cols-2 xl:grid-cols-[1.1fr_0.9fr_1fr]">
            <Card className="surface-hero">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Bot className="h-5 w-5 text-primary" />
                  Queue & approvals
                </CardTitle>
                <CardDescription>Queue pressure, approvals, and active work across the org.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <Metric label="Queued" value={`${snapshot.workforce.summary.pendingTasks + snapshot.workforce.summary.runningTasks}`} />
                  <Metric label="Approvals" value={`${snapshot.workforce.summary.pendingApprovals}`} />
                  <Metric label="Goals" value={`${snapshot.workforce.summary.activeGoals}`} />
                  <Metric
                    label="Trust"
                    value={
                      snapshot.workforce.summary.avgTrustScore === null
                        ? "--"
                        : `${Math.round(snapshot.workforce.summary.avgTrustScore * 100)}%`
                    }
                  />
                </div>
                {snapshot.workforce.tasks.slice(0, 3).map((task) => (
                  <Link
                    key={task.id}
                    href="/backlog"
                    className="surface-tile block rounded-2xl border p-3 sm:p-4 transition hover:bg-accent/60"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={task.status === "pending_approval" ? "destructive" : "outline"}>
                        {task.status.replace(/_/g, " ")}
                      </Badge>
                      <Badge variant="secondary">{task.agentId}</Badge>
                      {task.projectId ? <Badge variant="outline">{task.projectId}</Badge> : null}
                    </div>
                    <p className="mt-2 text-sm">{compactText(task.prompt, 140)}</p>
                  </Link>
                ))}
              </CardContent>
            </Card>

            <Card className="surface-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <FolderKanban className="h-5 w-5 text-primary" />
                  Active goals
                </CardTitle>
                <CardDescription>Steering constraints currently shaping the work planner.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {snapshot.workforce.goals.slice(0, 3).map((goal) => (
                  <div key={goal.id} className="surface-tile rounded-2xl border p-3 sm:p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">{goal.priority}</Badge>
                      <Badge variant="secondary">{goal.agentId === "global" ? "All agents" : goal.agentId}</Badge>
                    </div>
                    <p className="mt-2 text-sm">{goal.text}</p>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card className="surface-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Clock3 className="h-5 w-5 text-primary" />
                  Workspace broadcast
                </CardTitle>
                <CardDescription>Top salience items moving through the shared workspace.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {snapshot.workforce.workspace.broadcast.slice(0, 3).map((item) => (
                  <div key={item.id} className="surface-tile rounded-2xl border p-3 sm:p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium">{item.sourceAgent}</p>
                      <Badge variant="outline">{item.priority}</Badge>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">{compactText(item.content, 128)}</p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      salience {item.salience.toFixed(2)}
                      {item.projectId ? ` · ${item.projectId}` : ""}
                    </p>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </DeepDiveSection>
      )}

      {/* Governance */}
      {show("intelligenceRow") && (
        <DeepDiveSection title="Governance" icon={<Shield className="h-4 w-4" />}>
          <div className="grid gap-3 sm:gap-4 md:grid-cols-2">
            <GovernorCard compact />
            <ModelGovernanceCard />
            <ProvingGroundCard compact />
            <JudgePlaneCard compact />
            <OperationsReadinessCard compact />
          </div>
        </DeepDiveSection>
      )}
    </div>
  );
}
