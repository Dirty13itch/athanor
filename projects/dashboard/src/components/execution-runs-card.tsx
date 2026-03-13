"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, RefreshCcw } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getExecutionRuns } from "@/lib/api";
import { compactText, formatRelativeTime, formatTimestamp } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";

function formatLabel(value: string) {
  return value.replace(/_/g, " ");
}

function toneForStatus(status: string) {
  if (status === "failed") {
    return "destructive" as const;
  }
  if (["running", "pending", "issued"].includes(status)) {
    return "secondary" as const;
  }
  return "outline" as const;
}

export function ExecutionRunsCard({
  title = "Execution runs",
  description = "Parent and child execution records across supervisor, worker, and judge lanes.",
  limit = 6,
  compact = false,
}: {
  title?: string;
  description?: string;
  limit?: number;
  compact?: boolean;
}) {
  const runsQuery = useQuery({
    queryKey: queryKeys.executionRuns(limit),
    queryFn: () => getExecutionRuns(limit),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  if (runsQuery.isError && !runsQuery.data) {
    return (
      <ErrorPanel
        title={title}
        description={
          runsQuery.error instanceof Error
            ? runsQuery.error.message
            : "Failed to load execution-run records."
        }
      />
    );
  }

  const runs = runsQuery.data?.runs ?? [];
  const failedCount = runs.filter((run) => run.status === "failed").length;
  const activeCount = runs.filter((run) => ["queued", "running", "pending", "issued"].includes(run.status)).length;

  return (
    <Card className="border-border/70 bg-card/70">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Activity className="h-5 w-5 text-primary" />
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <Metric label="Visible runs" value={`${runs.length}`} />
          <Metric label="Active" value={`${activeCount}`} />
          <Metric label="Failed" value={`${failedCount}`} />
        </div>

        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => void runsQuery.refetch()} disabled={runsQuery.isFetching}>
            <RefreshCcw className={`mr-2 h-4 w-4 ${runsQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        {runs.length > 0 ? (
          <div className="space-y-3">
            {runs.map((run) => (
              <div key={run.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={toneForStatus(run.status)}>{formatLabel(run.status)}</Badge>
                  <Badge variant="secondary">{formatLabel(run.source_lane)}</Badge>
                  <Badge variant="outline">{run.agent}</Badge>
                  <Badge variant="outline">{run.provider}</Badge>
                  {run.policy_class ? (
                    <Badge variant="outline">{formatLabel(run.policy_class)}</Badge>
                  ) : null}
                  {run.approval_mode ? (
                    <Badge variant="outline">{formatLabel(run.approval_mode)}</Badge>
                  ) : null}
                </div>
                <p className="mt-3 text-sm">{compactText(run.summary, compact ? 120 : 200)}</p>
                <div className="mt-3 grid gap-2 text-xs text-muted-foreground md:grid-cols-2">
                  <span>run type: {formatLabel(run.run_type)}</span>
                  <span data-volatile="true">created {formatRelativeTime(run.created_at)}</span>
                  <span data-volatile="true">completed {formatTimestamp(run.completed_at)}</span>
                  <span>{run.lease_id ? `lease ${run.lease_id}` : "no lease"}</span>
                </div>
                {run.supervisor_lane || run.worker_lane || run.command_decision_id ? (
                  <div className="mt-3 grid gap-2 text-xs text-muted-foreground md:grid-cols-4">
                    <span>{run.supervisor_lane ? `supervisor ${formatLabel(run.supervisor_lane)}` : "supervisor --"}</span>
                    <span>{run.worker_lane ? `worker ${formatLabel(run.worker_lane)}` : "worker --"}</span>
                    <span>{run.judge_lane ? `judge ${formatLabel(run.judge_lane)}` : "judge --"}</span>
                    <span>{run.command_decision_id ? `decision ${run.command_decision_id}` : "decision --"}</span>
                  </div>
                ) : null}
                {run.prompt_version || run.policy_version || run.corpus_version ? (
                  <div className="mt-3 grid gap-2 text-xs text-muted-foreground md:grid-cols-3">
                    <span>{run.prompt_version ? `prompt ${run.prompt_version}` : "prompt --"}</span>
                    <span>{run.policy_version ? `policy ${run.policy_version}` : "policy --"}</span>
                    <span>{run.corpus_version ? `corpus ${run.corpus_version}` : "corpus --"}</span>
                  </div>
                ) : null}
                {run.artifact_provenance || run.lineage ? (
                  <div className="mt-3 rounded-xl border border-border/60 bg-background/20 px-3 py-2 text-xs text-muted-foreground">
                    <div className="grid gap-2 md:grid-cols-2">
                      <span>
                        provenance {run.artifact_provenance?.status ?? "partial"} | refs{" "}
                        {run.artifact_provenance?.artifact_ref_count ?? run.artifact_refs.length}
                      </span>
                      <span>
                        lineage {run.lineage?.lane ? formatLabel(run.lineage.lane) : formatLabel(run.source_lane)}
                      </span>
                      <span>
                        decided by {run.artifact_provenance?.deciding_layer ?? "governor"}
                      </span>
                      <span>
                        parent {run.lineage?.parent_run_id ?? "--"}
                      </span>
                    </div>
                  </div>
                ) : null}
                {run.failure_reason ? (
                  <p className="mt-3 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-100">
                    {run.failure_reason}
                  </p>
                ) : null}
                {run.artifact_refs.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {run.artifact_refs.slice(0, compact ? 1 : 3).map((artifact) => (
                      <a
                        key={`${run.id}-${artifact.href}`}
                        href={artifact.href}
                        className="rounded-full border border-border/60 px-3 py-1 text-xs text-muted-foreground transition hover:bg-accent hover:text-foreground"
                      >
                        {artifact.label}
                      </a>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No execution runs yet"
            description="Execution lineage will appear here once the backbone writes run records."
            className="py-8"
          />
        )}
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/30 px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}
