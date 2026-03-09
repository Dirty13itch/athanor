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
  Gauge,
  History,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { MetricChart } from "@/components/metric-chart";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { StatusDot } from "@/components/status-dot";
import { getOverview } from "@/lib/api";
import {
  agentThreadSchema,
  directChatSessionSchema,
  type OverviewSnapshot,
} from "@/lib/contracts";
import { formatLatency, formatPercent, formatRelativeTime, formatTimestamp } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import { readJsonStorage, STORAGE_KEYS } from "@/lib/state";

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

export function CommandCenter({ initialSnapshot }: { initialSnapshot: OverviewSnapshot }) {
  const overviewQuery = useQuery({
    queryKey: queryKeys.overview,
    queryFn: getOverview,
    initialData: initialSnapshot,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
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
    <div className="space-y-8">
      <PageHeader
        eyebrow="Operations"
        title="Command Center"
        description="Athanor cluster posture, incidents, trends, and launch points for the core operator workflows."
        actions={
          <>
            <Button asChild variant="outline">
              <Link href="/services?status=degraded">Open incidents</Link>
            </Button>
            <Button asChild>
              <Link href="/agents">Resume agents</Link>
            </Button>
          </>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
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
        </div>
      </PageHeader>

      <div className="grid gap-4 xl:grid-cols-[1.35fr_1fr]">
        <Card className="border-border/70 bg-card/70">
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
                className="flex items-start gap-3 rounded-2xl border border-border/70 bg-background/20 p-4 transition hover:bg-accent/50"
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

        <Card className="border-border/70 bg-card/70">
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
                  className="block rounded-2xl border border-border/70 bg-background/20 p-4 transition hover:bg-accent/50"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{item.title}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                        {item.type}
                      </p>
                    </div>
                    <Badge variant="outline">{formatRelativeTime(item.updatedAt)}</Badge>
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

      <div className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <Card className="border-border/70 bg-card/70">
          <CardHeader>
            <CardTitle className="text-lg">Cluster posture</CardTitle>
            <CardDescription>Availability and GPU load over the current history window.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <MetricChart
              data={trendData}
              series={[
                { dataKey: "services", label: "Service availability", color: "#f5c86d" },
                { dataKey: "gpu", label: "GPU utilization", color: "#78d1f2" },
              ]}
              mode="line"
              valueSuffix="%"
            />
            <div className="grid gap-4 md:grid-cols-3">
              {snapshot.nodes.map((node) => (
                <div key={node.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
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

        <Card className="border-border/70 bg-card/70">
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
                  className="block rounded-2xl border border-border/70 bg-background/20 p-4 transition hover:bg-accent/50"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{gpu.gpuName}</p>
                      <p className="mt-1 text-sm text-muted-foreground">{gpu.node}</p>
                    </div>
                    <Badge variant="outline">{formatPercent(gpu.utilization, 0)}</Badge>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
                    <Metric label="Temp" value={gpu.temperatureC === null ? "--" : `${Math.round(gpu.temperatureC)}C`} />
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

      <div className="grid gap-4 xl:grid-cols-[1.15fr_1fr_1fr]">
        <Card className="border-border/70 bg-card/70">
          <CardHeader>
            <CardTitle className="text-lg">Inference posture</CardTitle>
            <CardDescription>Reachable backends, model inventory, and active launch paths.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {snapshot.backends.map((backend) => (
              <div key={backend.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
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

        <Card className="border-border/70 bg-card/70">
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
                  className="block rounded-2xl border border-border/70 bg-background/20 p-4 transition hover:bg-accent/50"
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

        <Card className="border-border/70 bg-card/70">
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
                className="flex items-center justify-between rounded-2xl border border-border/70 bg-background/20 p-4 transition hover:bg-accent/50"
              >
                <div>
                  <p className="font-medium">{tool.label}</p>
                  <p className="text-sm text-muted-foreground">{tool.description}</p>
                </div>
                <ExternalLink className="h-4 w-4 text-muted-foreground" />
              </a>
            ))}

            <div className="rounded-2xl border border-border/70 bg-background/20 p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Snapshot time</p>
              <p className="mt-2 font-medium">{formatTimestamp(snapshot.generatedAt)}</p>
              <div className="mt-3 flex items-center gap-3 text-sm text-muted-foreground">
                <Clock3 className="h-4 w-4" />
                <span>{formatRelativeTime(snapshot.generatedAt)}</span>
              </div>
            </div>

            <div className="rounded-2xl border border-border/70 bg-background/20 p-4">
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
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/40 p-2">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}
