"use client";

import { useSystemStream } from "@/hooks/use-system-stream";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

export function SystemPulse() {
  const { data, connected } = useSystemStream();

  if (!data) {
    return (
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <div className="h-2 w-2 animate-pulse rounded-full bg-amber" />
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

  // Compute system warmth (0 = cold/idle, 1 = hot/loaded)
  const warmth = Math.min(1, avgUtil / 80);

  return (
    <Card
      className="transition-shadow duration-1000"
      style={{
        boxShadow: warmth > 0.1
          ? `0 0 ${Math.round(warmth * 20)}px oklch(0.75 ${(0.02 + warmth * 0.06).toFixed(3)} 65 / ${(warmth * 0.3).toFixed(2)})`
          : undefined,
      }}
    >
      <CardContent className="py-4">
        <div className="flex items-center gap-4 flex-wrap md:gap-6">
          {/* GPU utilization bars */}
          <div className="flex items-center gap-1.5">
            {data.gpus.map((g, i) => (
              <div key={i} className="flex flex-col items-center" title={`${g.name} (${g.node}) — ${g.workload}`}>
                <div className="w-3 h-8 rounded-sm bg-muted overflow-hidden flex flex-col-reverse">
                  <div
                    className={`w-full rounded-sm transition-all duration-700 ${
                      g.utilization > 80 ? "bg-red-500" : g.utilization > 50 ? "bg-yellow-500" : g.utilization > 5 ? "bg-green-500" : "bg-green-500/40"
                    }`}
                    style={{ height: `${Math.max(4, g.utilization)}%` }}
                  />
                </div>
              </div>
            ))}
            <span className="text-xs text-muted-foreground ml-1">{data.gpus.length} GPUs</span>
          </div>

          {/* VRAM */}
          <div className="text-xs">
            <span className="text-muted-foreground">VRAM</span>{" "}
            <span className="font-mono font-medium">
              {totalVramUsed.toFixed(0)}/{totalVramTotal.toFixed(0)} GB
            </span>
          </div>

          {/* Power */}
          <div className="text-xs">
            <span className="text-muted-foreground">Power</span>{" "}
            <span className="font-mono font-medium">{totalPower.toFixed(0)}W</span>
          </div>

          {/* Services */}
          <div className="text-xs">
            <span className="text-muted-foreground">Services</span>{" "}
            <span className="font-mono font-medium">
              {data.services.up}/{data.services.total}
            </span>
            {data.services.down.length > 0 && (
              <span className="ml-1 text-destructive" title={data.services.down.join(", ")}>
                ({data.services.down.length} down)
              </span>
            )}
          </div>

          {/* Agents */}
          {data.agents.online && (
            <div className="text-xs">
              <span className="text-muted-foreground">Agents</span>{" "}
              <Badge variant="default" className="text-xs py-0 px-1.5">
                {data.agents.count} online
              </Badge>
            </div>
          )}

          {/* Tasks */}
          {data.tasks && (data.tasks.currently_running > 0 || data.tasks.by_status.pending > 0) && (
            <div className="text-xs">
              <span className="text-muted-foreground">Tasks</span>{" "}
              <span className="font-mono font-medium">
                {data.tasks.currently_running} running
                {data.tasks.by_status.pending > 0 && `, ${data.tasks.by_status.pending} queued`}
              </span>
            </div>
          )}

          {/* Connection indicator */}
          <div className="ml-auto flex items-center gap-1.5 text-xs text-muted-foreground">
            <div className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-green-500" : "bg-red-500 animate-pulse"}`} />
            <span className="hidden sm:inline">
              {connected ? "Live" : "Reconnecting..."}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
