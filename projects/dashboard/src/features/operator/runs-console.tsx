"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Gauge, RefreshCcw, ShieldCheck, Waypoints } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { formatRelativeTime } from "@/lib/format";
import { requestJson } from "@/features/workforce/helpers";
import type { ExecutionResultProjection, ExecutionReviewProjection } from "@/lib/contracts";

type RunStatus = "all" | "queued" | "running" | "waiting_approval" | "blocked" | "completed" | "failed" | "cancelled";

interface OperatorRun {
  id: string;
  task_id: string;
  backlog_id: string;
  agent_id: string;
  workload_class: string;
  provider_lane: string;
  runtime_lane: string;
  policy_class: string;
  status: Exclude<RunStatus, "all">;
  summary: string;
  created_at: number;
  updated_at: number;
  completed_at: number;
  step_count: number;
  approval_pending: boolean;
  latest_attempt?: {
    id: string;
    runtime_host: string;
    status: string;
    heartbeat_at: number;
  };
  approvals?: Array<{ id: string; status: string; privilege_class: string }>;
}

interface RunsFeedStatus {
  available?: boolean;
  degraded?: boolean;
  detail?: string;
  source?: string;
}

interface RunsFeedPayload extends RunsFeedStatus {
  runs?: OperatorRun[];
  count?: number;
}

interface ExecutionReviewsPayload {
  reviews?: ExecutionReviewProjection[];
  count?: number;
}

interface ExecutionResultsPayload {
  results?: ExecutionResultProjection[];
  count?: number;
}

const STATUS_FILTERS: RunStatus[] = ["running", "waiting_approval", "completed", "failed", "all"];

const ACTIONABLE_RESULT_STATUSES = new Set(["failed", "blocked", "cancelled"]);

