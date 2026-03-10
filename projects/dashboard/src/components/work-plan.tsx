"use client";

import { useEffect, useState, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface PlanTask {
  agent: string;
  prompt: string;
  priority: string;
  project?: string;
  rationale?: string;
  status?: string;
  task_id?: string;
}

interface WorkPlan {
  plan_id: string;
  generated_at: number; // Unix timestamp
  focus: string;
  tasks: PlanTask[];
  task_count: number;
}

interface OutputFile {
  path: string;
  size_bytes: number;
  modified: number;
}

interface WorkPlanData {
  current_plan: WorkPlan | null;
  needs_refill: boolean;
  history: WorkPlan[];
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
      return "bg-amber-500 animate-pulse";
    case "failed":
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
    "general-assistant": "text-amber-400",
    "knowledge-agent": "text-purple-400",
    "research-agent": "text-cyan-400",
    "home-agent": "text-green-400",
    "stash-agent": "text-rose-400",
  };
  return map[agent] ?? "text-muted-foreground";
}

export function WorkPlan() {
  const [data, setData] = useState<WorkPlanData | null>(null);
  const [outputs, setOutputs] = useState<OutputFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [redirecting, setRedirecting] = useState(false);
  const [redirectSent, setRedirectSent] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let mounted = true;

    async function fetchData() {
      try {
        const [workforceRes, outputsRes] = await Promise.all([
          fetch("/api/workforce", { signal: AbortSignal.timeout(5000) }).catch(() => null),
          fetch("/api/outputs", { signal: AbortSignal.timeout(5000) }).catch(() => null),
        ]);

        if (mounted) {
          if (workforceRes?.ok) {
            const workforce = await workforceRes.json();
            const taskStatusById = new Map<string, string>(
              (workforce?.tasks ?? []).map((task: { id: string; status: string }) => [task.id, task.status])
            );
            setData({
              current_plan: workforce?.workplan?.current
                ? {
                    plan_id: workforce.workplan.current.planId,
                    generated_at: Math.floor(new Date(workforce.workplan.current.generatedAt).getTime() / 1000),
                    focus: workforce.workplan.current.focus,
                    tasks: (workforce.workplan.current.tasks ?? []).map((task: {
                      agentId: string;
                      prompt: string;
                      priority: string;
                      projectId?: string | null;
                      rationale?: string | null;
                      taskId?: string | null;
                    }) => ({
                      agent: task.agentId,
                      prompt: task.prompt,
                      priority: task.priority,
                      project: task.projectId ?? undefined,
                      rationale: task.rationale ?? undefined,
                      status: task.taskId ? taskStatusById.get(task.taskId) : undefined,
                      task_id: task.taskId ?? undefined,
                    })),
                    task_count: workforce.workplan.current.taskCount,
                  }
                : null,
              needs_refill: workforce?.workplan?.needsRefill ?? false,
              history: [],
            });
          }
          if (outputsRes?.ok) {
            const d = await outputsRes.json();
            setOutputs(d.outputs ?? []);
          }
          setLoading(false);
        }
      } catch {
        if (mounted) setLoading(false);
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  async function handleRedirect() {
    const direction = inputRef.current?.value?.trim();
    if (!direction || redirecting) return;

    setRedirecting(true);
    setRedirectSent(false);

    try {
      await fetch("/api/workforce/redirect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ direction }),
        signal: AbortSignal.timeout(10000),
      });
    } catch {
      // Server still processes even if proxy times out
    }

    setRedirecting(false);
    setRedirectSent(true);
    if (inputRef.current) inputRef.current.value = "";

    // Clear "sent" indicator after a few seconds
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
  const running = tasks.filter((t) => t.status === "running").length;
  const failed = tasks.filter((t) => t.status === "failed").length;
  const recentOutputs = outputs.slice(0, 4);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <span className="font-mono text-xs text-primary/70">WP</span>
          <span>Work Plan</span>
          {plan && (
            <span className="text-xs font-normal text-muted-foreground ml-auto">
              {timeAgo(plan.generated_at)}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {!plan ? (
          <p className="text-xs text-muted-foreground">
            No active work plan. The scheduler generates plans at 7:00 AM or when the queue runs low.
          </p>
        ) : (
          <>
            {/* Focus / summary */}
            {plan.focus && (
              <p className="text-xs text-muted-foreground italic">
                {plan.focus}
              </p>
            )}

            {/* Progress bar */}
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs">
                <span className="text-muted-foreground">
                  {completed}/{tasks.length} tasks
                </span>
                {running > 0 && (
                  <span className="flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
                    {running} running
                  </span>
                )}
                {failed > 0 && (
                  <span className="flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
                    {failed} failed
                  </span>
                )}
                {data?.needs_refill && (
                  <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                    needs refill
                  </Badge>
                )}
              </div>
              <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full bg-primary transition-all duration-500"
                  style={{ width: `${tasks.length > 0 ? (completed / tasks.length) * 100 : 0}%` }}
                />
              </div>
            </div>

            {/* Task list */}
            <div className="space-y-1.5">
              {tasks.map((task, i) => (
                <div
                  key={task.task_id ?? i}
                  className="flex items-start gap-2 text-xs"
                >
                  <span className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${statusColor(task.status)}`} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className={`font-mono text-[10px] ${agentColor(task.agent)}`}>
                        {task.agent.replace("-agent", "").replace("-assistant", "")}
                      </span>
                      {task.project && (
                        <span className="text-[10px] text-muted-foreground/50">
                          {task.project}
                        </span>
                      )}
                    </div>
                    <p className="text-muted-foreground leading-relaxed line-clamp-2">
                      {task.prompt}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* Recent outputs */}
        {recentOutputs.length > 0 && (
          <div className="border-t border-border pt-2 space-y-1">
            <span className="text-[10px] uppercase text-muted-foreground tracking-wider">
              Recent Outputs
            </span>
            {recentOutputs.map((o) => (
              <div key={o.path} className="flex items-center gap-2 text-xs">
                <span className="h-1 w-1 rounded-full bg-green-500/60 shrink-0" />
                <span className="font-mono text-muted-foreground truncate">
                  {o.path.split("/").slice(-2).join("/")}
                </span>
                <span className="text-[10px] text-muted-foreground/50 ml-auto shrink-0">
                  {timeAgo(o.modified)}
                </span>
              </div>
            ))}
            {outputs.length > 4 && (
              <p className="text-[10px] text-muted-foreground">
                +{outputs.length - 4} more
              </p>
            )}
          </div>
        )}

        {/* Steering input */}
        <div className="border-t border-border pt-2">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              placeholder="Steer the plan..."
              className="flex-1 rounded-md border border-border bg-background px-2.5 py-1.5 text-xs placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/50"
              onKeyDown={(e) => {
                if (e.key === "Enter") handleRedirect();
              }}
              disabled={redirecting}
            />
            <button
              onClick={handleRedirect}
              disabled={redirecting}
              className="rounded-md border border-border px-3 py-1.5 text-xs font-medium hover:bg-accent transition-colors disabled:opacity-50"
            >
              {redirecting ? "..." : "Steer"}
            </button>
          </div>
          {redirectSent && (
            <p className="text-[10px] text-green-400 mt-1">
              Preference saved — new plan generating in background
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
