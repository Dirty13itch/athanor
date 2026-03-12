"use client";

import { useEffect, useEffectEvent, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

interface AgentMeta {
  name: string;
  description: string;
  tools: string[];
  type: string;
  schedule?: string;
  status: string;
}

interface ActivityItem {
  agent: string;
  action_type: string;
  input_summary: string;
  output_summary?: string;
  timestamp: number | string;
}

interface TaskItem {
  id: string;
  prompt: string;
  status: string;
  agent: string;
  created_at: number | string;
}

interface RunItem {
  id: string;
  provider: string;
  status: string;
  summary: string;
  created_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  failure_reason?: string | null;
}

interface PatternItem {
  type: string;
  severity: string;
  agent?: string;
  count?: number;
  thumbs_up?: number;
  thumbs_down?: number;
  success_rate?: number;
  runs?: number;
}

interface AgentDetailPanelProps {
  agentName: string | null;
  agentColor: string;
  agentIcon: string;
  onClose: () => void;
}

export function AgentDetailPanel({ agentName, agentColor, agentIcon, onClose }: AgentDetailPanelProps) {
  const router = useRouter();
  const [agent, setAgent] = useState<AgentMeta | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [trust, setTrust] = useState<{ score: number; level: string; feedback_count: number } | null>(null);
  const [patterns, setPatterns] = useState<PatternItem[]>([]);
  const [autonomy, setAutonomy] = useState<Record<string, number>>({});
  const [runs, setRuns] = useState<RunItem[]>([]);
  const [loading, setLoading] = useState(false);

  const loadAgentDetails = useEffectEvent(async (currentAgentName: string) => {
    setLoading(true);

    const fetchJson = (path: string) =>
      fetch(path)
        .then((response) => (response.ok ? response.json() : null))
        .catch(() => null);

    const [agentsData, activityData, tasksData, workforceData, patternsData, autonomyData, runsData] = await Promise.all([
      fetchJson("/api/agents"),
      fetchJson(`/api/activity?agent=${currentAgentName}&limit=5`),
      fetchJson(`/api/workforce/tasks?agent=${currentAgentName}&limit=5`),
      fetchJson("/api/workforce"),
      fetchJson(`/api/insights?agent=${currentAgentName}`),
      fetchJson("/api/autonomy"),
      fetchJson(`/api/workforce/runs?agent=${currentAgentName}&limit=5`),
    ]);

    if (agentsData?.agents) {
      const found = agentsData.agents.find((entry: {
        id: string;
        name: string;
        description: string;
        tools: string[];
        type?: string;
        status: string;
      }) => entry.id === currentAgentName);
      setAgent(
        found
          ? {
              name: found.id,
              description: found.description,
              tools: found.tools,
              type: found.type ?? "reactive",
              status: found.status,
            }
          : null
      );
    }
    setActivity(activityData?.activity ?? []);
    setTasks(tasksData?.tasks ?? []);
    const trustEntry = workforceData?.trust?.find((entry: {
      agentId: string;
      trustScore: number;
      trustGrade: string | null;
      totalFeedback: number;
    }) => entry.agentId === currentAgentName);
    setTrust(
      trustEntry
        ? {
            score: trustEntry.trustScore,
            level: trustEntry.trustGrade ?? "NA",
            feedback_count: trustEntry.totalFeedback,
          }
        : null
    );
    setPatterns(patternsData?.patterns ?? []);
    setRuns(runsData?.runs ?? []);

    const adj: Record<string, number> = {};
    if (autonomyData?.adjustments) {
      for (const [key, val] of Object.entries(autonomyData.adjustments)) {
        if (key.startsWith(`${currentAgentName}:`)) {
          const category = key.split(":")[1];
          adj[category] = val as number;
        }
      }
    }
    setAutonomy(adj);
    setLoading(false);
  });

  useEffect(() => {
    if (!agentName) return;
    void loadAgentDetails(agentName);
  }, [agentName]);

  function formatTime(ts: number | string): string {
    if (!ts) return "";
    const d = new Date(typeof ts === "number" ? ts * 1000 : ts);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `${diffH}h ago`;
    return `${Math.floor(diffH / 24)}d ago`;
  }

  const statusColor: Record<string, string> = {
    completed: "text-green-400",
    running: "text-blue-400",
    failed: "text-red-400",
    cancelled: "text-muted-foreground",
    pending: "text-yellow-400",
  };

  const trustColor: Record<string, string> = {
    A: "bg-green-500/20 text-green-400",
    B: "bg-blue-500/20 text-blue-400",
    C: "bg-yellow-500/20 text-yellow-400",
    D: "bg-red-500/20 text-red-400",
  };

  return (
    <Sheet open={!!agentName} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="bottom" className="max-h-[85vh] rounded-t-xl">
        <SheetHeader className="pb-2">
          <div className="flex items-center gap-3">
            <div
              className="flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold"
              style={{ backgroundColor: agentColor, color: "#111" }}
            >
              {agentIcon}
            </div>
            <div className="min-w-0 flex-1">
              <SheetTitle className="text-base">
                {agentName?.split("-").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ")}
              </SheetTitle>
              <SheetDescription className="truncate text-xs">
                {agent?.description ?? "Loading..."}
              </SheetDescription>
            </div>
            {trust && (
              <Badge className={`shrink-0 ${trustColor[trust.level] ?? "bg-muted text-muted-foreground"}`}>
                {trust.level} ({trust.score.toFixed(1)})
              </Badge>
            )}
          </div>
        </SheetHeader>

        <ScrollArea className="flex-1 px-4 pb-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <span className="text-sm text-muted-foreground animate-pulse">Loading...</span>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Tools */}
              {agent && agent.tools.length > 0 && (
                <Section title="Tools">
                  <div className="flex flex-wrap gap-1">
                    {agent.tools.map((tool) => (
                      <Badge key={tool} variant="outline" className="text-[10px]">
                        {tool}
                      </Badge>
                    ))}
                  </div>
                </Section>
              )}

              {/* Schedule */}
              {agent?.schedule && (
                <Section title="Schedule">
                  <p className="text-xs text-muted-foreground">{agent.schedule}</p>
                </Section>
              )}

              {/* Trust & Autonomy */}
              {(trust || Object.keys(autonomy).length > 0) && (
                <Section title="Trust & Autonomy">
                  <div className="flex items-center gap-4 text-xs flex-wrap">
                    {trust && (
                      <>
                        <span>Score: <strong>{trust.score.toFixed(2)}</strong></span>
                        <span>Level: <strong>{trust.level}</strong></span>
                        <span>Feedback: <strong>{trust.feedback_count}</strong></span>
                      </>
                    )}
                    {Object.entries(autonomy).map(([cat, adj]) => (
                      <span key={cat} className={adj > 0 ? "text-red-400" : adj < 0 ? "text-green-400" : ""}>
                        {cat}: {adj > 0 ? "+" : ""}{adj.toFixed(3)}
                      </span>
                    ))}
                  </div>
                </Section>
              )}

              {/* Detected Patterns */}
              {patterns.length > 0 && (
                <Section title="Patterns">
                  <div className="space-y-1">
                    {patterns.map((p, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <Badge
                          variant={p.severity === "high" ? "destructive" : "outline"}
                          className="text-[10px] shrink-0"
                        >
                          {p.type.replace(/_/g, " ")}
                        </Badge>
                        <span className="text-muted-foreground">
                          {p.type === "failure_cluster" && `${p.count} failures`}
                          {p.type === "negative_feedback_trend" && `${p.thumbs_down}\u2193 vs ${p.thumbs_up}\u2191`}
                          {p.type === "high_escalation_rate" && `${p.count} escalations`}
                          {p.type === "schedule_summary" && `${p.runs} runs`}
                          {p.type === "task_throughput" && `${((p.success_rate ?? 1) * 100).toFixed(0)}% success`}
                        </span>
                      </div>
                    ))}
                  </div>
                </Section>
              )}

              {/* Recent Tasks */}
              <Section title="Recent Tasks">
                {tasks.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No recent tasks</p>
                ) : (
                  <div className="space-y-1.5">
                    {tasks.map((task) => (
                      <div key={task.id} className="flex items-start gap-2 text-xs">
                        <span className={`shrink-0 font-mono ${statusColor[task.status] ?? "text-muted-foreground"}`}>
                          {task.status === "completed" ? "+" : task.status === "failed" ? "x" : task.status === "running" ? "~" : "-"}
                        </span>
                        <span className="min-w-0 flex-1 truncate">{task.prompt}</span>
                        <span className="shrink-0 text-muted-foreground/60">{formatTime(task.created_at)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </Section>

              <Section title="Execution lanes">
                {runs.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No recent execution runs</p>
                ) : (
                  <div className="space-y-1.5">
                    {runs.map((run) => (
                      <div key={run.id} className="rounded-lg border border-border/50 px-2 py-2 text-xs">
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary" className="text-[10px]">{run.provider}</Badge>
                          <Badge variant={run.status === "failed" ? "destructive" : "outline"} className="text-[10px]">
                            {run.status}
                          </Badge>
                          <span className="ml-auto text-muted-foreground/60">
                            {formatTime(run.completed_at ?? run.started_at ?? run.created_at ?? "")}
                          </span>
                        </div>
                        <p className="mt-2 text-muted-foreground">{run.summary}</p>
                        {run.failure_reason ? (
                          <p className="mt-1 text-destructive">{run.failure_reason}</p>
                        ) : null}
                      </div>
                    ))}
                  </div>
                )}
              </Section>

              {/* Recent Activity */}
              <Section title="Recent Activity">
                {activity.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No recent activity</p>
                ) : (
                  <div className="space-y-1.5">
                    {activity.map((item, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs">
                        <Badge variant="outline" className="shrink-0 text-[10px]">{item.action_type}</Badge>
                        <span className="min-w-0 flex-1 truncate">{item.input_summary}</span>
                        <span className="shrink-0 text-muted-foreground/60">{formatTime(item.timestamp)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </Section>
            </div>
          )}
        </ScrollArea>

        <div className="flex gap-2 border-t border-border p-4">
          <Button
            className="flex-1"
            onClick={() => {
              onClose();
              router.push(`/chat?agent=${agentName}`);
            }}
          >
            Chat
          </Button>
          <Button
            variant="outline"
            className="flex-1"
            onClick={() => {
              onClose();
              router.push(`/tasks?agent=${agentName}`);
            }}
          >
            Tasks
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">{title}</h3>
      {children}
    </div>
  );
}
