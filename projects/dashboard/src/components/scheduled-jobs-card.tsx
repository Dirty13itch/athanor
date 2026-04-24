"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CalendarClock, RefreshCcw, Rocket, ShieldAlert } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getScheduledJobs } from "@/lib/api";
import type { ScheduledJobRecord, ScheduledJobsResponse } from "@/lib/contracts";
import { formatRelativeTime } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import {
  classifyScheduledJobAdmission,
  classifyScheduledJobExecutionMode,
  classifyScheduledJobExecutionPlane,
  isScheduledJobBlocked,
  isScheduledJobQueueBacked,
  isScheduledJobProposalOnly,
  scheduledJobNeedsSync,
} from "@/lib/scheduled-job-posture";

function formatLabel(value: string) {
  return value.replace(/_/g, " ");
}

function toneForStatus(value: string) {
  if (value === "blocked") {
    return "destructive" as const;
  }
  if (value === "running" || value === "active" || value === "materialized_to_backlog") {
    return "secondary" as const;
  }
  return "outline" as const;
}

function summarizeRunResult(payload: Record<string, unknown>, jobId: string) {
  const status = String(payload.status ?? "").trim();
  const backlogId = String(payload.backlog_id ?? "").trim();
  const materializationStatus = String(payload.materialization_status ?? "").trim();
  const admissionReason = String(payload.admission_reason ?? "").trim();
  const summary = String(payload.summary ?? "").trim();

  if (status === "materialized_to_backlog") {
    const backlogDetail = backlogId ? `backlog ${backlogId}` : "the canonical backlog";
    return `Scheduled job ${jobId} materialized to ${backlogDetail}${materializationStatus ? ` (${materializationStatus})` : ""}.`;
  }
  if (status.startsWith("blocked_by_")) {
    return summary || admissionReason || `Scheduled job ${jobId} is blocked (${status}).`;
  }
  if (status === "deferred") {
    return summary || `Scheduled job ${jobId} was deferred.`;
  }
  if (status === "queued" || status === "pending_approval") {
    return summary || `Scheduled job ${jobId} executed directly as ${status}.`;
  }
  return summary || `Scheduled job ${jobId} triggered.`;
}

