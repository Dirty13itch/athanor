"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowUpRight,
  Bot,
  Clock3,
  Cpu,
  ExternalLink,
  FolderKanban,
  Gauge,
  History,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AgentCrewBar } from "@/components/agent-crew-bar";
import { DailyBriefing } from "@/components/daily-briefing";
import { MediaGlance } from "@/components/media-glance";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { AttentionBanner } from "@/components/attention-banner";
import { GovernorQueuePanel } from "@/components/governor-queue-panel";
import { GoalsPanel } from "@/components/goals-panel";
import { LiveActivityPanel } from "@/components/live-activity-panel";
import { AgentWorkPanel } from "@/components/agent-work-panel";
import { GovernorCard } from "@/components/governor-card";
import { JudgePlaneCard } from "@/components/judge-plane-card";
import { LiveBadge } from "@/components/live-badge";
import { MetricChart } from "@/components/metric-chart";
import { ModelGovernanceCard } from "@/components/model-governance-card";
import { OperationsReadinessCard } from "@/components/operations-readiness-card";
import { PageHeader } from "@/components/page-header";
import { ProvingGroundCard } from "@/components/proving-ground-card";
import { SmartStack } from "@/components/smart-stack";
import { StatCard } from "@/components/stat-card";
import { StatusDot } from "@/components/status-dot";
import { SystemMapCard } from "@/components/system-map-card";
import { SystemPulse } from "@/components/system-pulse";
import { UnifiedStream } from "@/components/unified-stream";
import { WorkPlan } from "@/components/work-plan";
import { getOverview } from "@/lib/api";
import {
  agentThreadSchema,
  directChatSessionSchema,
  type OverviewSnapshot,
} from "@/lib/contracts";
import { compactText, formatLatency, formatPercent, formatRelativeTime, formatTimestamp } from "@/lib/format";
import { formatTemperatureF } from "@/lib/format";
import { LIVE_REFRESH_INTERVALS, liveQueryOptions } from "@/lib/live-updates";
import { queryKeys } from "@/lib/query-client";
import { readJsonStorage, STORAGE_KEYS } from "@/lib/state";
import { useLens } from "@/hooks/use-lens";
import type { SectionId } from "@/lib/lens";
import { QueenRosterCard } from "@/components/eoq/queen-roster-card";
import { RecentDialogueCard } from "@/components/eoq/recent-dialogue-card";
import { GenerationGalleryCard } from "@/components/eoq/generation-gallery-card";
import { CharacterMemoryCard } from "@/components/eoq/character-memory-card";
import { GameStatsCard } from "@/components/eoq/game-stats-card";

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

