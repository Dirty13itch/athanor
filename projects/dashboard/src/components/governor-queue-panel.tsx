"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Play, Plus, RefreshCw, Clock, CheckCircle, XCircle, Loader2, Zap } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface Task {
  id: string;
  title: string;
  description: string;
  repo: string;
  complexity: string;
  content_class: string;
  assigned_to: string | null;
  status: string;
  created_at: string;
}

interface GovernorData {
  stats: { total: number; queued: number; running: number; done: number; failed: number } | null;
  queue: Task[];
  attention: Array<{ type: string; priority: string; title: string; detail: string; action: string }>;
}

const statusIcon = {
  queued: <Clock className="h-3.5 w-3.5 text-muted-foreground" />,
  assigned: <Loader2 className="h-3.5 w-3.5 text-amber-400 animate-spin" />,
  running: <Zap className="h-3.5 w-3.5 text-primary animate-pulse" />,
  done: <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />,
  failed: <XCircle className="h-3.5 w-3.5 text-red-400" />,
  review: <RefreshCw className="h-3.5 w-3.5 text-amber-400" />,
};

const complexityColor = {
  critical: "text-red-400 border-red-500/30",
  high: "text-amber-400 border-amber-500/30",
  medium: "text-primary border-primary/30",
  low: "text-muted-foreground border-border",
};

export function GovernorQueuePanel() {
  const queryClient = useQueryClient();
  const [showAddTask, setShowAddTask] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newComplexity, setNewComplexity] = useState("medium");
  const [newContentClass, setNewContentClass] = useState("cloud_safe");

  const { data, isLoading } = useQuery<GovernorData>({
    queryKey: ["governor-queue"],
    queryFn: () => fetch("/api/governor/queue").then((r) => r.json()),
    refetchInterval: 15_000,
  });

  const dispatchMutation = useMutation({
    mutationFn: () => fetch("/api/governor/dispatch", { method: "POST" }).then((r) => r.json()),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["governor-queue"] }),
  });

  const addTaskMutation = useMutation({
    mutationFn: (task: { title: string; description: string; complexity: string; content_class: string; repo: string }) =>
      fetch("/api/governor/queue", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(task) }).then((r) => r.json()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["governor-queue"] });
      setNewTitle("");
      setNewDesc("");
      setShowAddTask(false);
    },
  });

  const stats = data?.stats;
  const tasks = data?.queue ?? [];

  return (
    <Card className="surface-panel">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle className="text-base font-semibold">Coding Agent Queue</CardTitle>
          <p className="text-xs text-muted-foreground mt-0.5">
            {stats ? `${stats.queued} queued · ${stats.running} running · ${stats.done} done` : "Loading..."}
          </p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => setShowAddTask(!showAddTask)}>
            <Plus className="h-3.5 w-3.5 mr-1" /> Add Task
          </Button>
          <Button size="sm" onClick={() => dispatchMutation.mutate()} disabled={!stats?.queued || dispatchMutation.isPending}>
            <Play className="h-3.5 w-3.5 mr-1" /> Dispatch Now
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {showAddTask && (
          <div className="rounded-xl border border-primary/20 bg-primary/5 p-3 space-y-2">
            <input
              className="w-full rounded-lg bg-background/60 border border-border/50 px-3 py-2 text-sm outline-none focus:border-primary/50"
              placeholder="Task title..."
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
            />
            <textarea
              className="w-full rounded-lg bg-background/60 border border-border/50 px-3 py-2 text-sm outline-none focus:border-primary/50 resize-none"
              placeholder="Description..."
              rows={2}
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
            />
            <div className="flex gap-2 items-center">
              <select
                className="rounded-lg bg-background/60 border border-border/50 px-2 py-1.5 text-xs"
                value={newComplexity}
                onChange={(e) => setNewComplexity(e.target.value)}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
              <select
                className="rounded-lg bg-background/60 border border-border/50 px-2 py-1.5 text-xs"
                value={newContentClass}
                onChange={(e) => setNewContentClass(e.target.value)}
              >
                <option value="cloud_safe">Cloud Safe</option>
                <option value="sovereign_only">Sovereign Only (NSFW/Local)</option>
              </select>
              <Button
                size="sm"
                className="ml-auto"
                onClick={() => addTaskMutation.mutate({ title: newTitle, description: newDesc, complexity: newComplexity, content_class: newContentClass, repo: "athanor" })}
                disabled={!newTitle || addTaskMutation.isPending}
              >
                Queue
              </Button>
            </div>
          </div>
        )}

        {tasks.length === 0 && !isLoading && (
          <p className="text-sm text-muted-foreground text-center py-4">Queue empty. Add tasks or wait for self-improvement proposals.</p>
        )}

        {tasks.map((task) => (
          <div key={task.id} className="flex items-start gap-3 rounded-xl border border-border/40 bg-background/30 px-3 py-2.5">
            {statusIcon[task.status as keyof typeof statusIcon] ?? statusIcon.queued}
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate">{task.title}</p>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="outline" className={cn("text-[10px]", complexityColor[task.complexity as keyof typeof complexityColor])}>
                  {task.complexity}
                </Badge>
                {task.content_class === "sovereign_only" && (
                  <Badge variant="outline" className="text-[10px] text-purple-400 border-purple-500/30">sovereign</Badge>
                )}
                {task.assigned_to && (
                  <span className="text-[10px] text-muted-foreground">→ {task.assigned_to}</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
