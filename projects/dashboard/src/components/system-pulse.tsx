"use client";

import { useSystemStream } from "@/hooks/use-system-stream";
import { useLens } from "@/hooks/use-lens";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

export function SystemPulse({ sticky = false }: { sticky?: boolean }) {
  const { data, connected } = useSystemStream();
  const { config: lensConfig } = useLens();

  if (!data) {
    return (
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <div className="h-2 w-2 animate-pulse rounded-full bg-primary" />
            Connecting to system stream...
          </div>
        </CardContent>
      </Card>
    );
  }

  const totalVramUsed = data.gpus.reduce((s, g) => s + g.memUsedGB, 0);
  const totalVramTotal = data.gpus.reduce((s, g) => s + g.memTotalGB, 0);
  const totalPower = data.gpus.reduce((s, g) => s + g.power, 0);
  const avgUtil = data.gpus.length > 0
    ? data.gpus.reduce((s, g) => s + g.utilization, 0) / data.gpus.length
    : 0;

  const intensity = Math.min(1, avgUtil / 80);
  const glowHue = lensConfig.accentHue || 65;
  const taskSignals: string[] = [];
  if (data.tasks) {
    if (data.tasks.currently_running > 0) {
      taskSignals.push(`${data.tasks.currently_running} running`);
    }
    if (data.tasks.pending > 0) {
      taskSignals.push(`${data.tasks.pending} queued`);
    }
    if (data.tasks.pending_approval > 0) {
      taskSignals.push(`${data.tasks.pending_approval} approval-held`);
    }
    if (data.tasks.stale_lease > 0) {
      taskSignals.push(`${data.tasks.stale_lease} stale`);
    }
    if (data.tasks.failed_actionable > 0) {
      taskSignals.push(`${data.tasks.failed_actionable} actionable`);
    }
  }

  return (
    <Card
      className={`transition-shadow duration-1000 ${sticky ? "sticky top-0 z-30" : ""}`}
      style={{
        boxShadow: intensity > 0.1
          ? `0 0 ${Math.round(intensity * 20)}px oklch(0.77 ${(0.02 + intensity * 0.04).toFixed(3)} ${glowHue} / ${(intensity * 0.22).toFixed(2)})`
          : undefined,
      }}
    >
      <CardContent className="py-2.5 sm:py-4">
        <div className="flex items-center gap-2.5 flex-wrap sm:gap-4 md:gap-6">
          {/* GPU utilization bars */}
          <div className="flex items-center gap-1">
            {data.gpus.map((g, i) => (
              <div key={i} className="flex flex-col items-center" title={`${g.name} (${g.node}) — ${g.workload}`}>
                <div className="w-2.5 h-6 rounded-sm bg-muted overflow-hidden flex flex-col-reverse sm:w-3 sm:h-8">
                  <div
                    className={`w-full rounded-sm transition-all duration-700 ${
                      g.utilization > 80
                        ? "bg-[color:var(--signal-danger)]"
                        : g.utilization > 50
                          ? "bg-[color:var(--signal-warning)]"
                          : g.utilization > 5
                            ? "bg-[color:var(--signal-success)]"
                            : "bg-[color:var(--signal-success)] opacity-40"
                    }`}
                    style={{ height: `${Math.max(4, g.utilization)}%` }}
                  />
                </div>
              </div>
            ))}
            <span className="text-[10px] text-muted-foreground ml-1 sm:text-xs">{data.gpus.length} GPUs</span>
          </div>

          {/* VRAM — hidden on smallest screens, show on sm+ */}
          <div className="hidden text-xs sm:block">
            <span className="text-muted-foreground">VRAM</span>{" "}
            <span className="font-mono font-medium">
              {totalVramUsed.toFixed(0)}/{totalVramTotal.toFixed(0)} GB
            </span>
          </div>

          {/* Power — hidden on smallest screens, show on sm+ */}
          <div className="hidden text-xs sm:block">
            <span className="text-muted-foreground">Power</span>{" "}
            <span className="font-mono font-medium">{totalPower.toFixed(0)}W</span>
          </div>

          {/* Services */}
          <div className="text-[10px] sm:text-xs">
            <span className="text-muted-foreground">Svc</span>{" "}
            <span className="font-mono font-medium">
              {data.services.up}/{data.services.total}
            </span>
            {data.services.down.length > 0 && (
              <span className="ml-0.5 text-destructive sm:ml-1" title={data.services.down.join(", ")}>
                ({data.services.down.length}<span className="hidden sm:inline"> down</span>)
              </span>
            )}
          </div>

          {/* Agents — compact on mobile */}
          {data.agents.online && (
            <div className="text-[10px] sm:text-xs">
              <span className="hidden text-muted-foreground sm:inline">Agents </span>
              <Badge variant="default" className="text-[10px] py-0 px-1 sm:text-xs sm:px-1.5">
                {data.agents.count}<span className="hidden sm:inline"> online</span>
              </Badge>
            </div>
          )}

          {/* Tasks — hidden on mobile if nothing running */}
          {taskSignals.length > 0 && (
            <div className="hidden text-xs sm:block">
              <span className="text-muted-foreground">Tasks</span>{" "}
              <span className="font-mono font-medium">{taskSignals.join(", ")}</span>
            </div>
          )}

          {/* Media streams — hidden on mobile */}
          {data.media && data.media.streamCount > 0 && (
            <div className="hidden text-xs sm:block">
              <span className="text-muted-foreground">Playing</span>{" "}
              <Badge variant="default" className="text-xs py-0 px-1.5">
                {data.media.streamCount} stream{data.media.streamCount !== 1 ? "s" : ""}
              </Badge>
            </div>
          )}

          {/* Downloads — hidden on mobile */}
          {data.media && data.media.downloadCount > 0 && (
            <div className="hidden text-xs sm:block">
              <span className="text-muted-foreground">Downloads</span>{" "}
              <Badge variant="outline" className="text-xs py-0 px-1.5 text-[color:var(--signal-warning)]">
                {data.media.downloadCount}
              </Badge>
            </div>
          )}

          {/* Connection indicator */}
          <div className="ml-auto flex items-center gap-1 text-[10px] text-muted-foreground sm:gap-1.5 sm:text-xs">
            <div className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-[color:var(--signal-success)]" : "bg-[color:var(--signal-danger)] animate-pulse"}`} />
            <span className="hidden sm:inline">
              {connected ? "Live" : "Reconnecting..."}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
