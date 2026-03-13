"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CalendarClock, PauseCircle, PlayCircle, RefreshCcw, Rocket } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getScheduledJobs } from "@/lib/api";
import { formatRelativeTime, formatTimestamp } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";

function formatLabel(value: string) {
  return value.replace(/_/g, " ");
}

function formatWindowLabel(value: string) {
  return value
    .split(/[-_]/g)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function toneForOutcome(value: string) {
  if (value === "failed") {
    return "destructive" as const;
  }
  if (value === "degraded" || value === "warning") {
    return "secondary" as const;
  }
  return "outline" as const;
}

export function ScheduledJobsCard({
  title = "Scheduled jobs",
  description = "Recurring autonomy loops, their current state, and their next expected execution.",
  limit = 6,
}: {
  title?: string;
  description?: string;
  limit?: number;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const jobsQuery = useQuery({
    queryKey: queryKeys.scheduledJobs(limit),
    queryFn: () => getScheduledJobs(limit),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  async function runJob(jobId: string, force = false) {
    setBusy(`${force ? "override" : "run"}:${jobId}`);
    setFeedback(null);
    try {
      const response = await fetch(`/api/workforce/scheduled/${encodeURIComponent(jobId)}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actor: "dashboard-operator", force }),
      });
      if (!response.ok) {
        throw new Error(`Run request failed (${response.status})`);
      }
      const payload = (await response.json()) as {
        status?: string;
        summary?: string;
        governor_decision?: { reason?: string };
      };
      if (payload.status === "deferred") {
        setFeedback(payload.summary ?? payload.governor_decision?.reason ?? `Governor deferred ${jobId}.`);
      } else {
        setFeedback(payload.summary ?? `Scheduled job ${jobId} triggered.`);
      }
      await jobsQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Failed to run scheduled job.");
    } finally {
      setBusy(null);
    }
  }

  async function toggleScope(scope: string, paused: boolean) {
    setBusy(`${paused ? "resume" : "pause"}:${scope}`);
    setFeedback(null);
    try {
      const response = await fetch(paused ? "/api/governor/resume" : "/api/governor/pause", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scope,
          actor: "dashboard-operator",
          reason: paused ? "" : `Paused from scheduled jobs (${scope})`,
        }),
      });
      if (!response.ok) {
        throw new Error(`Governor request failed (${response.status})`);
      }
      setFeedback(`${paused ? "Resumed" : "Paused"} ${scope.replace(/_/g, " ")} lane.`);
      await jobsQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Failed to update scheduled job lane.");
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
            : "Failed to load scheduled-job records."
        }
      />
    );
  }

  const jobs = jobsQuery.data?.jobs ?? [];
  const activeCount = jobs.filter((job) => job.current_state === "running").length;
  const failedCount = jobs.filter((job) => job.last_outcome === "failed").length;

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

        <div className="grid gap-3 sm:grid-cols-3">
          <Metric label="Visible jobs" value={`${jobs.length}`} />
          <Metric label="Running now" value={`${activeCount}`} />
          <Metric label="Failed last run" value={`${failedCount}`} />
        </div>

        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => void jobsQuery.refetch()} disabled={jobsQuery.isFetching}>
            <RefreshCcw className={`mr-2 h-4 w-4 ${jobsQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        {jobs.length > 0 ? (
          <div className="space-y-3">
            {jobs.map((job) => (
              <a
                key={job.id}
                href={job.deep_link}
                className="block rounded-2xl border border-border/70 bg-background/20 p-4 transition hover:bg-accent/40"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">{formatLabel(job.job_family)}</Badge>
                  <Badge variant="outline">{job.owner_agent}</Badge>
                  <Badge variant={toneForOutcome(job.last_outcome)}>{formatLabel(job.last_outcome)}</Badge>
                  {job.paused ? <Badge variant="destructive">paused</Badge> : null}
                  {job.current_state === "deferred" ? <Badge variant="secondary">deferred</Badge> : null}
                </div>
                <p className="mt-3 text-sm font-medium">{job.title}</p>
                <div className="mt-3 grid gap-2 text-xs text-muted-foreground md:grid-cols-2">
                  <span>cadence: {job.cadence}</span>
                  <span>trigger: {formatLabel(job.trigger_mode)}</span>
                  <span data-volatile="true">last run {formatRelativeTime(job.last_run)}</span>
                  <span data-volatile="true">next run {formatTimestamp(job.next_run)}</span>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  state {formatLabel(job.current_state)}
                </p>
                <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                  {job.priority_band ? (
                    <Badge variant="outline">priority {formatLabel(job.priority_band)}</Badge>
                  ) : null}
                  {job.capacity_posture ? (
                    <Badge variant="outline">
                      capacity {formatLabel(job.capacity_posture)}
                    </Badge>
                  ) : null}
                  {job.queue_posture ? (
                    <Badge variant="outline">queue {formatLabel(job.queue_posture)}</Badge>
                  ) : null}
                  {job.provider_posture ? (
                    <Badge variant="outline">
                      provider {formatLabel(job.provider_posture)}
                    </Badge>
                  ) : null}
                  {job.deferred_by ? (
                    <Badge variant="secondary">deferred by {formatLabel(job.deferred_by)}</Badge>
                  ) : null}
                </div>
                {job.active_window_ids?.length ? (
                  <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                    {job.active_window_ids.map((windowId) => (
                      <Badge key={windowId} variant="outline">
                        window {formatWindowLabel(windowId)}
                      </Badge>
                    ))}
                  </div>
                ) : null}
                {job.last_summary ? (
                  <p className="mt-2 text-xs text-muted-foreground">{job.last_summary}</p>
                ) : null}
                {job.governor_reason ? (
                  <p className="mt-2 text-xs text-muted-foreground">{job.governor_reason}</p>
                ) : null}
                {job.next_action ? (
                  <p className="mt-2 text-xs text-muted-foreground">
                    next action {formatLabel(job.next_action)}
                  </p>
                ) : null}
                {job.last_actor || job.last_force_override || job.last_task_id || job.last_plan_id ? (
                  <div className="mt-2 grid gap-1 text-[11px] text-muted-foreground md:grid-cols-2">
                    {job.last_actor ? <span>last actor {job.last_actor}</span> : null}
                    {job.last_force_override ? <span>force override yes</span> : null}
                    {job.last_task_id ? <span>task {job.last_task_id}</span> : null}
                    {job.last_plan_id ? <span>plan {job.last_plan_id}</span> : null}
                  </div>
                ) : null}
                {job.last_error ? (
                  <p className="mt-2 text-xs text-red-200">{job.last_error}</p>
                ) : null}
                <div className="mt-3 flex flex-wrap gap-2">
                  {job.can_run_now ? (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(event) => {
                        event.preventDefault();
                        void runJob(job.id);
                      }}
                      disabled={busy !== null}
                    >
                      <Rocket className="mr-2 h-4 w-4" />
                      Run now
                    </Button>
                  ) : null}
                  {job.can_override_now ? (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={(event) => {
                        event.preventDefault();
                        void runJob(job.id, true);
                      }}
                      disabled={busy !== null}
                    >
                      <Rocket className="mr-2 h-4 w-4" />
                      Override
                    </Button>
                  ) : null}
                  {job.control_scope ? (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(event) => {
                        event.preventDefault();
                        void toggleScope(job.control_scope!, Boolean(job.paused));
                      }}
                      disabled={busy !== null}
                    >
                      {job.paused ? (
                        <PlayCircle className="mr-2 h-4 w-4" />
                      ) : (
                        <PauseCircle className="mr-2 h-4 w-4" />
                      )}
                      {job.paused ? "Resume lane" : "Pause lane"}
                    </Button>
                  ) : null}
                </div>
              </a>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No scheduled jobs reported"
            description="Recurring autonomy lanes will appear here once the scheduler emits normalized records."
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
