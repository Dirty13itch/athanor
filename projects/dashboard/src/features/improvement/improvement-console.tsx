"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  RefreshCcw,
  Beaker,
  Play,
  TrendingUp,
  Rocket,
  Clock,
  CheckCircle2,
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
import { MetricChartClient } from "@/components/metric-chart-client";
import { formatRelativeTime } from "@/lib/format";
import { isOperatorSessionLocked, useOperatorSessionStatus } from "@/lib/operator-session";
import { requestJson, postWithoutBody } from "@/features/workforce/helpers";
import { useEffect, useState } from "react";

interface CycleSummary {
  last_cycle?: string;
  proposals_generated?: number;
  proposals_deployed?: number;
  cycle_duration_ms?: number;
  benchmark_pass_rate?: number;
}

interface Proposal {
  id?: string;
  agent_name?: string;
  variant_description?: string;
  status?: string;
  improvement_pct?: number | null;
}

interface BenchmarkEntry {
  date?: string;
  pass_count?: number;
  total_count?: number;
  pass_rate?: number;
}

function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function proposalBadgeVariant(status: string | undefined) {
  switch (status) {
    case "deployed":
      return "outline" as const;
    case "validated":
      return "secondary" as const;
    case "failed":
      return "destructive" as const;
    default:
      return "default" as const;
  }
}

