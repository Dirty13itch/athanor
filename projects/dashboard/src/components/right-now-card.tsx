"use client";

import Link from "next/link";
import { StatusDot } from "@/components/status-dot";
import { useSystemStream } from "@/hooks/use-system-stream";
import { formatRelativeTime } from "@/lib/format";
import type { OverviewSnapshot } from "@/lib/contracts";

/** Map agent IDs to their domain accent color for left-border treatment. */
const agentAccentColors: Record<string, string> = {
  "general-assistant": "oklch(0.75 0.08 65)",
  "media-agent": "oklch(0.65 0.12 160)",
  "research-agent": "oklch(0.65 0.12 230)",
  "creative-agent": "oklch(0.7 0.1 330)",
  "knowledge-agent": "oklch(0.54 0.06 90)",
  "home-agent": "oklch(0.65 0.18 145)",
  "coding-agent": "oklch(0.48 0.1 230)",
  "stash-agent": "oklch(0.7 0.1 330)",
  "data-curator": "oklch(0.44 0.02 255)",
};

function getAgentColor(agentId: string): string {
  return agentAccentColors[agentId] ?? "var(--text-muted)";
}

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
    <div className="space-y-1">
      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground/50 mb-2">Right now</p>

      {!hasActivity && recentCompleted.length === 0 && (
        <p className="text-sm text-muted-foreground/40">System idle</p>
      )}

      {/* Active generation */}
      {creativeGpu && (
        <Link
          href="/gallery"
          className="flex items-center gap-3 rounded-lg px-3 py-2.5 transition hover:bg-accent/40 border-l-2"
          style={{ borderLeftColor: agentAccentColors["creative-agent"] }}
        >
          <div className="flex h-6 w-6 items-center justify-center">
            <span className="h-2.5 w-2.5 rounded-full bg-[color:var(--signal-success)] task-pulse-dot" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium">
              {creativeGpu.workload || "Image generation"} on {creativeGpu.name.replace("NVIDIA GeForce ", "")}
            </p>
            <p className="text-xs text-muted-foreground/60">
              {creativeGpu.utilization}% util · {creativeGpu.memUsedGB.toFixed(1)} GB VRAM
            </p>
          </div>
        </Link>
      )}

      {/* Running tasks */}
      {runningTasks.map((task) => (
        <Link
          key={task.id}
          href="/tasks"
          className="flex items-center gap-3 rounded-lg px-3 py-2.5 transition hover:bg-accent/40 border-l-2"
          style={{ borderLeftColor: getAgentColor(task.agentId) }}
        >
          <div className="flex h-6 w-6 items-center justify-center">
            <span className="h-2.5 w-2.5 rounded-full bg-[color:var(--signal-success)] task-pulse-dot" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">
              {task.prompt.slice(0, 80)}{task.prompt.length > 80 ? "..." : ""}
            </p>
            <p className="text-xs text-muted-foreground/60">{task.agentId}</p>
          </div>
        </Link>
      ))}

      {/* Alerts */}
      {alerts.map((alert) => (
        <Link
          key={alert.id}
          href={alert.href}
          className="flex items-center gap-3 rounded-lg px-3 py-2.5 transition hover:bg-accent/40 border-l-2 border-l-[color:var(--signal-danger)]"
        >
          <StatusDot tone="danger" pulse className="mt-0.5" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium">{alert.title}</p>
            <p className="text-xs text-muted-foreground/60">{alert.description}</p>
          </div>
        </Link>
      ))}

      {/* Recent completions (only show if no active items) */}
      {runningTasks.length === 0 && !creativeGpu && recentCompleted.map((task) => (
        <div
          key={task.id}
          className="flex items-center gap-3 rounded-lg px-3 py-2 opacity-40"
        >
          <StatusDot tone="healthy" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm">
              {task.prompt.slice(0, 60)}{task.prompt.length > 60 ? "..." : ""}
            </p>
            <p className="text-xs text-muted-foreground/60">{task.agentId}</p>
          </div>
          <span className="text-xs text-muted-foreground/40" data-volatile="true">
            {task.completedAt ? formatRelativeTime(task.completedAt) : ""}
          </span>
        </div>
      ))}
    </div>
  );
}
