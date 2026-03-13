"use client";

import { Badge } from "@/components/ui/badge";
import type { TaskStatusParsed } from "@/lib/generative-ui";

const statusColors: Record<string, string> = {
  completed: "bg-green-500/20 text-green-400",
  running: "bg-primary/20 text-primary",
  failed: "bg-red-500/20 text-red-400",
  pending: "bg-muted text-muted-foreground",
  queued: "bg-muted text-muted-foreground",
  submitted: "bg-blue-500/20 text-blue-400",
};

export function TaskCard({ task }: { task: TaskStatusParsed }) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-border bg-card p-2">
      <Badge
        variant="outline"
        className={`shrink-0 text-[10px] ${statusColors[task.status] ?? ""}`}
      >
        {task.status}
      </Badge>
      <div className="min-w-0 flex-1">
        {task.agent && (
          <span className="text-xs font-medium text-primary">{task.agent}</span>
        )}
        {task.id && (
          <span className="ml-1 font-mono text-[10px] text-muted-foreground">
            {task.id.substring(0, 8)}
          </span>
        )}
        {task.description && (
          <p className="mt-0.5 text-xs text-muted-foreground truncate">{task.description}</p>
        )}
      </div>
      <a
        href="/tasks"
        className="shrink-0 text-[10px] text-primary hover:underline"
      >
        View
      </a>
    </div>
  );
}