export function ImprovementConsole() {
  const queryClient = useQueryClient();
  const operatorSession = useOperatorSessionStatus();
  const sessionLocked = isOperatorSessionLocked(operatorSession);
  const liveReadEnabled = !operatorSession.isPending && !sessionLocked;
  const [hydrated, setHydrated] = useState(false);
  const [triggeringCycle, setTriggeringCycle] = useState(false);
  const [triggeringBenchmarks, setTriggeringBenchmarks] = useState(false);

  useEffect(() => {
    setHydrated(true);
  }, []);

  const summaryQuery = useQuery({
    queryKey: ["improvement-summary"],
    queryFn: async (): Promise<CycleSummary> => {
      const data = await requestJson("/api/improvement/summary");
      return (data ?? {}) as CycleSummary;
    },
    enabled: liveReadEnabled,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  const proposalsQuery = useQuery({
    queryKey: ["improvement-proposals"],
    queryFn: async (): Promise<Proposal[]> => {
      const data = await requestJson("/api/improvement/proposals");
      return asArray<Proposal>(data?.proposals ?? data);
    },
    enabled: liveReadEnabled,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  const benchmarksQuery = useQuery({
    queryKey: ["improvement-benchmarks"],
    queryFn: async (): Promise<BenchmarkEntry[]> => {
      const data = await requestJson(
        "/api/improvement/benchmarks/history"
      );
      return asArray<BenchmarkEntry>(data?.entries ?? data?.benchmarks ?? data);
    },
    enabled: liveReadEnabled,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  const summary = summaryQuery.data ?? {};
  const proposals = proposalsQuery.data ?? [];
  const benchmarks = benchmarksQuery.data ?? [];
  const refreshing = hydrated && (summaryQuery.isFetching || proposalsQuery.isFetching || benchmarksQuery.isFetching);

  const deployedCount = proposals.filter((p) => p.status === "deployed").length;
  const passRate =
    summary.benchmark_pass_rate != null
      ? `${(summary.benchmark_pass_rate * 100).toFixed(0)}%`
      : benchmarks.length > 0 && benchmarks[benchmarks.length - 1]?.pass_rate != null
        ? `${((benchmarks[benchmarks.length - 1]?.pass_rate ?? 0) * 100).toFixed(0)}%`
        : "--";

  async function handleTriggerCycle() {
    setTriggeringCycle(true);
    try {
      await postWithoutBody(
        "/api/improvement/trigger"
      );
      void queryClient.invalidateQueries({
        queryKey: ["improvement-summary"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["improvement-proposals"],
      });
    } finally {
      setTriggeringCycle(false);
    }
  }

  async function handleTriggerBenchmarks() {
    setTriggeringBenchmarks(true);
    try {
      await postWithoutBody("/api/learning/benchmarks");
      void queryClient.invalidateQueries({
        queryKey: ["improvement-benchmarks"],
      });
    } finally {
      setTriggeringBenchmarks(false);
    }
  }

  const chartData = benchmarks.map((entry) => ({
    timestamp: entry.date ?? "",
    pass_rate: entry.pass_rate != null ? +(entry.pass_rate * 100).toFixed(1) : null,
  }));

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Intelligence"
        title="Self-Improvement"
        description="Nightly optimization cycles, prompt variant proposals, and benchmark health tracking."
        attentionHref="/improvement"
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={() => void handleTriggerCycle()}
              disabled={triggeringCycle}
            >
              <Play
                className={`mr-2 h-4 w-4 ${triggeringCycle ? "animate-spin" : ""}`}
              />
              Run Nightly Cycle
            </Button>
            <Button
              variant="outline"
              onClick={() => void handleTriggerBenchmarks()}
              disabled={triggeringBenchmarks}
            >
              <Beaker
                className={`mr-2 h-4 w-4 ${triggeringBenchmarks ? "animate-spin" : ""}`}
              />
              Run Benchmarks
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                void summaryQuery.refetch();
                void proposalsQuery.refetch();
                void benchmarksQuery.refetch();
              }}
              disabled={refreshing}
            >
              <RefreshCcw
                className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
              />
              Refresh
            </Button>
          </div>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Proposals"
            value={`${proposals.length}`}
            detail={`${deployedCount} deployed`}
            icon={<TrendingUp className="h-5 w-5" />}
          />
          <StatCard
            label="Deployed"
            value={`${deployedCount}`}
            detail="Active variants"
            icon={<Rocket className="h-5 w-5" />}
            tone={deployedCount > 0 ? "success" : "default"}
          />
          <StatCard
            label="Pass Rate"
            value={passRate}
            detail="Latest benchmark"
            icon={<CheckCircle2 className="h-5 w-5" />}
            tone={
              passRate !== "--" && parseInt(passRate) >= 90
                ? "success"
                : passRate !== "--" && parseInt(passRate) >= 70
                  ? "warning"
                  : "default"
            }
          />
          <StatCard
            label="Last Cycle"
            value={
              summary.last_cycle
                ? formatRelativeTime(summary.last_cycle)
                : "--"
            }
            detail={
              summary.cycle_duration_ms != null
                ? `${(summary.cycle_duration_ms / 1000).toFixed(1)}s`
                : "No cycle data"
            }
            icon={<Clock className="h-5 w-5" />}
          />
        </div>
      </PageHeader>

      {/* Nightly Cycle Results */}
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Nightly Cycle Results</CardTitle>
          <CardDescription>
            Last optimization cycle summary and outcome metrics.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {summary.last_cycle ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="surface-instrument rounded-xl border px-4 py-3">
                <p className="text-xs text-muted-foreground">Last Cycle</p>
                <p className="text-sm font-medium">
                  {formatRelativeTime(summary.last_cycle)}
                </p>
              </div>
              <div className="surface-instrument rounded-xl border px-4 py-3">
                <p className="text-xs text-muted-foreground">
                  Proposals Generated
                </p>
                <p className="text-sm font-medium">
                  {summary.proposals_generated ?? "--"}
                </p>
              </div>
              <div className="surface-instrument rounded-xl border px-4 py-3">
                <p className="text-xs text-muted-foreground">
                  Proposals Deployed
                </p>
                <p className="text-sm font-medium">
                  {summary.proposals_deployed ?? "--"}
                </p>
              </div>
              <div className="surface-instrument rounded-xl border px-4 py-3">
                <p className="text-xs text-muted-foreground">Cycle Duration</p>
                <p className="text-sm font-medium">
                  {summary.cycle_duration_ms != null
                    ? `${(summary.cycle_duration_ms / 1000).toFixed(1)}s`
                    : "--"}
                </p>
              </div>
            </div>
          ) : (
            <EmptyState
              title="No cycle data"
              description="Nightly cycle results will appear after the first optimization run."
              className="py-8"
            />
          )}
        </CardContent>
      </Card>

      {/* Proposals */}
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Proposals</CardTitle>
          <CardDescription>
            Prompt variant proposals and their deployment status.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {proposals.length > 0 ? (
            <div className="space-y-2">
              {proposals.map((proposal, idx) => (
                <div
                  key={proposal.id ?? idx}
                  className="surface-instrument flex items-center justify-between rounded-xl border px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium">
                      {proposal.agent_name ?? "Unknown Agent"}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {proposal.variant_description ?? "No description"}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    {proposal.improvement_pct != null && (
                      <span className="text-sm tabular-nums text-[color:var(--signal-success)]">
                        +{proposal.improvement_pct.toFixed(1)}%
                      </span>
                    )}
                    <Badge variant={proposalBadgeVariant(proposal.status)}>
                      {proposal.status ?? "pending"}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No proposals"
              description="Proposals will appear after a nightly cycle generates prompt variants."
              className="py-8"
            />
          )}
        </CardContent>
      </Card>

      {/* Benchmark History */}
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Benchmark History</CardTitle>
          <CardDescription>
            Pass rate trend across benchmark runs.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {benchmarks.length > 0 ? (
            <div className="space-y-4">
              {chartData.length >= 2 && (
                <MetricChartClient
                  data={chartData}
                  series={[
                    {
                      dataKey: "pass_rate",
                      label: "Pass Rate",
                      color: "oklch(0.75 0.18 145)",
                    },
                  ]}
                  mode="area"
                  valueSuffix="%"
                />
              )}
              <div className="space-y-1">
                {benchmarks.map((entry, idx) => (
                  <div
                    key={entry.date ?? idx}
                    className="surface-instrument flex items-center justify-between rounded-xl border px-4 py-2"
                  >
                    <span className="text-sm text-muted-foreground">
                      {entry.date
                        ? new Date(entry.date).toLocaleDateString([], {
                            month: "short",
                            day: "numeric",
                          })
                        : "--"}
                    </span>
                    <span className="text-sm tabular-nums">
                      {entry.pass_count ?? 0}/{entry.total_count ?? 0}
                    </span>
                    <span className="text-sm font-medium tabular-nums">
                      {entry.pass_rate != null
                        ? `${(entry.pass_rate * 100).toFixed(0)}%`
                        : "--"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <EmptyState
              title="No benchmark data"
              description="Benchmark history will appear after the first benchmark run."
              className="py-8"
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
