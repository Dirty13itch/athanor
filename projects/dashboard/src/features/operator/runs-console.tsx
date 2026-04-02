"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Gauge, RefreshCcw, ShieldCheck, TimerReset, Waypoints } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { formatRelativeTime } from "@/lib/format";
import { requestJson } from "@/features/workforce/helpers";

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

interface OperatorSummary {
  runs?: {
    total?: number;
    by_status?: Record<string, number>;
  };
}

const STATUS_FILTERS: RunStatus[] = ["running", "waiting_approval", "completed", "failed", "all"];

export function RunsConsole() {
  const [status, setStatus] = useState<RunStatus>("running");

  const runsQuery = useQuery({
    queryKey: ["operator-runs", status],
    queryFn: async (): Promise<OperatorRun[]> => {
      const query = status === "all" ? "" : `?status=${encodeURIComponent(status)}`;
      const data = await requestJson(`/api/operator/runs${query}`);
      return (data?.runs ?? data ?? []) as OperatorRun[];
    },
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });

  const summaryQuery = useQuery({
    queryKey: ["operator-work-summary"],
    queryFn: async (): Promise<OperatorSummary> => {
      const data = await requestJson("/api/operator/summary");
      return (data ?? {}) as OperatorSummary;
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

  const runs = runsQuery.data ?? [];
  const byStatus = summaryQuery.data?.runs?.by_status ?? {};

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Operator Work"
        title="Runs"
        description="Canonical execution lineage projected from durable run, attempt, and step state."
        attentionHref="/runs"
        actions={
          <Button variant="outline" onClick={() => void Promise.all([runsQuery.refetch(), summaryQuery.refetch()])} disabled={runsQuery.isFetching || summaryQuery.isFetching}>
            <RefreshCcw className={`mr-2 h-4 w-4 ${runsQuery.isFetching || summaryQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Visible runs" value={`${runs.length}`} detail="Current filtered run ledger." icon={<Waypoints className="h-5 w-5" />} />
          <StatCard label="Running" value={`${byStatus.running ?? 0}`} detail={`${byStatus.waiting_approval ?? 0} waiting on approval.`} icon={<Gauge className="h-5 w-5" />} />
          <StatCard label="Completed" value={`${byStatus.completed ?? 0}`} detail={`${byStatus.failed ?? 0} failed executions remain in view.`} icon={<TimerReset className="h-5 w-5" />} />
          <StatCard label="Approval holds" value={`${byStatus.waiting_approval ?? 0}`} detail="Pending approval requests linked to execution runs." icon={<ShieldCheck className="h-5 w-5" />} />
        </div>
      </PageHeader>

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
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{run.status}</Badge>
                    <Badge variant="secondary">{run.agent_id}</Badge>
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
                  {run.approval_pending ? <p className="mt-3 text-xs text-amber-600">Approval hold is active on this run.</p> : null}
                  <p className="mt-3 text-xs text-muted-foreground">{formatRelativeTime(new Date(run.updated_at * 1000).toISOString())}</p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No runs in this view" description="Dispatch backlog work or change the current filter." className="py-10" />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
