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
      <CardHeader className="px-4 pb-2 pt-4 sm:px-6 sm:pb-3 sm:pt-6">
        <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
          <Zap className="h-4 w-4 text-primary sm:h-5 sm:w-5" />
          Right now
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1.5 px-4 sm:space-y-2 sm:px-6">
        {!hasActivity && recentCompleted.length === 0 && (
          <p className="text-sm text-muted-foreground">System idle. No active tasks or generations.</p>
        )}

        {/* Active generation */}
        {creativeGpu && (
          <Link
            href="/gallery"
            className="flex items-center gap-2.5 rounded-xl px-2.5 py-2 transition hover:bg-accent/40 min-h-[44px] sm:gap-3 sm:px-3 sm:py-2.5"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[oklch(0.7_0.1_330/0.15)] sm:h-8 sm:w-8">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-[oklch(0.7_0.1_330)] sm:h-4 sm:w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium sm:text-sm">
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
            href="/runs"
            className="flex items-center gap-2.5 rounded-xl px-2.5 py-2 transition hover:bg-accent/40 min-h-[44px] sm:gap-3 sm:px-3 sm:py-2.5"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 sm:h-8 sm:w-8">
              <Activity className="h-3.5 w-3.5 text-primary sm:h-4 sm:w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium sm:text-sm">
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
            className="flex items-center gap-2.5 rounded-xl px-2.5 py-2 transition hover:bg-accent/40 min-h-[44px] sm:gap-3 sm:px-3 sm:py-2.5"
          >
            <StatusDot tone="danger" pulse className="mt-0.5" />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium sm:text-sm">{alert.title}</p>
              <p className="text-[11px] text-muted-foreground sm:text-xs">{alert.description}</p>
            </div>
          </Link>
        ))}

        {/* Recent completions (only show if no active items) */}
        {runningTasks.length === 0 && !creativeGpu && recentCompleted.map((task) => (
          <div
            key={task.id}
            className="flex items-center gap-2.5 rounded-xl px-2.5 py-1.5 opacity-60 sm:gap-3 sm:px-3 sm:py-2"
          >
            <StatusDot tone="healthy" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs sm:text-sm">
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
