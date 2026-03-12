"use client";

import { useDeferredValue, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bot, Goal, RefreshCcw, ShieldAlert, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { ResearchJobsCard } from "@/components/research-jobs-card";
import { StatCard } from "@/components/stat-card";
import { getWorkforce } from "@/lib/api";
import { type WorkforceSnapshot, type WorkforceTask } from "@/lib/contracts";
import { compactText, formatRelativeTime, formatTimestamp } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import { useUrlState } from "@/lib/url-state";

type TaskFilter = "all" | "queued" | "approval" | "running" | "completed" | "failed";

function getTaskLabel(status: WorkforceTask["status"]) {
  switch (status) {
    case "pending_approval":
      return "Needs approval";
    case "running":
      return "Running";
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
    case "cancelled":
      return "Cancelled";
    default:
      return "Queued";
  }
}

function getProjectName(snapshot: WorkforceSnapshot, projectId: string | null) {
  if (!projectId) {
    return "Unscoped";
  }

  return snapshot.projects.find((project) => project.id === projectId)?.name ?? projectId;
}

function getAgentName(snapshot: WorkforceSnapshot, agentId: string) {
  return snapshot.agents.find((agent) => agent.id === agentId)?.name ?? agentId;
}

function formatCountdown(timestamp: string) {
  const diffMs = new Date(timestamp).getTime() - Date.now();
  if (diffMs <= 0) {
    return "due now";
  }

  const totalMinutes = Math.round(diffMs / 60000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
}

async function postJson(path: string, body: Record<string, string>) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
}

async function postWithoutBody(path: string) {
  const response = await fetch(path, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
}

export function WorkPlannerConsole({ initialSnapshot }: { initialSnapshot: WorkforceSnapshot }) {
  const { getSearchValue, setSearchValue } = useUrlState();
  const [focus, setFocus] = useState("");
  const [direction, setDirection] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const search = getSearchValue("search", "");
  const project = getSearchValue("project", "all");
  const status = getSearchValue("status", "queued") as TaskFilter;
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

  if (workforceQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Workforce" title="Work Planner" description="The workforce snapshot failed to load." />
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

  const snapshot = workforceQuery.data ?? initialSnapshot;
  const visibleTasks = snapshot.tasks.filter((task) => {
    if (project !== "all" && task.projectId !== project) {
      return false;
    }
    if (status === "approval" && task.status !== "pending_approval") {
      return false;
    }
    if (status === "running" && task.status !== "running") {
      return false;
    }
    if (status === "completed" && task.status !== "completed") {
      return false;
    }
    if (status === "failed" && task.status !== "failed") {
      return false;
    }
    if (status === "queued" && !["pending", "pending_approval", "running"].includes(task.status)) {
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
  });
  const approvalQueue = snapshot.tasks.filter((task) => task.status === "pending_approval");

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Workforce"
        title="Work Planner"
        description="Plan generation, queue posture, approvals, and project-state visibility for the Athanor operator loop."
        actions={
          <>
            <Button variant="outline" onClick={() => void workforceQuery.refetch()} disabled={workforceQuery.isFetching}>
              <RefreshCcw className={`mr-2 h-4 w-4 ${workforceQuery.isFetching ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button
              onClick={() =>
                void handleAction("generate", async () => {
                  await postJson("/api/workforce/plan", { focus });
                  setFocus("");
                })
              }
              disabled={busy === "generate"}
            >
              <Sparkles className="mr-2 h-4 w-4" />
              Generate plan
            </Button>
          </>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Queued work" value={`${snapshot.summary.pendingTasks + snapshot.summary.runningTasks}`} detail={`${snapshot.summary.runningTasks} running now.`} icon={<Bot className="h-5 w-5" />} />
          <StatCard label="Approvals" value={`${snapshot.summary.pendingApprovals}`} detail={snapshot.summary.pendingApprovals > 0 ? "Human review required." : "No actions waiting."} tone={snapshot.summary.pendingApprovals > 0 ? "warning" : "success"} icon={<ShieldAlert className="h-5 w-5" />} />
          <StatCard label="Active goals" value={`${snapshot.summary.activeGoals}`} detail={`${snapshot.summary.queuedProjects} projects have active queue pressure.`} icon={<Goal className="h-5 w-5" />} />
          <StatCard label="Next run" value={formatCountdown(snapshot.workplan.schedule.nextRunAt)} detail={formatTimestamp(snapshot.workplan.schedule.nextRunAt)} />
        </div>
      </PageHeader>

      {feedback ? <ErrorPanel title="Planner feedback" description={feedback} /> : null}

      <ResearchJobsCard />

      <div className="grid gap-4 xl:grid-cols-[1.35fr_1fr]">
        <Card className="border-border/70 bg-card/70">
          <CardHeader>
            <CardTitle className="text-lg">Current plan</CardTitle>
            <CardDescription>Latest plan plus quick operator steering.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {snapshot.workplan.current ? (
              <div className="rounded-2xl border border-border/70 bg-background/20 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge>{snapshot.workplan.current.planId}</Badge>
                  <Badge variant="outline">{snapshot.workplan.current.taskCount} tasks</Badge>
                  {snapshot.workplan.needsRefill ? <Badge variant="destructive">Needs refill</Badge> : null}
                </div>
                <p className="mt-3 text-sm text-muted-foreground">{snapshot.workplan.current.focus || "No explicit focus recorded."}</p>
                <div className="mt-4 space-y-3">
                  {snapshot.workplan.current.tasks.map((task) => (
                    <div key={`${task.taskId ?? task.prompt}`} className="rounded-xl border border-border/60 bg-background/40 p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="secondary">{getAgentName(snapshot, task.agentId)}</Badge>
                        {task.projectId ? <Badge variant="outline">{getProjectName(snapshot, task.projectId)}</Badge> : null}
                        <Badge variant="outline">{task.priority}</Badge>
                        {task.requiresApproval ? <Badge variant="destructive">approval</Badge> : null}
                      </div>
                      <p className="mt-2 text-sm">{task.prompt}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <EmptyState title="No plan yet" description="Generate a plan or wait for the next scheduled run." />
            )}

            <div className="grid gap-3 lg:grid-cols-2">
              <div className="space-y-2">
                <p className="text-sm font-medium">Focus hint</p>
                <div className="flex gap-2">
                  <Input value={focus} onChange={(event) => setFocus(event.target.value)} placeholder="eoq, infra drift, media..." />
                </div>
              </div>
              <div className="space-y-2">
                <p className="text-sm font-medium">Steer future plans</p>
                <textarea value={direction} onChange={(event) => setDirection(event.target.value)} rows={3} className="w-full rounded-xl border border-border/70 bg-background/30 px-3 py-2 text-sm outline-none transition focus:border-primary" placeholder="Keep EoBQ momentum ahead of low-value infrastructure churn." />
                <Button
                  variant="outline"
                  onClick={() =>
                    void handleAction("redirect", async () => {
                      await postJson("/api/workforce/redirect", { direction });
                      setDirection("");
                    })
                  }
                  disabled={busy === "redirect" || !direction.trim()}
                >
                  Save direction
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-card/70">
          <CardHeader>
            <CardTitle className="text-lg">Approval lane</CardTitle>
            <CardDescription>High-impact tasks waiting on operator judgment.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {approvalQueue.length > 0 ? (
              approvalQueue.map((task) => (
                <div key={task.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">{getAgentName(snapshot, task.agentId)}</Badge>
                    {task.projectId ? <Badge variant="outline">{getProjectName(snapshot, task.projectId)}</Badge> : null}
                  </div>
                  <p className="mt-3 text-sm">{compactText(task.prompt, 140)}</p>
                  <div className="mt-3 flex gap-2">
                    <Button size="sm" onClick={() => void handleAction(`approve:${task.id}`, () => postWithoutBody(`/api/workforce/tasks/${task.id}/approve`))}>Approve</Button>
                    <Button size="sm" variant="outline" onClick={() => void handleAction(`cancel:${task.id}`, () => postWithoutBody(`/api/workforce/tasks/${task.id}/cancel`))}>Cancel</Button>
                  </div>
                </div>
              ))
            ) : (
              <EmptyState title="No approvals queued" description="The workforce is operating within current autonomy bounds." className="py-8" />
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.35fr_1fr]">
        <Card className="border-border/70 bg-card/70">
          <CardHeader>
            <CardTitle className="text-lg">Queue</CardTitle>
            <CardDescription>URL-persisted filters for operator review and handoff.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input value={search} onChange={(event) => setSearchValue("search", event.target.value || null)} placeholder="Search tasks" />
            <div className="flex flex-wrap gap-2">
              {["queued", "approval", "running", "completed", "failed", "all"].map((value) => (
                <button key={value} type="button" onClick={() => setSearchValue("status", value === "queued" ? null : value)} className={`rounded-full border px-3 py-1 text-xs transition ${status === value ? "border-primary bg-primary/10 text-primary" : "border-border/70 text-muted-foreground hover:bg-accent"}`}>{value}</button>
              ))}
              {snapshot.projects.map((entry) => (
                <button key={entry.id} type="button" onClick={() => setSearchValue("project", project === entry.id ? null : entry.id)} className={`rounded-full border px-3 py-1 text-xs transition ${project === entry.id ? "border-primary bg-primary/10 text-primary" : "border-border/70 text-muted-foreground hover:bg-accent"}`}>{entry.name}</button>
              ))}
            </div>

            {visibleTasks.length > 0 ? (
              <div className="space-y-3">
                {visibleTasks.map((task) => (
                  <div key={task.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">{getTaskLabel(task.status)}</Badge>
                      <Badge variant="secondary">{getAgentName(snapshot, task.agentId)}</Badge>
                      {task.projectId ? <Badge variant="outline">{getProjectName(snapshot, task.projectId)}</Badge> : null}
                    </div>
                    <p className="mt-3 text-sm">{task.prompt}</p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      Created {formatRelativeTime(task.createdAt)}
                      {task.planId ? ` · ${task.planId}` : ""}
                    </p>
                    {task.error ? <p className="mt-2 text-xs text-red-200">{task.error}</p> : null}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="No tasks match the current filters" description="Adjust the filters or generate a fresh plan." />
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="border-border/70 bg-card/70">
            <CardHeader>
              <CardTitle className="text-lg">Project posture</CardTitle>
              <CardDescription>Queue pressure and mapped agents by project.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {snapshot.projects.map((entry) => (
                <div key={entry.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">{entry.name}</p>
                      <p className="mt-1 text-sm text-muted-foreground">{entry.pendingTasks + entry.pendingApprovals + entry.runningTasks} active items</p>
                    </div>
                    <Badge variant={entry.firstClass ? "default" : "outline"}>{entry.status}</Badge>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                    <Metric label="Pending" value={String(entry.pendingTasks)} />
                    <Metric label="Approval" value={String(entry.pendingApprovals)} />
                    <Metric label="Running" value={String(entry.runningTasks)} />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="border-border/70 bg-card/70">
            <CardHeader>
              <CardTitle className="text-lg">Active goals</CardTitle>
              <CardDescription>Steering context shaping the next wave of work.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {snapshot.goals.length > 0 ? (
                snapshot.goals.map((goal) => (
                  <div key={goal.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">{goal.priority}</Badge>
                      <Badge variant="secondary">{goal.agentId === "global" ? "All agents" : getAgentName(snapshot, goal.agentId)}</Badge>
                    </div>
                    <p className="mt-3 text-sm">{goal.text}</p>
                  </div>
                ))
              ) : (
                <EmptyState title="No active goals" description="Add goals to steer the workforce." className="py-8" />
              )}
            </CardContent>
          </Card>
        </div>
      </div>
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
