"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { config } from "@/lib/config";
import { SwipeCard } from "@/components/swipe-card";
import { FeedbackButtons } from "@/components/gen-ui/feedback-buttons";

interface TaskStep {
  index: number;
  type: string;
  tool_name?: string;
  tool_input?: Record<string, unknown>;
  tool_output?: string;
  content?: string;
  timestamp: number;
}

interface Task {
  id: string;
  agent: string;
  prompt: string;
  priority: string;
  status: string;
  result: string;
  error: string;
  steps: TaskStep[];
  created_at: number;
  started_at: number;
  completed_at: number;
  metadata: Record<string, unknown>;
  parent_task_id: string;
}

interface TaskStats {
  total: number;
  by_status: Record<string, number>;
  by_agent: Record<string, number>;
  currently_running: number;
  max_concurrent: number;
  avg_duration_ms: number;
  worker_running: boolean;
}

interface AgentSchedule {
  agent: string;
  interval_seconds: number;
  interval_human: string;
  enabled: boolean;
  last_run: number | null;
  next_run_in: number;
  priority: string;
}

interface ScheduleStatus {
  schedules: AgentSchedule[];
  scheduler_running: boolean;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-500/20 text-yellow-400",
  pending_approval: "bg-amber-500/20 text-amber-400",
  running: "bg-blue-500/20 text-blue-400",
  completed: "bg-green-500/20 text-green-400",
  failed: "bg-red-500/20 text-red-400",
  cancelled: "bg-zinc-500/20 text-zinc-400",
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400",
  high: "bg-orange-500/20 text-orange-400",
  normal: "bg-blue-500/20 text-blue-400",
  low: "bg-zinc-500/20 text-zinc-400",
};

const AGENT_COLORS: Record<string, string> = {
  "general-assistant": "bg-emerald-500/20 text-emerald-400",
  "media-agent": "bg-purple-500/20 text-purple-400",
  "research-agent": "bg-cyan-500/20 text-cyan-400",
  "creative-agent": "bg-pink-500/20 text-pink-400",
  "knowledge-agent": "bg-amber-500/20 text-amber-400",
  "home-agent": "bg-teal-500/20 text-teal-400",
  "coding-agent": "bg-indigo-500/20 text-indigo-400",
  "stash-agent": "bg-rose-500/20 text-rose-400",
};

