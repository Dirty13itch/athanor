"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface PlannedTask {
  agent: string;
  prompt: string;
  priority: string;
  plan_id: string;
  task_id?: string;
  requires_approval?: boolean;
}

interface WorkPlan {
  plan_id: string;
  generated_at: number;
  focus: string;
  tasks: PlannedTask[];
  task_count: number;
  error?: string;
}

interface Project {
  name: string;
  description: string;
  status: string;
  agents: string[];
  needs_count: number;
  constraints: string[];
}

const PRIORITY_COLORS: Record<string, string> = {
  high: "bg-red-400/20 text-red-400 border-red-400/30",
  normal: "bg-blue-400/20 text-blue-400 border-blue-400/30",
  low: "bg-zinc-400/20 text-zinc-400 border-zinc-400/30",
};

const STATUS_COLORS: Record<string, string> = {
  active: "text-green-400",
  paused: "text-yellow-400",
  complete: "text-muted-foreground",
  planning: "text-blue-400",
};

function PlanCard({ plan, collapsed = false }: { plan: WorkPlan; collapsed?: boolean }) {
  const [open, setOpen] = useState(!collapsed);
  const ts = new Date(plan.generated_at * 1000);

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between p-4 hover:bg-muted/50 transition-colors text-left"
      >
        <div className="space-y-0.5">
          <p className="text-sm font-medium font-mono">{plan.plan_id}</p>
          <p className="text-xs text-muted-foreground">
            {ts.toLocaleString()} · {plan.task_count} tasks
            {plan.focus && ` · ${plan.focus.slice(0, 60)}`}
          </p>
        </div>
        <span className="text-muted-foreground text-xs">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="border-t border-border divide-y divide-border">
          {plan.error ? (
            <p className="p-4 text-sm text-red-400">{plan.error}</p>
          ) : plan.tasks.length === 0 ? (
            <p className="p-4 text-sm text-muted-foreground">No tasks in this plan.</p>
          ) : (
            plan.tasks.map((task, i) => (
              <div key={i} className="p-4 flex items-start gap-3">
                <div className="flex-1 space-y-1.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-medium text-foreground">{task.agent}</span>
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded border ${PRIORITY_COLORS[task.priority] || PRIORITY_COLORS.normal}`}
                    >
                      {task.priority}
                    </span>
                    {task.requires_approval && (
                      <span className="text-xs px-1.5 py-0.5 rounded border bg-amber-400/20 text-amber-400 border-amber-400/30">
                        approval
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {task.prompt.slice(0, 200)}
                    {task.prompt.length > 200 && "…"}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default function WorkPlannerPage() {
  const [currentPlan, setCurrentPlan] = useState<WorkPlan | null>(null);
  const [history, setHistory] = useState<WorkPlan[]>([]);
  const [needsRefill, setNeedsRefill] = useState(false);
  const [projects, setProjects] = useState<Record<string, Project>>({});
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [focus, setFocus] = useState("");
  const [redirectDir, setRedirectDir] = useState("");
  const [redirectStatus, setRedirectStatus] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const [planRes, projRes] = await Promise.all([
        fetch("/api/agents/proxy?path=/v1/workplan"),
        fetch("/api/agents/proxy?path=/v1/projects"),
      ]);
      if (planRes.ok) {
        const d = await planRes.json();
        setCurrentPlan(d.current_plan || null);
        setHistory(d.history || []);
        setNeedsRefill(d.needs_refill || false);
      }
      if (projRes.ok) {
        const d = await projRes.json();
        setProjects(d.projects || {});
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const iv = setInterval(fetchData, 60000);
    return () => clearInterval(iv);
  }, [fetchData]);

  const generatePlan = async () => {
    setGenerating(true);
    try {
      const res = await fetch("/api/agents/proxy?path=/v1/workplan/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ focus }),
      });
      if (res.ok) {
        await fetchData();
        setFocus("");
      }
    } catch {
      // silent
    } finally {
      setGenerating(false);
    }
  };

  const redirectPlan = async () => {
    if (!redirectDir.trim()) return;
    try {
      const res = await fetch("/api/agents/proxy?path=/v1/workplan/redirect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ direction: redirectDir.trim() }),
      });
      if (res.ok) {
        setRedirectStatus("Saved — next plan will reflect this direction.");
        setRedirectDir("");
        setTimeout(() => setRedirectStatus(""), 5000);
        await fetchData();
      }
    } catch {
      // silent
    }
  };

  // Compute next scheduled run (7:00 AM today or tomorrow)
  const nextRun = (() => {
    const now = new Date();
    const target = new Date();
    target.setHours(7, 0, 0, 0);
    if (now >= target) target.setDate(target.getDate() + 1);
    const diff = target.getTime() - now.getTime();
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    return `${h}h ${m}m`;
  })();

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <h1 className="text-2xl font-bold">Work Planner</h1>
        <div className="grid grid-cols-1 gap-4">
          {[...Array(3)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="h-24 bg-muted animate-pulse rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Work Planner</h1>
          <p className="text-sm text-muted-foreground">
            Autonomous task generation · Next run in {nextRun}
            {needsRefill && (
              <span className="ml-2 text-amber-400 font-medium">· Queue low</span>
            )}
          </p>
        </div>
        <button
          onClick={fetchData}
          className="shrink-0 px-3 py-1.5 text-sm border rounded-md hover:bg-muted transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Generate Plan */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Generate Plan Now</CardTitle>
          <CardDescription>
            Optionally specify a focus to steer task selection.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <input
              type="text"
              value={focus}
              onChange={(e) => setFocus(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && generatePlan()}
              placeholder="Focus hint (e.g. eoq, research, infrastructure)…"
              className="flex-1 px-3 py-2 text-sm bg-muted border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <button
              onClick={generatePlan}
              disabled={generating}
              className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {generating ? "Generating…" : "Generate"}
            </button>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Current Plan */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-lg font-semibold">Current Plan</h2>
          {!currentPlan ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              No plan generated yet. First plan runs at 7:00 AM or trigger manually.
            </p>
          ) : (
            <PlanCard plan={currentPlan} collapsed={false} />
          )}

          {history.length > 0 && (
            <>
              <h2 className="text-lg font-semibold pt-2">Recent Plans</h2>
              <div className="space-y-2">
                {history.slice(0, 5).map((plan) => (
                  <PlanCard key={plan.plan_id} plan={plan} collapsed={true} />
                ))}
              </div>
            </>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Redirect / Steer */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Steer Future Plans</CardTitle>
              <CardDescription>
                Saved as a durable preference — influences all future plans.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <textarea
                value={redirectDir}
                onChange={(e) => setRedirectDir(e.target.value)}
                placeholder="e.g. Focus more on EoBQ character scenes, less infrastructure maintenance…"
                rows={3}
                className="w-full px-3 py-2 text-sm bg-muted border rounded-md resize-none focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <button
                onClick={redirectPlan}
                disabled={!redirectDir.trim()}
                className="w-full px-3 py-2 text-sm border rounded-md hover:bg-muted disabled:opacity-50 transition-colors"
              >
                Save Direction
              </button>
              {redirectStatus && (
                <p className="text-xs text-green-400">{redirectStatus}</p>
              )}
            </CardContent>
          </Card>

          {/* Projects */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Projects</CardTitle>
              <CardDescription>
                Active projects the planner sources tasks from.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {Object.keys(projects).length === 0 ? (
                <p className="text-sm text-muted-foreground">No projects loaded.</p>
              ) : (
                Object.entries(projects).map(([id, p]) => (
                  <div key={id} className="space-y-1.5 p-3 rounded-md bg-muted">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{p.name}</span>
                      <span
                        className={`text-xs font-medium ${STATUS_COLORS[p.status] || "text-muted-foreground"}`}
                      >
                        {p.status}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {p.description}
                    </p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{p.needs_count} needs</span>
                      <span>·</span>
                      <span>{p.agents.slice(0, 2).join(", ")}{p.agents.length > 2 ? " +" + (p.agents.length - 2) : ""}</span>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* Schedule info */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Schedule</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Morning plan</span>
                <span className="font-mono">7:00 AM</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Queue refill</span>
                <span className="font-mono">every 2h</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Max tasks/day</span>
                <span className="font-mono">10</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Next run in</span>
                <span className="font-mono text-green-400">{nextRun}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <p className="text-xs text-muted-foreground text-center">
        Auto-refreshes every 60s
      </p>
    </div>
  );
}
