"use client";

import { useState, useEffect } from "react";
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
  timestamp: number;
}

interface TaskItem {
  id: string;
  prompt: string;
  status: string;
  agent: string;
  created_at: number;
}

interface TrustData {
  scores: Record<string, { score: number; level: string; feedback_count: number }>;
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
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!agentName) return;
    setLoading(true);

    const proxy = (path: string) =>
      fetch(`/api/agents/proxy?path=${encodeURIComponent(path)}`)
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null);

    Promise.all([
      proxy("/v1/agents"),
      proxy(`/v1/activity?agent=${agentName}&limit=5`),
      proxy(`/v1/tasks?agent=${agentName}&limit=5`),
      proxy("/v1/trust"),
    ]).then(([agentsData, activityData, tasksData, trustData]) => {
      if (agentsData?.agents) {
        const found = agentsData.agents.find((a: AgentMeta) => a.name === agentName);
        setAgent(found ?? null);
      }
      setActivity(activityData?.activity ?? []);
      setTasks(tasksData?.tasks ?? []);
      if (trustData?.scores?.[agentName]) {
        setTrust(trustData.scores[agentName]);
      } else {
        setTrust(null);
      }
      setLoading(false);
    });
  }, [agentName]);

  function formatTime(ts: number): string {
    if (!ts) return "";
    const d = new Date(ts * 1000);
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

              {/* Trust & Feedback */}
              {trust && (
                <Section title="Trust">
                  <div className="flex items-center gap-4 text-xs">
                    <span>Score: <strong>{trust.score.toFixed(2)}</strong></span>
                    <span>Level: <strong>{trust.level}</strong></span>
                    <span>Feedback: <strong>{trust.feedback_count}</strong></span>
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