function formatTime(unix: number): string {
  if (!unix) return "";
  return new Date(unix * 1000).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}min`;
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [stats, setStats] = useState<TaskStats | null>(null);
  const [schedules, setSchedules] = useState<ScheduleStatus | null>(null);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [agentFilter, setAgentFilter] = useState("");
  const [showSubmit, setShowSubmit] = useState(false);
  const [newAgent, setNewAgent] = useState("research-agent");
  const [newPrompt, setNewPrompt] = useState("");
  const [newPriority, setNewPriority] = useState("normal");
  const [submitting, setSubmitting] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status", statusFilter);
      if (agentFilter) params.set("agent", agentFilter);
      params.set("limit", "50");

      const [tasksRes, statsRes, schedRes] = await Promise.all([
        fetch(`${config.agentServer.url}/v1/tasks?${params}`),
        fetch(`${config.agentServer.url}/v1/tasks/stats`),
        fetch(`${config.agentServer.url}/v1/tasks/schedules`),
      ]);

      if (tasksRes.ok) {
        const data = await tasksRes.json();
        setTasks(data.tasks || []);
      }
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
      if (schedRes.ok) {
        setSchedules(await schedRes.json());
      }
    } catch (e) {
      console.error("Failed to fetch tasks:", e);
    }
  }, [statusFilter, agentFilter]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const submitTask = async () => {
    if (!newPrompt.trim()) return;
    setSubmitting(true);
    try {
      const resp = await fetch(`${config.agentServer.url}/v1/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agent: newAgent,
          prompt: newPrompt,
          priority: newPriority,
        }),
      });
      if (resp.ok) {
        setNewPrompt("");
        setShowSubmit(false);
        fetchData();
      }
    } catch (e) {
      console.error("Failed to submit task:", e);
    } finally {
      setSubmitting(false);
    }
  };

  const cancelTask = async (taskId: string) => {
    try {
      await fetch(`${config.agentServer.url}/v1/tasks/${taskId}/cancel`, {
        method: "POST",
      });
      fetchData();
    } catch (e) {
      console.error("Failed to cancel task:", e);
    }
  };

  const approveTask = async (taskId: string) => {
    try {
      await fetch(`${config.agentServer.url}/v1/tasks/${taskId}/approve`, {
        method: "POST",
      });
      fetchData();
    } catch (e) {
      console.error("Failed to approve task:", e);
    }
  };

  const rerunTask = async (task: Task) => {
    try {
      await fetch(`${config.agentServer.url}/v1/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agent: task.agent,
          prompt: task.prompt,
          priority: task.priority,
        }),
      });
      fetchData();
    } catch (e) {
      console.error("Failed to rerun task:", e);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Task Board</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Autonomous agent task execution
          </p>
        </div>
        <button
          onClick={() => setShowSubmit(!showSubmit)}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90"
        >
          + New Task
        </button>
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <Card>
            <CardContent className="pt-4 pb-3 px-4">
              <div className="text-2xl font-bold">{stats.total}</div>
              <div className="text-xs text-muted-foreground">Total Tasks</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-3 px-4">
              <div className="text-2xl font-bold text-blue-400">{stats.currently_running}</div>
              <div className="text-xs text-muted-foreground">Running / {stats.max_concurrent}</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-3 px-4">
              <div className="text-2xl font-bold text-yellow-400">{stats.by_status?.pending || 0}</div>
              <div className="text-xs text-muted-foreground">Pending</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-3 px-4">
              <div className="text-2xl font-bold text-green-400">{stats.by_status?.completed || 0}</div>
              <div className="text-xs text-muted-foreground">Completed</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-3 px-4">
              <div className="text-2xl font-bold">
                {stats.avg_duration_ms ? formatDuration(stats.avg_duration_ms) : "—"}
              </div>
              <div className="text-xs text-muted-foreground">Avg Duration</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Worker Status */}
      {stats && (
        <div className="flex items-center gap-2 text-sm">
          <span className={`w-2 h-2 rounded-full ${stats.worker_running ? "bg-green-500" : "bg-red-500"}`} />
          <span className="text-muted-foreground">
            Task worker {stats.worker_running ? "running" : "stopped"}
          </span>
        </div>
      )}

      {/* Proactive Schedules */}
      {schedules && schedules.schedules.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Proactive Schedules</CardTitle>
              <div className="flex items-center gap-2 text-xs">
                <span className={`w-2 h-2 rounded-full ${schedules.scheduler_running ? "bg-green-500" : "bg-red-500"}`} />
                <span className="text-muted-foreground">
                  Scheduler {schedules.scheduler_running ? "active" : "stopped"}
                </span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              {schedules.schedules.map((s) => (
                <div
                  key={s.agent}
                  className={`flex items-center justify-between p-2 rounded border text-sm ${
                    s.enabled ? "border-border" : "border-border/50 opacity-50"
                  }`}
                >
                  <div>
                    <Badge className={AGENT_COLORS[s.agent] || "bg-zinc-500/20 text-zinc-400"}>
                      {s.agent}
                    </Badge>
                    <span className="text-xs text-muted-foreground ml-2">
                      every {s.interval_human}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {s.enabled ? (
                      s.next_run_in > 0 ? `in ${formatDuration(s.next_run_in * 1000)}` : "due now"
                    ) : (
                      "disabled"
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Submit Task Form */}
      {showSubmit && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Submit New Task</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-muted-foreground">Agent</label>
                <select
                  value={newAgent}
                  onChange={(e) => setNewAgent(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-background border rounded-md text-sm"
                >
                  {["general-assistant", "research-agent", "creative-agent", "media-agent",
                    "knowledge-agent", "home-agent", "coding-agent", "stash-agent"].map((a) => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Priority</label>
                <select
                  value={newPriority}
                  onChange={(e) => setNewPriority(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-background border rounded-md text-sm"
                >
                  {["low", "normal", "high", "critical"].map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Prompt</label>
              <textarea
                value={newPrompt}
                onChange={(e) => setNewPrompt(e.target.value)}
                placeholder="Describe what the agent should do..."
                rows={3}
                className="w-full mt-1 px-3 py-2 bg-background border rounded-md text-sm resize-none"
              />
            </div>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowSubmit(false)}
                className="px-3 py-1.5 border rounded-md text-sm hover:bg-muted"
              >
                Cancel
              </button>
              <button
                onClick={submitTask}
                disabled={submitting || !newPrompt.trim()}
                className="px-3 py-1.5 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
              >
                {submitting ? "Submitting..." : "Submit Task"}
              </button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <div className="flex gap-3">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-1.5 bg-background border rounded-md text-sm"
        >
          <option value="">All Statuses</option>
          <option value="pending_approval">Needs Approval</option>
          <option value="pending">Pending</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <select
          value={agentFilter}
          onChange={(e) => setAgentFilter(e.target.value)}
          className="px-3 py-1.5 bg-background border rounded-md text-sm"
        >
          <option value="">All Agents</option>
          {["general-assistant", "research-agent", "creative-agent", "media-agent",
            "knowledge-agent", "home-agent", "coding-agent", "stash-agent"].map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
      </div>

      {/* Approval Banner */}
      {stats && (stats.by_status?.pending_approval || 0) > 0 && (
        <div className="flex items-center gap-3 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-sm text-amber-400">
          <span className="font-medium">
            {stats.by_status.pending_approval} task{stats.by_status.pending_approval > 1 ? "s" : ""} waiting for your approval
          </span>
          <span className="text-amber-400/60 text-xs">— from work planner (high-impact agents)</span>
        </div>
      )}

      {/* Task List */}
      <div className="space-y-3">
        {tasks.length === 0 && (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              No tasks found. Submit a task to get started.
            </CardContent>
          </Card>
        )}

        {tasks.map((task) => {
          const canApprove = task.status === "pending_approval";
          const canCancel = task.status === "pending" || task.status === "running" || task.status === "pending_approval";
          const canRerun = task.status === "completed" || task.status === "failed";
          return (
          <SwipeCard
            key={task.id}
            onSwipeRight={canRerun ? () => rerunTask(task) : undefined}
            onSwipeLeft={canCancel ? () => cancelTask(task.id) : undefined}
            rightLabel="Re-run"
            leftLabel="Cancel"
            rightColor="bg-blue-500/20"
            leftColor="bg-red-500/20"
            disabled={!canCancel && !canRerun}
          >
          <Card
            className="cursor-pointer hover:border-primary/50 transition-colors"
            onClick={() => setExpandedTask(expandedTask === task.id ? null : task.id)}
          >
            <CardContent className="py-3 px-4">
              {/* Task Header */}
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge className={STATUS_COLORS[task.status] || "bg-zinc-500/20 text-zinc-400"}>
                      {task.status === "running" && (
                        <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse mr-1.5" />
                      )}
                      {task.status}
                    </Badge>
                    <Badge className={AGENT_COLORS[task.agent] || "bg-zinc-500/20 text-zinc-400"}>
                      {task.agent}
                    </Badge>
                    <Badge className={PRIORITY_COLORS[task.priority] || ""}>
                      {task.priority}
                    </Badge>
                    <span className="text-xs text-muted-foreground font-mono">{task.id}</span>
                  </div>
                  <p className="text-sm mt-1.5 line-clamp-2">{task.prompt}</p>
                </div>
                <div className="text-right text-xs text-muted-foreground whitespace-nowrap">
                  <div>{formatTime(task.created_at)}</div>
                  {task.started_at > 0 && task.completed_at > 0 && (
                    <div>{formatDuration((task.completed_at - task.started_at) * 1000)}</div>
                  )}
                  {task.status === "running" && task.started_at > 0 && (
                    <div className="text-blue-400">
                      {formatDuration((Date.now() / 1000 - task.started_at) * 1000)}
                    </div>
                  )}
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex gap-2 mt-2">
                {canApprove && (
                  <button
                    onClick={(e) => { e.stopPropagation(); approveTask(task.id); }}
                    className="px-3 py-1 text-xs border border-amber-500/30 text-amber-400 rounded hover:bg-amber-500/10 font-medium"
                  >
                    ✓ Approve
                  </button>
                )}
                {canCancel && (
                  <button
                    onClick={(e) => { e.stopPropagation(); cancelTask(task.id); }}
                    className="px-2 py-1 text-xs border border-red-500/30 text-red-400 rounded hover:bg-red-500/10"
                  >
                    Cancel
                  </button>
                )}
              </div>

              {/* Expanded Details */}
              {expandedTask === task.id && (
                <div className="mt-3 pt-3 border-t space-y-3">
                  {/* Result */}
                  {task.status === "completed" && task.result && (
                    <div>
                      <div className="text-xs font-medium text-muted-foreground mb-1">Result</div>
                      <pre className="text-xs bg-muted/50 rounded p-3 whitespace-pre-wrap max-h-64 overflow-y-auto">
                        {task.result}
                      </pre>
                      <FeedbackButtons
                        messageContent={`Task ${task.id}: ${task.prompt} → ${task.result.substring(0, 300)}`}
                        agent={task.agent}
                      />
                    </div>
                  )}

                  {/* Error */}
                  {task.status === "failed" && task.error && (
                    <div>
                      <div className="text-xs font-medium text-red-400 mb-1">Error</div>
                      <pre className="text-xs bg-red-500/10 rounded p-3 whitespace-pre-wrap">
                        {task.error}
                      </pre>
                    </div>
                  )}

                  {/* Steps */}
                  {task.steps.length > 0 && (
                    <div>
                      <div className="text-xs font-medium text-muted-foreground mb-1">
                        Steps ({task.steps.length})
                      </div>
                      <div className="space-y-1.5">
                        {task.steps.map((step, i) => (
                          <div key={i} className="flex items-start gap-2 text-xs">
                            <span className="text-muted-foreground font-mono w-4 text-right flex-shrink-0">
                              {step.index + 1}
                            </span>
                            <Badge variant="outline" className="text-[10px] flex-shrink-0">
                              {step.tool_name || step.type}
                            </Badge>
                            {step.tool_output && (
                              <span className="text-muted-foreground truncate">
                                {step.tool_output.slice(0, 120)}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Metadata */}
                  {Object.keys(task.metadata).length > 0 && (
                    <div>
                      <div className="text-xs font-medium text-muted-foreground mb-1">Metadata</div>
                      <pre className="text-xs bg-muted/50 rounded p-2">
                        {JSON.stringify(task.metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
          </SwipeCard>
          );
        })}
      </div>
    </div>
  );
}
