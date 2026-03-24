"use client";

import { useQuery } from "@tanstack/react-query";
import {
  RefreshCcw,
  Network,
  Activity,
  DollarSign,
  BarChart3,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { requestJson } from "@/features/workforce/helpers";

interface RoutingLogEntry {
  task_id?: string;
  policy_class?: string;
  execution_lane?: string;
  provider?: string;
  outcome?: string;
  timestamp?: string;
}

interface ProviderStatus {
  name: string;
  status?: string;
  tasks_today?: number;
  avg_latency_ms?: number;
}

function policyBadgeVariant(policyClass: string | undefined) {
  switch (policyClass) {
    case "local_only":
      return "outline" as const;
    case "cli_review":
      return "secondary" as const;
    case "cloud_escalation":
      return "destructive" as const;
    default:
      return "default" as const;
  }
}

function outcomeBadgeVariant(outcome: string | undefined) {
  if (outcome === "success") return "outline" as const;
  if (outcome === "fail" || outcome === "failed") return "destructive" as const;
  return "default" as const;
}

function statusDot(status: string | undefined) {
  if (status === "healthy" || status === "active" || status === "online")
    return "bg-[color:var(--signal-success)]";
  if (status === "degraded" || status === "warning")
    return "bg-[color:var(--signal-warning)]";
  if (status === "down" || status === "offline" || status === "error")
    return "bg-[color:var(--signal-danger)]";
  return "bg-muted-foreground";
}

const COST_LINES = [
  { name: "Claude 20x Max", monthly: 150 },
  { name: "ChatGPT Pro", monthly: 200 },
  { name: "Gemini Pro", monthly: 35 },
  { name: "Local Inference", monthly: 0 },
];

const TOTAL_FIXED = COST_LINES.reduce((sum, line) => sum + line.monthly, 0);

export function RoutingConsole() {
  const logQuery = useQuery({
    queryKey: ["routing-log"],
    queryFn: async (): Promise<RoutingLogEntry[]> => {
      const data = await requestJson("/api/routing/log?limit=30");
      return (data?.entries ?? data ?? []) as RoutingLogEntry[];
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const providersQuery = useQuery({
    queryKey: ["routing-providers"],
    queryFn: async (): Promise<ProviderStatus[]> => {
      const data = await requestJson("/api/routing/providers");
      return (data?.providers ?? data ?? []) as ProviderStatus[];
    },
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  const logEntries = logQuery.data ?? [];
  const providers = providersQuery.data ?? [];

  const totalRouted = logEntries.length;
  const localOnly = logEntries.filter(
    (e) => e.policy_class === "local_only"
  ).length;
  const localPct =
    totalRouted > 0 ? `${((localOnly / totalRouted) * 100).toFixed(0)}%` : "--";
  const cliReviewed = logEntries.filter(
    (e) => e.policy_class === "cli_review"
  ).length;
  const cliPct =
    totalRouted > 0
      ? `${((cliReviewed / totalRouted) * 100).toFixed(0)}%`
      : "--";

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Intelligence"
        title="Routing & Cost"
        description="Provider routing decisions, execution lane visibility, and subscription cost tracking."
        attentionHref="/routing"
        actions={
          <Button
            variant="outline"
            onClick={() => {
              void logQuery.refetch();
              void providersQuery.refetch();
            }}
            disabled={logQuery.isFetching || providersQuery.isFetching}
          >
            <RefreshCcw
              className={`mr-2 h-4 w-4 ${
                logQuery.isFetching || providersQuery.isFetching
                  ? "animate-spin"
                  : ""
              }`}
            />
            Refresh
          </Button>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Tasks Routed"
            value={`${totalRouted}`}
            detail="Recent window"
            icon={<Network className="h-5 w-5" />}
          />
          <StatCard
            label="Local-Only"
            value={localPct}
            detail={`${localOnly} of ${totalRouted}`}
            icon={<Activity className="h-5 w-5" />}
            tone={
              localPct !== "--" && parseInt(localPct) >= 80
                ? "success"
                : "default"
            }
          />
          <StatCard
            label="CLI-Reviewed"
            value={cliPct}
            detail={`${cliReviewed} of ${totalRouted}`}
            icon={<BarChart3 className="h-5 w-5" />}
          />
          <StatCard
            label="Monthly Cost"
            value={`$${TOTAL_FIXED}`}
            detail="Fixed subscriptions"
            icon={<DollarSign className="h-5 w-5" />}
          />
        </div>
      </PageHeader>

      {/* Routing Log */}
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Routing Log</CardTitle>
          <CardDescription>
            Recent task routing decisions and outcomes.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {logEntries.length > 0 ? (
            <div className="space-y-1">
              {/* Header row */}
              <div className="surface-tile grid grid-cols-5 gap-2 rounded-xl px-4 py-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                <span>Task ID</span>
                <span>Policy</span>
                <span>Lane</span>
                <span>Provider</span>
                <span className="text-right">Outcome</span>
              </div>
              {logEntries.map((entry, idx) => (
                <div
                  key={entry.task_id ?? idx}
                  className="surface-tile grid grid-cols-5 items-center gap-2 rounded-xl px-4 py-2"
                >
                  <span className="truncate text-sm font-mono text-muted-foreground">
                    {entry.task_id
                      ? entry.task_id.length > 12
                        ? `${entry.task_id.slice(0, 12)}...`
                        : entry.task_id
                      : "--"}
                  </span>
                  <span>
                    <Badge variant={policyBadgeVariant(entry.policy_class)}>
                      {entry.policy_class ?? "unknown"}
                    </Badge>
                  </span>
                  <span className="text-sm">
                    {entry.execution_lane ?? "--"}
                  </span>
                  <span className="text-sm">{entry.provider ?? "--"}</span>
                  <span className="text-right">
                    <Badge variant={outcomeBadgeVariant(entry.outcome)}>
                      {entry.outcome ?? "pending"}
                    </Badge>
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No routing data"
              description="Routing log entries will appear as tasks are classified and executed."
              className="py-8"
            />
          )}
        </CardContent>
      </Card>

      {/* Provider Status */}
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Provider Status</CardTitle>
          <CardDescription>
            Active inference providers and their current health.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {providers.length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {providers.map((provider) => (
                <div
                  key={provider.name}
                  className="surface-instrument flex items-center gap-4 rounded-xl border px-4 py-3"
                >
                  <div
                    className={`h-2.5 w-2.5 shrink-0 rounded-full ${statusDot(provider.status)}`}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{provider.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {provider.tasks_today != null
                        ? `${provider.tasks_today} tasks today`
                        : "No tasks"}{" "}
                      &middot;{" "}
                      {provider.avg_latency_ms != null
                        ? `${provider.avg_latency_ms}ms avg`
                        : "-- latency"}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No provider data"
              description="Provider status will appear when providers are registered."
              className="py-8"
            />
          )}
        </CardContent>
      </Card>

      {/* Cost Summary */}
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Cost Summary</CardTitle>
          <CardDescription>
            Fixed monthly subscription costs and variable inference spend.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {COST_LINES.map((line) => (
              <div
                key={line.name}
                className="surface-instrument flex items-center justify-between rounded-xl border px-4 py-3"
              >
                <span className="text-sm font-medium">{line.name}</span>
                <span className="text-sm tabular-nums text-muted-foreground">
                  {line.monthly === 0
                    ? "Free"
                    : `~$${line.monthly}/mo`}
                </span>
              </div>
            ))}
            <div className="surface-instrument flex items-center justify-between rounded-xl border px-4 py-3">
              <span className="text-sm font-medium">Variable Cost</span>
              <span className="text-sm tabular-nums text-muted-foreground">
                $0
              </span>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-border/70 bg-background/30 px-4 py-3">
              <span className="text-sm font-semibold">Total</span>
              <span className="text-sm font-semibold tabular-nums">
                ~${TOTAL_FIXED}/mo fixed
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
