"use client";

import { useDeferredValue, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PlayCircle, RefreshCcw, ShieldAlert, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { SubscriptionControlCard } from "@/components/subscription-control-card";
import { StatCard } from "@/components/stat-card";
import { getWorkforce } from "@/lib/api";
import { type WorkforceSnapshot, type WorkforceTask } from "@/lib/contracts";
import { compactText, formatRelativeTime, formatTimestamp } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import { useUrlState } from "@/lib/url-state";
import {
  getAgentName,
  getProjectName,
  getTaskLabel,
  postJson,
  postWithoutBody,
} from "@/features/workforce/helpers";

type TaskFilter = "all" | "queued" | "approval" | "running" | "completed" | "failed";

function matchesStatus(task: WorkforceTask, filter: TaskFilter) {
  switch (filter) {
    case "approval":
      return task.status === "pending_approval";
    case "running":
      return task.status === "running";
    case "completed":
      return task.status === "completed";
    case "failed":
      return task.status === "failed";
    case "queued":
      return ["pending", "pending_approval", "running"].includes(task.status);
    default:
      return true;
  }
}

function formatDuration(durationMs: number | null) {
  if (!durationMs || durationMs <= 0) {
    return "--";
  }
  if (durationMs < 1000) {
    return `${durationMs}ms`;
  }
  if (durationMs < 60_000) {
    return `${(durationMs / 1000).toFixed(1)}s`;
  }
  return `${(durationMs / 60_000).toFixed(1)}m`;
}

export function TasksConsole({ initialSnapshot }: { initialSnapshot: WorkforceSnapshot }) {
  const { getSearchValue, setSearchValue } = useUrlState();
  const [showComposer, setShowComposer] = useState(false);
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [newAgent, setNewAgent] = useState("research-agent");
  const [newPriority, setNewPriority] = useState<WorkforceTask["priority"]>("normal");
  const [newPrompt, setNewPrompt] = useState("");

  const search = getSearchValue("search", "");
  const status = getSearchValue("status", "queued") as TaskFilter;
  const agent = getSearchValue("agent", "all");
  const deferredSearch = useDeferredValue(search.trim().toLowerCase());

  const workforceQuery = useQuery({
    queryKey: queryKeys.workforce,
    queryFn: getWorkforce,
    initialData: initialSnapshot,
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });

  async function handleAction(action: string, run: () => Promise<void>) {
    setBusy(action);
    setFeedback(null);
    try {
      await run();
      await workforceQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Request failed.");
    } finally {
      setBusy(null);
    }
  }

  const snapshot = workforceQuery.data ?? initialSnapshot;
  const visibleTasks = useMemo(
    () =>
      snapshot.tasks.filter((task) => {
        if (agent !== "all" && task.agentId !== agent) {
          return false;
        }
        if (!matchesStatus(task, status)) {
          return false;
        }
        if (!deferredSearch) {
          return true;
        }
        return (
          task.prompt.toLowerCase().includes(deferredSearch) ||
          getAgentName(snapshot, task.agentId).toLowerCase().includes(deferredSearch) ||
          getProjectName(snapshot, task.projectId).toLowerCase().includes(deferredSearch)
        );
      }),
    [agent, deferredSearch, snapshot, status]
  );

  if (workforceQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Workforce" title="Task Board" description="The workforce task snapshot failed to load." />
        <ErrorPanel
          description={
            workforceQuery.error instanceof Error
              ? workforceQuery.error.message
              : "Failed to load workforce data."
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Workforce"
        title="Task Board"
        description="Operator review, submission, reruns, and human-in-the-loop control for the active workforce queue."
        actions={
          <>
            <Button variant="outline" onClick={() => void workforceQuery.refetch()} disabled={workforceQuery.isFetching}>
              <RefreshCcw className={`mr-2 h-4 w-4 ${workforceQuery.isFetching ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button variant="outline" onClick={() => setShowComposer((current) => !current)}>
              <Sparkles className="mr-2 h-4 w-4" />
              {showComposer ? "Hide composer" : "New task"}
            </Button>
          </>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Queued" value={`${snapshot.summary.pendingTasks}`} detail={`${snapshot.summary.runningTasks} tasks currently running.`} icon={<PlayCircle className="h-5 w-5" />} />
          <StatCard label="Approvals" value={`${snapshot.summary.pendingApprovals}`} detail={snapshot.summary.pendingApprovals > 0 ? "Human review required." : "Autonomy within current bounds."} tone={snapshot.summary.pendingApprovals > 0 ? "warning" : "success"} icon={<ShieldAlert className="h-5 w-5" />} />
          <StatCard label="Completed" value={`${snapshot.summary.completedTasks}`} detail={`${snapshot.summary.failedTasks} failures still need review.`} />
          <StatCard label="Projects in motion" value={`${snapshot.summary.queuedProjects}`} detail={`${snapshot.summary.activeProjects} active projects in the current system posture.`} />
        </div>
      </PageHeader>

      {feedback ? <ErrorPanel title="Task feedback" description={feedback} /> : null}

      <SubscriptionControlCard
        title="Execution leases"
        description="See which premium lanes are available before handing larger coding or research work to the workforce."
        requester="coding-agent"
        taskClass="async_backlog_execution"
        compact
      />

      {showComposer ? (
        <Card className="border-border/70 bg-card/70">
          <CardHeader>
            <CardTitle className="text-lg">Submit task</CardTitle>
            <CardDescription>Create explicit workforce work outside the current planner cycle.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-2 text-sm">
                <span className="font-medium">Agent</span>
                <select
                  value={newAgent}
                  onChange={(event) => setNewAgent(event.target.value)}
                  className="w-full rounded-xl border border-border/70 bg-background/30 px-3 py-2 text-sm outline-none transition focus:border-primary"
                >
                  {snapshot.agents.map((entry) => (
                    <option key={entry.id} value={entry.id}>
                      {entry.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-2 text-sm">
                <span className="font-medium">Priority</span>
                <select
                  value={newPriority}
                  onChange={(event) => setNewPriority(event.target.value as WorkforceTask["priority"])}
                  className="w-full rounded-xl border border-border/70 bg-background/30 px-3 py-2 text-sm outline-none transition focus:border-primary"
                >
                  {["low", "normal", "high", "critical"].map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className="space-y-2 text-sm">
              <span className="font-medium">Prompt</span>
              <textarea
                rows={4}
                value={newPrompt}
                onChange={(event) => setNewPrompt(event.target.value)}
                placeholder="Describe the work to execute."
                className="w-full rounded-xl border border-border/70 bg-background/30 px-3 py-2 text-sm outline-none transition focus:border-primary"
              />
            </label>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={() =>
                  void handleAction("submit", async () => {
                    await postJson("/api/workforce/tasks", {
                      agent: newAgent,
                      prompt: newPrompt.trim(),
                      priority: newPriority,
                    });
                    setNewPrompt("");
                    setShowComposer(false);
                  })
                }
                disabled={busy === "submit" || !newPrompt.trim()}
              >
                Submit task
              </Button>
              <Button variant="outline" onClick={() => setShowComposer(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <Card className="border-border/70 bg-card/70">
        <CardHeader>
          <CardTitle className="text-lg">Queue filters</CardTitle>
          <CardDescription>Persisted in the URL for operator handoff and quick review.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input value={search} onChange={(event) => setSearchValue("search", event.target.value || null)} placeholder="Search prompts, agents, or projects" />
          <div className="flex flex-wrap gap-2">
            {(["queued", "approval", "running", "completed", "failed", "all"] as TaskFilter[]).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setSearchValue("status", value === "queued" ? null : value)}
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
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setSearchValue("agent", null)}
              className={`rounded-full border px-3 py-1 text-xs transition ${
                agent === "all"
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border/70 text-muted-foreground hover:bg-accent"
              }`}
            >
              All agents
            </button>
            {snapshot.agents.map((entry) => (
              <button
                key={entry.id}
                type="button"
                onClick={() => setSearchValue("agent", agent === entry.id ? null : entry.id)}
                className={`rounded-full border px-3 py-1 text-xs transition ${
                  agent === entry.id
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border/70 text-muted-foreground hover:bg-accent"
                }`}
              >
                {entry.name}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/70 bg-card/70">
        <CardHeader>
          <CardTitle className="text-lg">Tasks</CardTitle>
          <CardDescription>{visibleTasks.length} tasks match the current filters.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {visibleTasks.length > 0 ? (
            visibleTasks.map((task) => {
              const expanded = expandedTaskId === task.id;
              return (
                <div key={task.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                  <button
                    type="button"
                    onClick={() => setExpandedTaskId(expanded ? null : task.id)}
                    className="w-full text-left"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">{getTaskLabel(task.status)}</Badge>
                      <Badge variant="secondary">{getAgentName(snapshot, task.agentId)}</Badge>
                      {task.projectId ? <Badge variant="outline">{getProjectName(snapshot, task.projectId)}</Badge> : null}
                      <Badge variant="outline">{task.priority}</Badge>
                    </div>
                    <p className="mt-3 text-sm">{compactText(task.prompt, 180)}</p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      Created {formatRelativeTime(task.createdAt)}
                      {task.planId ? ` | ${task.planId}` : ""}
                      {task.durationMs ? ` | ${formatDuration(task.durationMs)}` : ""}
                    </p>
                  </button>

                  {expanded ? (
                    <div className="mt-4 space-y-4 border-t border-border/60 pt-4">
                      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                        <Metric label="Created" value={formatTimestamp(task.createdAt)} />
                        <Metric label="Started" value={formatTimestamp(task.startedAt)} />
                        <Metric label="Completed" value={formatTimestamp(task.completedAt)} />
                        <Metric label="Steps" value={`${task.stepCount}`} />
                      </div>
                      {task.rationale ? (
                        <div>
                          <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">Rationale</p>
                          <p className="mt-2 text-sm">{task.rationale}</p>
                        </div>
                      ) : null}
                      {task.result ? (
                        <div>
                          <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">Result</p>
                          <p className="mt-2 whitespace-pre-wrap rounded-xl border border-border/60 bg-background/30 p-3 text-sm">
                            {task.result}
                          </p>
                        </div>
                      ) : null}
                      {task.error ? (
                        <div>
                          <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">Error</p>
                          <p className="mt-2 whitespace-pre-wrap rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-100">
                            {task.error}
                          </p>
                        </div>
                      ) : null}
                      <div className="flex flex-wrap gap-2">
                        {task.status === "pending_approval" ? (
                          <Button
                            size="sm"
                            onClick={() =>
                              void handleAction(`approve:${task.id}`, () =>
                                postWithoutBody(`/api/workforce/tasks/${task.id}/approve`)
                              )
                            }
                          >
                            Approve
                          </Button>
                        ) : null}
                        {["pending", "pending_approval", "running"].includes(task.status) ? (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() =>
                              void handleAction(`cancel:${task.id}`, () =>
                                postWithoutBody(`/api/workforce/tasks/${task.id}/cancel`)
                              )
                            }
                          >
                            Cancel
                          </Button>
                        ) : null}
                        {["completed", "failed", "cancelled"].includes(task.status) ? (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() =>
                              void handleAction(`rerun:${task.id}`, () =>
                                postJson("/api/workforce/tasks", {
                                  agent: task.agentId,
                                  prompt: task.prompt,
                                  priority: task.priority,
                                  metadata: {
                                    source: "dashboard_rerun",
                                    parent_task_id: task.id,
                                    project: task.projectId,
                                  },
                                })
                              )
                            }
                          >
                            Re-run
                          </Button>
                        ) : null}
                      </div>
                    </div>
                  ) : null}
                </div>
              );
            })
          ) : (
            <EmptyState title="No tasks match the current filters" description="Adjust the filters or submit a new task." className="py-10" />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/30 px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 font-medium">{value}</p>
    </div>
  );
}
