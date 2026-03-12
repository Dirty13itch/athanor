"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { RefreshCcw, Sparkles } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  asArray,
  asObject,
  fetchJson,
  formatKey,
  getNumber,
  getOptionalString,
  getString,
  type JsonObject,
} from "@/components/runtime-panel-utils";
import { formatRelativeTime } from "@/lib/format";

export function ResearchJobsCard() {
  const [topic, setTopic] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const jobsQuery = useQuery({
    queryKey: ["operator-panel", "research-jobs"],
    queryFn: async () => ({
      jobs: await fetchJson<unknown>("/api/research/jobs"),
      scheduled: await fetchJson<JsonObject>("/api/workforce/scheduled"),
      scheduling: await fetchJson<JsonObject>("/api/scheduling/status"),
    }),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  async function createJob() {
    if (!topic.trim()) {
      return;
    }
    setBusy("create");
    setFeedback(null);
    try {
      await fetchJson<JsonObject>("/api/research/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: topic.trim(),
          description: `Operator-seeded research job: ${topic.trim()}`,
          sources: ["web_search", "knowledge_base"],
          max_duration_minutes: 45,
        }),
      });
      setTopic("");
      setFeedback("Research job created.");
      await jobsQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Failed to create research job.");
    } finally {
      setBusy(null);
    }
  }

  async function executeJob(jobId: string) {
    setBusy(jobId);
    setFeedback(null);
    try {
      await fetchJson<JsonObject>(`/api/research/jobs/${jobId}/execute`, { method: "POST" });
      setFeedback(`Research job ${jobId} executed.`);
      await jobsQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Failed to execute research job.");
    } finally {
      setBusy(null);
    }
  }

  if (jobsQuery.isError && !jobsQuery.data) {
    return (
      <ErrorPanel
        title="Research jobs"
        description={
          jobsQuery.error instanceof Error ? jobsQuery.error.message : "Failed to load research jobs."
        }
      />
    );
  }

  const jobsValue = jobsQuery.data?.jobs;
  const jobs = Array.isArray(jobsValue)
    ? (jobsValue as JsonObject[])
    : asArray<JsonObject>(asObject(jobsValue)?.jobs);
  const scheduled = asArray<JsonObject>(asObject(jobsQuery.data?.scheduled)?.jobs);
  const scheduling = asObject(jobsQuery.data?.scheduling);
  const load = asObject(scheduling?.load);
  const thresholds = asObject(scheduling?.thresholds);
  const agentClasses = asObject(scheduling?.agent_classes);

  return (
    <Card className="border-border/70 bg-card/70">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Sparkles className="h-5 w-5 text-primary" />
          Research jobs and scheduling
        </CardTitle>
        <CardDescription>
          Queue autonomous research runs against current inference load and class budgets.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {feedback ? (
          <div className="rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm">
            {feedback}
          </div>
        ) : null}

        <div className="grid gap-3 md:grid-cols-[1fr_auto]">
          <Input
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            placeholder="Seed a new research topic"
          />
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => void jobsQuery.refetch()} disabled={jobsQuery.isFetching}>
              <RefreshCcw className={`mr-2 h-4 w-4 ${jobsQuery.isFetching ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button onClick={() => void createJob()} disabled={busy === "create" || !topic.trim()}>
              Create job
            </Button>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <Metric label="Jobs" value={`${jobs.length}`} />
          <Metric label="Scheduled lanes" value={`${scheduled.length}`} />
          <Metric
            label="Inference pressure"
            value={load ? `${Math.round(getNumber(load.current_ratio, 0) * 100)}%` : "--"}
          />
        </div>

        <div className="grid gap-3 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Jobs</p>
            {jobs.length > 0 ? (
              jobs.slice(0, 5).map((job) => {
                const jobId = getString(job.job_id ?? job.id);
                return (
                  <div
                    key={jobId}
                    className="rounded-xl border border-border/60 bg-background/30 p-3 text-sm"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-medium">{getString(job.topic, jobId)}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {getString(job.description, "No description provided.")}
                        </p>
                      </div>
                      <Badge variant="outline">{getString(job.status, "queued")}</Badge>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Badge variant="secondary">
                        {getNumber(job.schedule_hours, 0) > 0
                          ? `every ${getNumber(job.schedule_hours, 0)}h`
                          : "manual"}
                      </Badge>
                      {getOptionalString(job.updated_at) ? (
                        <Badge variant="outline" data-volatile="true">
                          {formatRelativeTime(getString(job.updated_at))}
                        </Badge>
                      ) : null}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        onClick={() => void executeJob(jobId)}
                        disabled={busy === jobId}
                      >
                        Run now
                      </Button>
                    </div>
                  </div>
                );
              })
            ) : (
              <EmptyState
                title="No research jobs queued"
                description="Seed a topic above to create the first dashboard-visible research lane."
                className="py-8"
              />
            )}
          </div>

          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
              Scheduling posture
            </p>
            <div className="rounded-xl border border-border/60 bg-background/30 p-3 text-sm">
              <MetricRow
                label="Current ratio"
                value={load ? `${Math.round(getNumber(load.current_ratio, 0) * 100)}%` : "--"}
              />
              <MetricRow
                label="Warning threshold"
                value={thresholds ? `${Math.round(getNumber(thresholds.warning, 0) * 100)}%` : "--"}
              />
              <MetricRow
                label="Critical threshold"
                value={thresholds ? `${Math.round(getNumber(thresholds.critical, 0) * 100)}%` : "--"}
              />
              <MetricRow
                label="Agent classes"
                value={`${Object.keys(agentClasses ?? {}).length}`}
              />
              <div className="mt-3 space-y-2">
                {scheduled.slice(0, 4).map((job) => (
                  <div key={getString(job.id)} className="rounded-lg border border-border/50 px-2 py-2">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium">{getString(job.title)}</p>
                      <Badge variant="outline">{getString(job.current_state, "scheduled")}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {getString(job.cadence, "manual")}
                      {getOptionalString(job.next_run)
                        ? ` · next ${formatRelativeTime(getString(job.next_run))}`
                        : ""}
                    </p>
                  </div>
                ))}
                {scheduled.length === 0
                  ? Object.entries(agentClasses ?? {}).slice(0, 3).map(([name, value]) => {
                      const meta = asObject(value);
                      return (
                        <div key={name} className="rounded-lg border border-border/50 px-2 py-2">
                          <p className="font-medium">{formatKey(name)}</p>
                          <p className="text-xs text-muted-foreground">
                            max concurrency {getNumber(meta?.max_concurrency, 0)}
                          </p>
                        </div>
                      );
                    })
                  : null}
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/40 px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