export function ScheduledJobsCard({
  title = "Autonomy schedule",
  description = "Recurring queue-backed product work and direct system loops, with explicit backlog materialization posture.",
}: {
  title?: string;
  description?: string;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const limit = 8;

  const jobsQuery = useQuery({
    queryKey: queryKeys.scheduledJobs(limit),
    queryFn: async () => getScheduledJobs(limit),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  async function runJob(jobId: string, force = false) {
    setBusy(`${jobId}:${force ? "force" : "run"}`);
    setFeedback(null);
    try {
      const response = await fetch(`/api/workforce/scheduled/${encodeURIComponent(jobId)}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          force,
        }),
      });
      if (!response.ok) {
        throw new Error(`Scheduled job run failed (${response.status})`);
      }
      const payload = ((await response.json()) ?? {}) as Record<string, unknown>;
      setFeedback(summarizeRunResult(payload, jobId));
      await jobsQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Failed to run scheduled job.");
    } finally {
      setBusy(null);
    }
  }

  if (jobsQuery.isError && !jobsQuery.data) {
    return (
      <ErrorPanel
        title={title}
        description={
          jobsQuery.error instanceof Error
            ? jobsQuery.error.message
            : "Failed to load scheduled job records."
        }
      />
    );
  }

  const payload: ScheduledJobsResponse = jobsQuery.data ?? { jobs: [] };
  const jobs = payload.jobs ?? [];
  const queueBackedCount = jobs.filter((job) => isScheduledJobQueueBacked(job)).length;
  const directCount = jobs.filter((job) => classifyScheduledJobExecutionPlane(job) === "direct_control").length;
  const proposalOnlyCount = jobs.filter((job) => isScheduledJobProposalOnly(job)).length;
  const blockedCount = jobs.filter((job) => isScheduledJobBlocked(job)).length;
  const needsSyncCount = jobs.filter((job) => scheduledJobNeedsSync(job)).length;

  return (
    <Card className="border-border/70 bg-card/70">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <CalendarClock className="h-5 w-5 text-primary" />
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {feedback ? (
          <div className="rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm">
            {feedback}
          </div>
        ) : null}

        <div className="grid gap-3 sm:grid-cols-5">
          <Metric label="Jobs" value={`${jobs.length}`} />
          <Metric label="Queue-backed" value={`${queueBackedCount}`} />
          <Metric label="Proposal-only" value={`${proposalOnlyCount}`} />
          <Metric label="Direct loops" value={`${directCount}`} />
          <Metric label="Blocked" value={`${blockedCount}`} />
          <Metric label="Needs sync" value={`${needsSyncCount}`} />
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={() => void jobsQuery.refetch()}
            disabled={jobsQuery.isFetching}
          >
            <RefreshCcw className={`mr-2 h-4 w-4 ${jobsQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Badge variant="outline">queue-backed {queueBackedCount}</Badge>
          <Badge variant="outline">proposal-only {proposalOnlyCount}</Badge>
          <Badge variant="outline">direct {directCount}</Badge>
          {blockedCount > 0 ? <Badge variant="outline">blocked {blockedCount}</Badge> : null}
          {needsSyncCount > 0 ? <Badge variant="destructive">needs sync {needsSyncCount}</Badge> : null}
        </div>

        {jobs.length > 0 ? (
          <div className="space-y-3">
            {jobs.map((job: ScheduledJobRecord) => {
              const executionMode = classifyScheduledJobExecutionMode(job);
              const queueBacked = executionMode === "materialized_to_backlog";
              const executionPlane = classifyScheduledJobExecutionPlane(job);
              const admission = classifyScheduledJobAdmission(job);
              const blocked = isScheduledJobBlocked(job);
              const needsSync = scheduledJobNeedsSync(job);
              const runDisabled = !(job.can_run_now ?? true) && !(job.can_override_now ?? false);
              return (
                <div
                  key={job.id}
                  className="block rounded-2xl border border-border/70 bg-background/20 p-4"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={toneForStatus(job.current_state)}>{formatLabel(job.current_state)}</Badge>
                    <Badge variant={queueBacked ? "secondary" : executionPlane === "proposal_only" ? "secondary" : "outline"}>
                      {queueBacked ? "queue-backed" : executionPlane === "proposal_only" ? "proposal-only" : "direct"}
                    </Badge>
                    <Badge variant="outline">{formatLabel(job.job_family)}</Badge>
                    {job.last_materialization_status ? (
                      <Badge variant="outline">{formatLabel(job.last_materialization_status)}</Badge>
                    ) : null}
                    {job.last_backlog_id ? <Badge variant="outline">{job.last_backlog_id}</Badge> : null}
                    {job.last_execution_plane ? (
                      <Badge variant="outline">{formatLabel(job.last_execution_plane)}</Badge>
                    ) : null}
                    {needsSync ? (
                      <Badge variant="destructive">
                        <ShieldAlert className="mr-1 h-3 w-3" />
                        needs sync
                      </Badge>
                    ) : null}
                    {blocked ? <Badge variant="destructive">{formatLabel(admission)}</Badge> : null}
                  </div>
                  <p className="mt-3 text-sm font-medium">{job.title}</p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {job.last_summary || job.last_admission_reason || job.governor_reason || "No scheduler summary recorded yet."}
                  </p>
                  <div className="mt-3 grid gap-2 text-xs text-muted-foreground md:grid-cols-3">
                    <span>cadence: {job.cadence}</span>
                    <span>owner: {job.owner_agent}</span>
                    <span data-volatile="true">
                      next {job.next_run ? formatRelativeTime(job.next_run) : "unscheduled"}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                    {job.last_run ? <Badge variant="outline">last run {formatRelativeTime(job.last_run)}</Badge> : null}
                    {job.priority_band ? <Badge variant="outline">{job.priority_band}</Badge> : null}
                    {job.last_admission_classification ? (
                      <Badge variant="outline">{formatLabel(job.last_admission_classification)}</Badge>
                    ) : null}
                    {job.deferred_by ? <Badge variant="outline">deferred by {formatLabel(job.deferred_by)}</Badge> : null}
                    {job.last_error ? <Badge variant="destructive">{job.last_error}</Badge> : null}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => void runJob(job.id, false)}
                      disabled={busy !== null || runDisabled}
                    >
                      <Rocket className="mr-2 h-4 w-4" />
                      Run now
                    </Button>
                    {!(job.can_run_now ?? true) && (job.can_override_now ?? false) ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => void runJob(job.id, true)}
                        disabled={busy !== null}
                      >
                        Force run
                      </Button>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyState
            title="No scheduled jobs yet"
            description="Scheduled jobs will appear here once the scheduler publishes normalized posture records."
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
