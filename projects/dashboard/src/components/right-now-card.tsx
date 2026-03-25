"use client";

import Link from "next/link";
import { Activity, Loader2, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusDot } from "@/components/status-dot";
import { useSystemStream } from "@/hooks/use-system-stream";
import { formatRelativeTime } from "@/lib/format";
import type { OverviewSnapshot } from "@/lib/contracts";

export function RightNowCard({ snapshot }: { snapshot: OverviewSnapshot }) {
  const { data: stream } = useSystemStream();

  const runningTasks = snapshot.workforce.tasks
    .filter((t) => t.status === "running")
    .slice(0, 3);
  const recentCompleted = snapshot.workforce.tasks
    .filter((t) => t.status === "completed")
    .slice(0, 2);
  const alerts = snapshot.alerts.filter((a) => a.tone === "degraded");

  const activeGpus = stream?.gpus.filter((g) => g.utilization > 10) ?? [];
  const creativeGpu = activeGpus.find((g) => {
    const w = g.workload?.toLowerCase() ?? "";
    return w.includes("comfyui") || w.includes("flux") || w.includes("ltx") || w.includes("wan") || w.includes("pulid");
  });

  const hasActivity = runningTasks.length > 0 || creativeGpu || alerts.length > 0;

  return (
    <Card className="surface-hero border">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Zap className="h-5 w-5 text-primary" />
          Right now
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {!hasActivity && recentCompleted.length === 0 && (
          <p className="text-sm text-muted-foreground">System idle. No active tasks or generations.</p>
        )}

        {/* Active generation */}
        {creativeGpu && (
          <Link
            href="/gallery"
            className="flex items-center gap-3 rounded-xl px-3 py-2.5 transition hover:bg-accent/40"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[oklch(0.7_0.1_330/0.15)]">
              <Loader2 className="h-4 w-4 animate-spin text-[oklch(0.7_0.1_330)]" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">
                {creativeGpu.workload || "Image generation"} on {creativeGpu.name.replace("NVIDIA GeForce ", "")}
              </p>
              <p className="text-xs text-muted-foreground">
                {creativeGpu.utilization}% util · {creativeGpu.memUsedGB.toFixed(1)} GB VRAM
              </p>
            </div>
            <Badge variant="outline" className="text-xs">generating</Badge>
          </Link>
        )}

        {/* Running tasks */}
        {runningTasks.map((task) => (
          <Link
            key={task.id}
            href="/tasks"
            className="flex items-center gap-3 rounded-xl px-3 py-2.5 transition hover:bg-accent/40"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <Activity className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">
                {task.prompt.slice(0, 80)}{task.prompt.length > 80 ? "..." : ""}
              </p>
              <p className="text-xs text-muted-foreground">{task.agentId}</p>
            </div>
            <Badge variant="outline" className="text-xs">running</Badge>
          </Link>
        ))}

        {/* Alerts */}
        {alerts.map((alert) => (
          <Link
            key={alert.id}
            href={alert.href}
            className="flex items-center gap-3 rounded-xl px-3 py-2.5 transition hover:bg-accent/40"
          >
            <StatusDot tone="danger" pulse className="mt-0.5" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{alert.title}</p>
              <p className="text-xs text-muted-foreground">{alert.description}</p>
            </div>
          </Link>
        ))}

        {/* Recent completions (only show if no active items) */}
        {runningTasks.length === 0 && !creativeGpu && recentCompleted.map((task) => (
          <div
            key={task.id}
            className="flex items-center gap-3 rounded-xl px-3 py-2 opacity-60"
          >
            <StatusDot tone="healthy" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm">
                {task.prompt.slice(0, 60)}{task.prompt.length > 60 ? "..." : ""}
              </p>
              <p className="text-xs text-muted-foreground">{task.agentId}</p>
            </div>
            <span className="text-xs text-muted-foreground" data-volatile="true">
              {task.completedAt ? formatRelativeTime(task.completedAt) : ""}
            </span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
