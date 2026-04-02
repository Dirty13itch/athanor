"use client";

import { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";
import { isOperatorSessionLocked, useOperatorSessionStatus } from "@/lib/operator-session";

interface PlanTask {
  id: string;
  agent: string;
  prompt: string;
  priority: string;
  project?: string;
  rationale?: string;
  status?: string;
  task_id?: string;
}

interface WorkPlanSnapshot {
  plan_id: string;
  generated_at: number;
  focus: string;
  tasks: PlanTask[];
  task_count: number;
}

interface OutputFile {
  path: string;
  size_bytes: number;
  modified: number;
}

interface BacklogItem {
  id: string;
  title: string;
  prompt: string;
  owner_agent: string;
  status: string;
  scope_id?: string;
  metadata?: Record<string, unknown>;
}

interface RunItem {
  id: string;
  backlog_id?: string;
  status: string;
  summary?: string;
  updated_at?: string | number | null;
  metadata?: Record<string, unknown>;
}

interface OperatorSummary {
  backlog?: { total?: number; by_status?: Record<string, number> };
  bootstrap?: { active_family?: string; active_program_id?: string; last_updated_at?: string };
  outputs?: { recent?: OutputFile[] };
}

interface WorkPlanData {
  current_plan: WorkPlanSnapshot | null;
  needs_refill: boolean;
  history: WorkPlanSnapshot[];
  recent_outputs: OutputFile[];
}

function timeAgo(ts: number): string {
  const ms = Date.now() - ts * 1000;
  const min = Math.floor(ms / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  return `${Math.floor(hr / 24)}d ago`;
}

function statusColor(status?: string): string {
  switch (status) {
    case "completed":
      return "bg-green-500";
    case "running":
    case "scheduled":
      return "bg-primary animate-pulse";
    case "failed":
    case "blocked":
      return "bg-red-500";
    default:
      return "bg-zinc-500";
  }
}

function agentColor(agent: string): string {
  const map: Record<string, string> = {
    "coding-agent": "text-blue-400",
    "creative-agent": "text-pink-400",
    "media-agent": "text-teal-400",
    "general-assistant": "text-primary",
    "knowledge-agent": "text-purple-400",
    "research-agent": "text-cyan-400",
    "home-agent": "text-green-400",
    "stash-agent": "text-rose-400",
  };
  return map[agent] ?? "text-muted-foreground";
}

function buildPlanFromCanonicalState(
  summary: OperatorSummary,
  backlog: BacklogItem[],
  runs: RunItem[]
): WorkPlanData {
  const latestRunByBacklogId = new Map<string, RunItem>();
  for (const run of runs) {
    const backlogId = String(run.backlog_id ?? run.metadata?.["backlog_id"] ?? "").trim();
    if (!backlogId || latestRunByBacklogId.has(backlogId)) {
      continue;
    }
    latestRunByBacklogId.set(backlogId, run);
  }

  const tasks = backlog.slice(0, 8).map((item) => {
    const latestRun = latestRunByBacklogId.get(item.id);
    const metadata = item.metadata ?? {};
    return {
      id: item.id,
      agent: item.owner_agent,
      prompt: item.prompt || item.title,
      priority: String(metadata["priority_band"] ?? "normal"),
      project: item.scope_id || undefined,
      rationale: String(metadata["last_dispatch_reason"] ?? ""),
      status: latestRun?.status ?? item.status,
      task_id: String(metadata["latest_task_id"] ?? latestRun?.id ?? ""),
    };
  });

  const activeFamily = String(summary.bootstrap?.active_family ?? "").trim();
  const generatedAtRaw = String(summary.bootstrap?.last_updated_at ?? "");
  const generatedAt = generatedAtRaw ? Math.floor(new Date(generatedAtRaw).getTime() / 1000) : Math.floor(Date.now() / 1000);
  const totalBacklog = Number(summary.backlog?.total ?? backlog.length);
  const focus = activeFamily
    ? `Bootstrap focus: ${activeFamily.replace(/_/g, " ")}`
    : totalBacklog > 0
      ? `Operator backlog has ${totalBacklog} captured slices ready for continued execution.`
      : "Operator backlog is empty.";

  return {
    current_plan: tasks.length
      ? {
          plan_id: String(summary.bootstrap?.active_program_id ?? "operator-backlog"),
          generated_at: generatedAt,
          focus,
          tasks,
          task_count: tasks.length,
        }
      : null,
    needs_refill: tasks.length === 0,
    history: [],
    recent_outputs: Array.isArray(summary.outputs?.recent) ? summary.outputs.recent : [],
  };
}

export function WorkPlan() {
  const session = useOperatorSessionStatus();
  const locked = isOperatorSessionLocked(session);
  const [data, setData] = useState<WorkPlanData | null>(null);
  const [loading, setLoading] = useState(true);
  const [redirecting, setRedirecting] = useState(false);
  const [redirectSent, setRedirectSent] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (locked) {
      setData(null);
      setLoading(false);
      return;
    }

    let mounted = true;

    async function fetchData() {
      try {
        const [summaryRes, backlogRes, runsRes] = await Promise.all([
          fetch("/api/operator/summary", { signal: AbortSignal.timeout(5000) }).catch(() => null),
          fetch("/api/operator/backlog?limit=12", { signal: AbortSignal.timeout(5000) }).catch(() => null),
          fetch("/api/operator/runs?limit=25", { signal: AbortSignal.timeout(5000) }).catch(() => null),
        ]);

        if (!mounted) {
          return;
        }

        if (summaryRes?.ok && backlogRes?.ok && runsRes?.ok) {
          const [summary, backlogPayload, runsPayload] = await Promise.all([
            summaryRes.json(),
            backlogRes.json(),
            runsRes.json(),
          ]);
          setData(
            buildPlanFromCanonicalState(
              (summary ?? {}) as OperatorSummary,
              Array.isArray(backlogPayload?.backlog) ? (backlogPayload.backlog as BacklogItem[]) : [],
              Array.isArray(runsPayload?.runs) ? (runsPayload.runs as RunItem[]) : []
            )
          );
        } else {
          setData({ current_plan: null, needs_refill: true, history: [], recent_outputs: [] });
        }
      } catch {
        if (mounted) {
          setData({ current_plan: null, needs_refill: true, history: [], recent_outputs: [] });
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    void fetchData();
    const interval = setInterval(() => {
      void fetchData();
    }, 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [locked]);

  if (locked) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <span className="font-mono text-xs text-primary/70">WP</span>
            <span>Work Plan</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="Unlock required"
            description="The active work plan stays hidden until the operator session is unlocked."
            className="py-6"
          />
        </CardContent>
      </Card>
    );
  }

  async function handleRedirect() {
    const direction = inputRef.current?.value?.trim();
    if (!direction || redirecting) return;

    setRedirecting(true);
    setRedirectSent(false);

    try {
      await fetch("/api/operator/backlog", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "Operator redirect",
          prompt: direction,
          owner_agent: "general-assistant",
          scope_type: "global",
          scope_id: "athanor",
          work_class: "routing",
          priority: 3,
          metadata: {
            redirect_intent: true,
            created_from: "work-plan-card",
          },
          reason: "Created operator redirect from work plan card",
        }),
        signal: AbortSignal.timeout(10000),
      });
    } catch {
      // The dashboard proxy may time out while the agent server still accepts the request.
    }

    setRedirecting(false);
    setRedirectSent(true);
    if (inputRef.current) inputRef.current.value = "";
    setTimeout(() => setRedirectSent(false), 4000);
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="py-4">
          <div className="h-4 w-40 animate-pulse rounded bg-muted" />
        </CardContent>
      </Card>
    );
  }

  const plan = data?.current_plan;
  const tasks = plan?.tasks ?? [];
  const completed = tasks.filter((t) => t.status === "completed").length;
  const running = tasks.filter((t) => ["running", "scheduled"].includes(t.status ?? "")).length;
  const failed = tasks.filter((t) => ["failed", "blocked"].includes(t.status ?? "")).length;
  const recentOutputs = data?.recent_outputs?.slice(0, 4) ?? [];

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <span className="font-mono text-xs text-primary/70">WP</span>
          <span>Work Plan</span>
          {plan && (
            <span className="ml-auto text-xs font-normal text-muted-foreground">
              {timeAgo(plan.generated_at)}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {!plan ? (
          <p className="text-xs text-muted-foreground">
            No canonical work plan is active. Capture a redirect or promote more backlog to keep the builder loop moving.
          </p>
        ) : (
          <>
            {plan.focus ? (
              <p className="text-xs italic text-muted-foreground">{plan.focus}</p>
            ) : null}

            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs">
                <span className="text-muted-foreground">
                  {completed}/{tasks.length} tasks
                </span>
                {running > 0 ? (
                  <span className="flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
                    {running} active
                  </span>
                ) : null}
                {failed > 0 ? (
                  <span className="flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
                    {failed} blocked
                  </span>
                ) : null}
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded bg-zinc-800">
                <div
                  className="h-full bg-primary transition-all"
                  style={{ width: `${tasks.length > 0 ? (completed / tasks.length) * 100 : 0}%` }}
                />
              </div>
            </div>

            <div className="space-y-2">
              {tasks.slice(0, 4).map((task) => (
                <div key={task.id} className="rounded-md border border-border/50 p-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className={`text-xs font-medium ${agentColor(task.agent)}`}>
                        {task.agent}
                      </div>
                      <div className="mt-1 text-sm line-clamp-2">{task.prompt}</div>
                      {task.project ? (
                        <div className="mt-1 text-[11px] text-muted-foreground">{task.project}</div>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full ${statusColor(task.status)}`} />
                      <Badge variant="outline" className="text-[10px]">
                        {task.priority}
                      </Badge>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        <div className="border-t border-border/50 pt-2">
          <div className="mb-2 text-[11px] uppercase tracking-wider text-muted-foreground">
            Redirect the builder
          </div>
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              placeholder="Tell Athanor what to focus on next..."
              className="min-w-0 flex-1 rounded border border-border bg-background px-3 py-2 text-sm outline-none"
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  void handleRedirect();
                }
              }}
            />
            <Button size="sm" onClick={() => void handleRedirect()} disabled={redirecting}>
              {redirecting ? "Sending..." : redirectSent ? "Sent" : "Redirect"}
            </Button>
          </div>
        </div>

        {recentOutputs.length > 0 ? (
          <div className="border-t border-border/50 pt-2">
            <div className="mb-2 text-[11px] uppercase tracking-wider text-muted-foreground">
              Recent outputs
            </div>
            <div className="space-y-1">
              {recentOutputs.map((file) => (
                <div
                  key={file.path}
                  className="flex items-center justify-between text-xs text-muted-foreground"
                >
                  <span className="truncate">{file.path.split(/[\\/]/).pop()}</span>
                  <span>{Math.round(file.size_bytes / 1024)} KB</span>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