export function RunsConsole() {
  const [status, setStatus] = useState<RunStatus>("running");

  const runsQuery = useQuery({
    queryKey: ["operator-runs", status],
    queryFn: async (): Promise<RunsFeedPayload> => {
      const query = status === "all" ? "" : `?status=${encodeURIComponent(status)}`;
      const data = await requestJson(`/api/operator/runs${query}`);
      return (data ?? {}) as RunsFeedPayload;
    },
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });

  const allRunsQuery = useQuery({
    queryKey: ["operator-runs-all"],
    queryFn: async (): Promise<RunsFeedPayload> => {
      try {
        const data = await requestJson("/api/operator/runs?limit=500");
        return (data ?? {}) as RunsFeedPayload;
      } catch {
        return {
          available: false,
          degraded: true,
          detail: "Failed to load complete operator run ledger.",
          runs: [],
          count: 0,
        };
      }
    },
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });

  const reviewsQuery = useQuery({
    queryKey: ["execution-reviews-pending"],
    queryFn: async (): Promise<ExecutionReviewsPayload> => {
      try {
        const data = await requestJson("/api/execution/reviews?status=pending");
        return (data ?? {}) as ExecutionReviewsPayload;
      } catch {
        return {
          reviews: [],
          count: 0,
        };
      }
    },
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });

  const resultsQuery = useQuery({
    queryKey: ["execution-results-all"],
    queryFn: async (): Promise<ExecutionResultsPayload> => {
      try {
        const data = await requestJson("/api/execution/results?limit=500");
        return (data ?? {}) as ExecutionResultsPayload;
      } catch {
        return {
          results: [],
          count: 0,
        };
      }
    },
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });

  if (runsQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Operator Work" title="Runs" description="The operator run ledger failed to load." attentionHref="/runs" />
        <ErrorPanel description={runsQuery.error instanceof Error ? runsQuery.error.message : "Failed to load operator runs."} />
      </div>
    );
  }

  const runs = runsQuery.data?.runs ?? [];
  const allRuns = allRunsQuery.data?.runs ?? [];
  const pendingReviews = reviewsQuery.data?.reviews ?? [];
  const actionableResults = (resultsQuery.data?.results ?? []).filter((result) =>
    ACTIONABLE_RESULT_STATUSES.has(result.status),
  );
  const runningCount = allRuns.filter((run) => run.status === "running").length;
  const pendingReviewRunIds = new Set(
    pendingReviews.map((review) => review.related_run_id || review.owner_id).filter(Boolean),
  );
  const actionableResultRunIds = new Set(
    actionableResults.map((result) => result.related_run_id || result.owner_id).filter(Boolean),
  );
  const runsFeedStatus = runsQuery.data;
  const allRunsFeedStatus = allRunsQuery.data;
  const runsFeedUnavailable =
    runsFeedStatus?.available === false ||
    runsFeedStatus?.degraded ||
    allRunsFeedStatus?.available === false ||
    allRunsFeedStatus?.degraded;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Operator Work"
        title="Runs"
        description="Canonical execution lineage projected from durable run, attempt, and step state."
        attentionHref="/runs"
        actions={
          <Button
            variant="outline"
            onClick={() =>
              void Promise.all([
                runsQuery.refetch(),
                allRunsQuery.refetch(),
                reviewsQuery.refetch(),
                resultsQuery.refetch(),
              ])
            }
            disabled={
              runsQuery.isFetching ||
              allRunsQuery.isFetching ||
              reviewsQuery.isFetching ||
              resultsQuery.isFetching
            }
          >
            <RefreshCcw
              className={`mr-2 h-4 w-4 ${
                runsQuery.isFetching || allRunsQuery.isFetching || reviewsQuery.isFetching || resultsQuery.isFetching
                  ? "animate-spin"
                  : ""
              }`}
            />
            Refresh
          </Button>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Visible runs" value={`${runs.length}`} detail="Current filtered run ledger." icon={<Waypoints className="h-5 w-5" />} />
          <StatCard
            label="Running"
            value={`${runningCount}`}
            detail={`${allRuns.length} total runs currently projected through the ledger.`}
            icon={<Gauge className="h-5 w-5" />}
          />
          <StatCard
            label="Shared reviews"
            value={`${pendingReviews.length}`}
            detail="Kernel-backed approval holds linked to execution runs."
            icon={<ShieldCheck className="h-5 w-5" />}
          />
          <StatCard
            label="Result alerts"
            value={`${actionableResults.length}`}
            detail="Kernel-backed failed, blocked, or cancelled result packets."
            icon={<AlertTriangle className="h-5 w-5" />}
          />
        </div>
      </PageHeader>

      {runsFeedUnavailable ? (
        <div className="surface-panel rounded-[24px] border border-[color:var(--signal-warning)]/40 px-5 py-4 sm:px-6">
          <p className="page-eyebrow text-[color:var(--signal-warning)]">Runs feed degraded</p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            The run ledger is still usable, but the dashboard is falling back to empty state data because the upstream runs feed is temporarily unavailable.
          </p>
        </div>
      ) : null}

      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Execution runs</CardTitle>
          <CardDescription>This is the canonical run view; the old task queue remains a compatibility surface.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {STATUS_FILTERS.map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setStatus(value)}
                className={`rounded-full border px-3 py-1 text-xs transition ${
                  status === value
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border/70 text-muted-foreground hover:bg-accent"
                }`}
              >
                {value}
              </button>
            ))}
          </div>

          {runs.length > 0 ? (
            <div className="space-y-3">
              {runs.map((run) => (
                <div key={run.id} className="surface-tile rounded-2xl border p-4">
                  {(() => {
                    const hasSharedReview = pendingReviewRunIds.has(run.id);
                    const hasResultAlert = actionableResultRunIds.has(run.id);
                    const needsSync =
                      !hasSharedReview &&
                      !hasResultAlert &&
                      (run.approval_pending ||
                        ["waiting_approval", "failed", "blocked", "cancelled"].includes(run.status));

                    return (
                      <>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{run.status}</Badge>
                    <Badge variant="secondary">{run.agent_id}</Badge>
                    {hasSharedReview ? <Badge variant="outline">shared review</Badge> : null}
                    {hasResultAlert ? <Badge variant="destructive">result alert</Badge> : null}
                    {needsSync ? <Badge variant="outline">needs sync</Badge> : null}
                    <span className="text-xs text-muted-foreground">{`${run.workload_class || "task"} · ${run.provider_lane || run.runtime_lane}`}</span>
                  </div>
                  <p className="mt-3 font-medium">{run.summary || run.id}</p>
                  <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
                    <span>{`Run ${run.id}`}</span>
                    {run.backlog_id ? <span>{`Backlog ${run.backlog_id}`}</span> : null}
                    {run.task_id ? <span>{`Task ${run.task_id}`}</span> : null}
                    <span>{`${run.step_count} steps`}</span>
                    {run.latest_attempt?.runtime_host ? <span>{`Host ${run.latest_attempt.runtime_host}`}</span> : null}
                  </div>
                  {hasSharedReview ? (
                    <p className="mt-3 text-xs text-amber-600">Shared review hold is active on this run.</p>
                  ) : null}
                  {hasResultAlert ? (
                    <p className="mt-3 text-xs text-[color:var(--signal-danger)]">Kernel result alert is active on this run.</p>
                  ) : null}
                  {needsSync ? (
                    <p className="mt-3 text-xs text-muted-foreground">
                      Run status and shared kernel evidence need sync.
                    </p>
                  ) : null}
                  <p className="mt-3 text-xs text-muted-foreground">{formatRelativeTime(new Date(run.updated_at * 1000).toISOString())}</p>
                      </>
                    );
                  })()}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title={runsFeedUnavailable ? "Runs feed unavailable" : "No runs in this view"}
              description={
                runsFeedUnavailable
                  ? "The dashboard cannot currently read the live operator run ledger, so this view is showing the fail-soft fallback."
                  : "Dispatch backlog work or change the current filter."
              }
              className="py-10"
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