export function CommandCenter({ initialSnapshot }: { initialSnapshot: OverviewSnapshot }) {
  const { config: lensConfig } = useLens();
  const show = (group: string) => isCardVisible(group, lensConfig.sections);
  const [agentFilter, setAgentFilter] = useState<string | null>(null);

  const overviewQuery = useQuery({
    queryKey: queryKeys.overview,
    queryFn: getOverview,
    initialData: initialSnapshot,
    ...liveQueryOptions(LIVE_REFRESH_INTERVALS.overview),
  });
  const [recentContext] = useState<
    Array<{ id: string; title: string; route: string; updatedAt: string; type: string }>
  >(() => {
    const directSessions = directChatSessionSchema
      .array()
      .safeParse(readJsonStorage(STORAGE_KEYS.directChatSessions, []));
    const agentThreads = agentThreadSchema
      .array()
      .safeParse(readJsonStorage(STORAGE_KEYS.agentThreads, []));

    const nextContext = [
      ...(directSessions.success
        ? directSessions.data.map((session) => ({
            id: session.id,
            title: session.title,
            route: `/chat?session=${session.id}`,
            updatedAt: session.updatedAt,
            type: "model session",
          }))
        : []),
      ...(agentThreads.success
        ? agentThreads.data.map((thread) => ({
            id: thread.id,
            title: thread.title,
            route: `/agents?thread=${thread.id}&agent=${thread.agentId}`,
            updatedAt: thread.updatedAt,
            type: "agent thread",
          }))
        : []),
    ]
      .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))
      .slice(0, 5);
    return nextContext;
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

  return (
    <div className="command-center space-y-8">
      <SystemPulse sticky />
      <AgentCrewBar onAgentFilter={setAgentFilter} />

      {show("eoqContent") && (
        <div className="space-y-4">
          <QueenRosterCard />
          <GameStatsCard />
          <div className="grid gap-4 md:grid-cols-2">
            <RecentDialogueCard />
            <GenerationGalleryCard />
          </div>
          <CharacterMemoryCard />
        </div>
      )}

      <PageHeader
        eyebrow="Operations"
        title="Command Center"
        description="Athanor cluster posture, workforce state, first-class projects, and launch points for the operator workflow."
        actions={
          <>
            <LiveBadge updatedAt={snapshot.generatedAt} intervalMs={LIVE_REFRESH_INTERVALS.overview} />
            <Button asChild variant="outline">
              <Link href="/services?status=degraded">Open incidents</Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/workplanner">Open work planner</Link>
            </Button>
            <Button asChild>
              <Link href="/agents">Resume agents</Link>
            </Button>
          </>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <StatCard
            label="Cluster health"
            value={`${snapshot.summary.healthyServices}/${snapshot.summary.totalServices}`}
            detail={
              snapshot.summary.degradedServices > 0
                ? `${snapshot.summary.degradedServices} service issues need attention.`
                : "All monitored endpoints are reachable."
            }
            tone={snapshot.summary.degradedServices > 0 ? "warning" : "success"}
            icon={<Activity className="h-5 w-5" />}
          />
          <StatCard
            label="Average latency"
            value={formatLatency(snapshot.summary.averageLatencyMs)}
            detail={`Overview refreshed ${formatRelativeTime(snapshot.generatedAt)}.`}
            detailVolatile
            tone={
              snapshot.summary.averageLatencyMs !== null &&
              snapshot.summary.averageLatencyMs > 900
                ? "warning"
                : "default"
            }
            icon={<Gauge className="h-5 w-5" />}
          />
          <StatCard
            label="GPU utilization"
            value={formatPercent(snapshot.summary.averageGpuUtilization, 0)}
            detail={`${snapshot.hotspots.length} GPUs surfaced in the hotspot lane.`}
            tone={
              snapshot.summary.averageGpuUtilization !== null &&
              snapshot.summary.averageGpuUtilization >= 80
                ? "warning"
                : "success"
            }
            icon={<Cpu className="h-5 w-5" />}
          />
          <StatCard
            label="Agent readiness"
            value={`${snapshot.summary.readyAgents}/${snapshot.summary.totalAgents}`}
            detail={`${snapshot.summary.reachableBackends}/${snapshot.summary.totalBackends} inference backends reachable.`}
            tone={snapshot.summary.readyAgents > 0 ? "success" : "warning"}
            icon={<Bot className="h-5 w-5" />}
          />
          <StatCard
            label="Project platform"
            value={`${snapshot.summary.activeProjects}/${snapshot.projects.length}`}
            detail={`${snapshot.summary.firstClassProjects} first-class projects in the registry.`}
            tone={snapshot.summary.firstClassProjects > 0 ? "success" : "warning"}
            icon={<FolderKanban className="h-5 w-5" />}
          />
        </div>
      </PageHeader>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <DailyBriefing />
        <MediaGlance />
        <SmartStack />
        <Card className="surface-hero">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Clock3 className="h-5 w-5 text-primary" />
              Unified stream
            </CardTitle>
            <CardDescription>
              Cross-route activity across tasks, agents, and operator feedback.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <UnifiedStream limit={8} showFilters agentFilter={agentFilter} />
          </CardContent>
        </Card>
        <WorkPlan />
      </div>

      {show("priorityLane") && <div className="grid gap-4 xl:grid-cols-[1.35fr_1fr]">
        <Card className="surface-hero">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Sparkles className="h-5 w-5 text-primary" />
              Priority lane
            </CardTitle>
            <CardDescription>Incidents and live attention areas across the cluster.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {snapshot.alerts.map((alert) => (
              <Link
                key={alert.id}
                href={alert.href}
                  className="surface-tile flex items-start gap-3 rounded-2xl border p-4 transition hover:bg-accent/60"
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
            <CardDescription>Browser-local sessions and threads you touched most recently.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {recentContext.length > 0 ? (
              recentContext.map((item) => (
                <Link
                  key={item.id}
                  href={item.route}
                  className="surface-tile block rounded-2xl border p-4 transition hover:bg-accent/60"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{item.title}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                        {item.type}
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
      </div>}

      {show("workforceRow") && <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr_1fr]">
        <Card className="surface-hero">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Bot className="h-5 w-5 text-primary" />
              Workforce pulse
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
                href="/workplanner"
                className="surface-tile block rounded-2xl border p-4 transition hover:bg-accent/60"
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
              <div key={goal.id} className="surface-tile rounded-2xl border p-4">
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
              <div key={item.id} className="surface-tile rounded-2xl border p-4">
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
      </div>}

      {show("projectPlatform") && <div className="grid gap-4 xl:grid-cols-[1.35fr_1fr]">
        <Card className="surface-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <FolderKanban className="h-5 w-5 text-primary" />
              Project platform
            </CardTitle>
            <CardDescription>
              Athanor core, first-class tenants, and scaffolded future projects surfaced in one place.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {snapshot.projects.map((project) => (
              <div
                key={project.id}
              className="surface-tile rounded-2xl border p-4"
              >
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
                  <Badge variant="secondary">{project.agents.length} mapped agents</Badge>
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
          </CardContent>
        </Card>

        <SystemMapCard />
        <GovernorCard compact />
      </div>}

      {show("intelligenceRow") && <div className="grid gap-4 xl:grid-cols-2">
        <ModelGovernanceCard />
        <ProvingGroundCard compact />
        <JudgePlaneCard compact />
        <OperationsReadinessCard compact />
      </div>}

      {show("clusterPosture") && <div className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <Card className="surface-instrument">
          <CardHeader>
            <CardTitle className="text-lg">Cluster posture</CardTitle>
            <CardDescription>Availability and GPU load over the current history window.</CardDescription>
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
            <div className="grid gap-4 md:grid-cols-3">
              {snapshot.nodes.map((node) => (
                <div key={node.id} className="surface-tile rounded-2xl border p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-lg font-semibold">{node.name}</p>
                      <p className="font-mono text-xs text-muted-foreground">{node.ip}</p>
                    </div>
                    <StatusDot
                      tone={node.degradedServices > 0 ? "warning" : "healthy"}
                      pulse={node.degradedServices > 0}
                    />
                  </div>
                  <p className="mt-3 text-sm text-muted-foreground">{node.role}</p>
                  <div className="mt-4 grid gap-2 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Services</span>
                      <span>{node.healthyServices}/{node.totalServices}</span>
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
            <CardTitle className="text-lg">GPU hotspot summary</CardTitle>
            <CardDescription>Cards under the highest current demand.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {snapshot.hotspots.length > 0 ? (
              snapshot.hotspots.map((gpu) => (
                <Link
                  key={gpu.id}
                  href={`/gpu?highlight=${encodeURIComponent(gpu.id)}`}
                  className="surface-tile block rounded-2xl border p-4 transition hover:bg-accent/60"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{gpu.gpuName}</p>
                      <p className="mt-1 text-sm text-muted-foreground">{gpu.node}</p>
                    </div>
                    <Badge variant="outline">{formatPercent(gpu.utilization, 0)}</Badge>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
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
      </div>}

      {show("inferenceRow") && <div className="grid gap-4 xl:grid-cols-[1.15fr_1fr_1fr]">
        <Card className="surface-instrument">
          <CardHeader>
            <CardTitle className="text-lg">Inference posture</CardTitle>
            <CardDescription>Reachable backends, model inventory, and active launch paths.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {snapshot.backends.map((backend) => (
              <div key={backend.id} className="surface-tile rounded-2xl border p-4">
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
            <CardTitle className="text-lg">Agent capability surface</CardTitle>
            <CardDescription>Live agent roster and exposed tool counts.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {snapshot.agents.length > 0 ? (
              snapshot.agents.map((agent) => (
                <Link
                  key={agent.id}
                  href={`/agents?agent=${agent.id}`}
                  className="surface-tile block rounded-2xl border p-4 transition hover:bg-accent/60"
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
            <CardDescription>External tooling and common paths into the rest of the stack.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {snapshot.externalTools.map((tool) => (
              <a
                key={tool.id}
                href={tool.url}
                target="_blank"
                rel="noopener noreferrer"
                className="surface-tile flex items-center justify-between rounded-2xl border p-4 transition hover:bg-accent/60"
              >
                <div>
                  <p className="font-medium">{tool.label}</p>
                  <p className="text-sm text-muted-foreground">{tool.description}</p>
                </div>
                <ExternalLink className="h-4 w-4 text-muted-foreground" />
              </a>
            ))}

            <div className="surface-tile rounded-2xl border p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Snapshot time</p>
              <p className="mt-2 font-medium" data-volatile="true">
                {formatTimestamp(snapshot.generatedAt)}
              </p>
              <div className="mt-3 flex items-center gap-3 text-sm text-muted-foreground" data-volatile="true">
                <Clock3 className="h-4 w-4" />
                <span>{formatRelativeTime(snapshot.generatedAt)}</span>
              </div>
            </div>

            <div className="surface-tile rounded-2xl border p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Next actions</p>
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
      </div>}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="surface-instrument rounded-xl border p-2.5">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}
