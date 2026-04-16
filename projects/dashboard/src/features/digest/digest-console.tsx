"use client";

import { useCallback, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  FolderX,
  Inbox,
  RefreshCcw,
  Sparkles,
  Stamp,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { requestJson, postWithoutBody, postJson } from "@/features/workforce/helpers";
import { formatRelativeTime } from "@/lib/format";
import { isOperatorSessionLocked, useOperatorSessionStatus } from "@/lib/operator-session";

interface DigestTask {
  id: string;
  prompt: string;
  agent_id?: string;
  agent_name?: string;
  priority?: string;
  status: string;
  created_at?: string;
  completed_at?: string;
  duration_ms?: number;
  quality_score?: number;
}

interface OperatorRunRecord {
  id: string;
  summary?: string;
  agent_id?: string;
  agent?: string;
  status?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  metadata?: Record<string, unknown>;
}

interface PendingApproval {
  id: string;
  related_task_id?: string;
  requested_action: string;
  privilege_class: string;
  reason: string;
  status: string;
  requested_at?: number;
  task_prompt?: string;
  task_agent_id?: string;
  task_priority?: string;
}

interface StalledProject {
  id: string;
  name?: string;
  reason?: string;
  stalled_since?: string;
}

interface OperatorProjectSummary {
  stalled_total?: number;
  stalled_preview?: StalledProject[];
}

interface OperatorSummaryPayload {
  projects?: OperatorProjectSummary;
}

function priorityVariant(priority: string | undefined) {
  if (priority === "critical") return "destructive" as const;
  if (priority === "high") return "default" as const;
  return "secondary" as const;
}

const PENDING_QUERY_KEY = ["digest-pending-approvals"] as const;
const COMPLETED_QUERY_KEY = ["digest-overnight-results"] as const;
const SUMMARY_QUERY_KEY = ["digest-operator-summary"] as const;

export function DigestConsole() {
  const queryClient = useQueryClient();
  const operatorSession = useOperatorSessionStatus();
  const approvalTimestamps = useRef<number[]>([]);
  const [rubberStampWarning, setRubberStampWarning] = useState(false);

  const pendingQuery = useQuery({
    queryKey: PENDING_QUERY_KEY,
    queryFn: async (): Promise<PendingApproval[]> => {
      const data = await requestJson("/api/operator/approvals?status=pending");
      return (data?.approvals ?? data ?? []) as PendingApproval[];
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const completedQuery = useQuery({
    queryKey: COMPLETED_QUERY_KEY,
    queryFn: async (): Promise<DigestTask[]> => {
      const data = await requestJson("/api/operator/runs?status=completed&limit=20");
      const tasks = ((data?.runs ?? data ?? []) as OperatorRunRecord[]).map((run) => ({
        id: run.id,
        prompt: run.summary ?? String(run.metadata?.prompt ?? "(no summary)"),
        agent_id: run.agent_id ?? run.agent,
        agent_name: run.agent_id ?? run.agent,
        priority:
          typeof run.metadata?.priority === "string"
            ? run.metadata.priority
            : typeof run.metadata?.priority_band === "string"
              ? run.metadata.priority_band
              : undefined,
        status: run.status ?? "completed",
        created_at: run.created_at,
        completed_at: run.completed_at,
        duration_ms:
          typeof run.metadata?.duration_ms === "number"
            ? run.metadata.duration_ms
            : undefined,
        quality_score:
          typeof run.metadata?.quality_score === "number"
            ? run.metadata.quality_score
            : undefined,
      }));
      const cutoff = Date.now() - 12 * 60 * 60 * 1000;
      return tasks.filter((t) => {
        const ts = t.completed_at ?? t.created_at;
        return ts ? new Date(ts).getTime() >= cutoff : true;
      });
    },
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  const summaryQuery = useQuery({
    queryKey: SUMMARY_QUERY_KEY,
    queryFn: async (): Promise<OperatorSummaryPayload> => {
      return (await requestJson("/api/operator/summary")) as OperatorSummaryPayload;
    },
    enabled: !operatorSession.isPending && !isOperatorSessionLocked(operatorSession),
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  const pendingApprovals = pendingQuery.data ?? [];
  const completedTasks = completedQuery.data ?? [];
  const projectSummary = ((summaryQuery.data as OperatorSummaryPayload | undefined)?.projects ?? {}) as OperatorProjectSummary;
  const stalledProjects = Array.isArray(projectSummary.stalled_preview) ? projectSummary.stalled_preview : [];
  const stalledProjectCount = Number(projectSummary.stalled_total ?? stalledProjects.length);

  const avgQuality = completedTasks.length > 0
    ? completedTasks.reduce((sum, t) => sum + (t.quality_score ?? 0), 0) / completedTasks.filter((t) => t.quality_score != null).length
    : 0;

  const checkRubberStamp = useCallback(() => {
    const now = Date.now();
    approvalTimestamps.current.push(now);
    approvalTimestamps.current = approvalTimestamps.current.filter((ts) => now - ts < 30_000);
    if (approvalTimestamps.current.length > 5) {
      setRubberStampWarning(true);
      setTimeout(() => setRubberStampWarning(false), 10_000);
    }
  }, []);

  const approveMutation = useMutation({
    mutationFn: async (approvalId: string) => {
      await postWithoutBody(`/api/operator/approvals/${encodeURIComponent(approvalId)}/approve`);
    },
    onSuccess: () => {
      checkRubberStamp();
      void queryClient.invalidateQueries({ queryKey: PENDING_QUERY_KEY });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async ({ approvalId, reason }: { approvalId: string; reason: string }) => {
      await postJson(`/api/operator/approvals/${encodeURIComponent(approvalId)}/reject`, { reason });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PENDING_QUERY_KEY });
    },
  });

  const batchApproveMutation = useMutation({
    mutationFn: async (approvalIds: string[]) => {
      for (const id of approvalIds) {
        await postWithoutBody(`/api/operator/approvals/${encodeURIComponent(id)}/approve`);
      }
    },
    onSuccess: () => {
      const now = Date.now();
      for (const _id of pendingApprovals) {
        approvalTimestamps.current.push(now);
      }
      approvalTimestamps.current = approvalTimestamps.current.filter((ts) => now - ts < 30_000);
      if (approvalTimestamps.current.length > 5) {
        setRubberStampWarning(true);
        setTimeout(() => setRubberStampWarning(false), 10_000);
      }
      void queryClient.invalidateQueries({ queryKey: PENDING_QUERY_KEY });
    },
  });

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Workforce"
        title="Morning Digest"
        description="Pending approvals, overnight results, and stalled projects at a glance."
        attentionHref="/digest"
        actions={
          <Button
            variant="outline"
            onClick={() => {
              void pendingQuery.refetch();
              void completedQuery.refetch();
              void summaryQuery.refetch();
            }}
            disabled={pendingQuery.isFetching || completedQuery.isFetching || summaryQuery.isFetching}
          >
            <RefreshCcw
              className={`mr-2 h-4 w-4 ${
                pendingQuery.isFetching || completedQuery.isFetching || summaryQuery.isFetching ? "animate-spin" : ""
              }`}
            />
            Refresh
          </Button>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Pending Approvals"
            value={`${pendingApprovals.length}`}
            detail={pendingApprovals.length === 0 ? "All clear" : "Awaiting review"}
            icon={<Inbox className="h-5 w-5" />}
            tone={pendingApprovals.length > 0 ? "warning" : "success"}
          />
          <StatCard
            label="Overnight Tasks"
            value={`${completedTasks.length}`}
            detail="Completed in last 12h"
            icon={<Clock className="h-5 w-5" />}
          />
          <StatCard
            label="Avg Quality"
            value={avgQuality > 0 ? `${(avgQuality * 100).toFixed(0)}%` : "--"}
            detail="Across overnight tasks"
            icon={<Sparkles className="h-5 w-5" />}
            tone={avgQuality >= 0.8 ? "success" : avgQuality >= 0.5 ? "warning" : "default"}
          />
          <StatCard
            label="Stalled Projects"
            value={`${stalledProjectCount}`}
            detail={stalledProjectCount === 0 ? "None detected" : "Need attention"}
            icon={<FolderX className="h-5 w-5" />}
            tone={stalledProjectCount > 0 ? "danger" : "success"}
          />
        </div>
      </PageHeader>

      {/* Rubber-stamp warning */}
      {rubberStampWarning ? (
        <div className="flex items-center gap-3 rounded-2xl border border-yellow-500/30 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-200">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          Rubber-stamp detected — consider reviewing more carefully.
        </div>
      ) : null}

      {/* Pending Approvals */}
      <Card className="surface-panel">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg">Pending Approvals</CardTitle>
              <CardDescription>
                Canonical approval requests awaiting operator review before execution.
              </CardDescription>
            </div>
            {pendingApprovals.length > 1 ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  void batchApproveMutation.mutateAsync(pendingApprovals.map((approval) => approval.id))
                }
                disabled={batchApproveMutation.isPending}
              >
                <Stamp className="mr-2 h-4 w-4" />
                Approve all ({pendingApprovals.length})
              </Button>
            ) : null}
          </div>
        </CardHeader>
        <CardContent>
          {pendingApprovals.length > 0 ? (
            <div className="space-y-3">
              {pendingApprovals.map((approval) => (
                <div
                  key={approval.id}
                  className="surface-instrument rounded-2xl border p-4"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0 flex-1 space-y-2">
                      <p className="text-sm font-medium">{approval.task_prompt || approval.reason}</p>
                      <div className="flex flex-wrap items-center gap-2">
                        {approval.task_agent_id ? (
                          <Badge variant="outline">{approval.task_agent_id}</Badge>
                        ) : null}
                        {approval.task_priority ? (
                          <Badge variant={priorityVariant(approval.task_priority)}>
                            {approval.task_priority}
                          </Badge>
                        ) : null}
                        {approval.requested_at ? (
                          <span className="text-xs text-muted-foreground" data-volatile="true">
                            {formatRelativeTime(new Date(approval.requested_at * 1000).toISOString())}
                          </span>
                        ) : null}
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Button
                        size="sm"
                        onClick={() => void approveMutation.mutateAsync(approval.id)}
                        disabled={approveMutation.isPending}
                      >
                        <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
                        Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                          void rejectMutation.mutateAsync({
                            approvalId: approval.id,
                            reason: "Rejected from digest",
                          })
                        }
                        disabled={rejectMutation.isPending}
                      >
                        <XCircle className="mr-1.5 h-3.5 w-3.5" />
                        Reject
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No pending approvals"
              description="All tasks have been reviewed. Check back later."
              className="py-8"
            />
          )}
        </CardContent>
      </Card>

      {/* Overnight Results */}
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Overnight Results</CardTitle>
          <CardDescription>
            Tasks completed in the last 12 hours.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {completedTasks.length > 0 ? (
            <div className="space-y-2">
              {completedTasks.map((task) => (
                <div
                  key={task.id}
                  className="surface-instrument flex items-center justify-between rounded-xl border px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-[color:var(--signal-success)]" />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">
                        {task.prompt.length > 80 ? `${task.prompt.slice(0, 80)}...` : task.prompt}
                      </p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        {task.agent_name || task.agent_id ? (
                          <span>{task.agent_name ?? task.agent_id}</span>
                        ) : null}
                        {task.duration_ms ? (
                          <span>
                            {task.duration_ms < 1000
                              ? `${task.duration_ms}ms`
                              : `${(task.duration_ms / 1000).toFixed(1)}s`}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>
                  <span className="shrink-0 text-xs text-muted-foreground" data-volatile="true">
                    {formatRelativeTime(task.completed_at ?? task.created_at ?? null)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No overnight results"
              description="No tasks were completed in the last 12 hours."
              className="py-8"
            />
          )}
        </CardContent>
      </Card>

      {/* Stalled Projects */}
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Stalled Projects</CardTitle>
          <CardDescription>
            Projects that have stopped making progress.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {stalledProjects.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {stalledProjects.map((project) => (
                <div
                  key={project.id}
                  className="surface-instrument rounded-2xl border px-4 py-3"
                >
                  <div className="flex items-center gap-2">
                    <Badge variant="destructive">{project.id}</Badge>
                    {project.name ? (
                      <span className="text-sm font-medium">{project.name}</span>
                    ) : null}
                  </div>
                  {project.reason ? (
                    <p className="mt-1 text-xs text-muted-foreground">{project.reason}</p>
                  ) : null}
                  {project.stalled_since ? (
                    <p className="mt-1 text-xs text-muted-foreground" data-volatile="true">
                      Since {formatRelativeTime(project.stalled_since)}
                    </p>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No stalled projects"
              description="All projects are making progress."
              className="py-8"
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
