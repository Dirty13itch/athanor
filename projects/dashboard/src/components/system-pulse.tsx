"use client";

import { useSystemStream } from "@/hooks/use-system-stream";
import { useLens } from "@/hooks/use-lens";
import { Badge } from "@/components/ui/badge";

/** Group GPUs by node for labeling. */
function groupByNode(gpus: Array<{ node: string; name: string; utilization: number; memUsedGB: number; memTotalGB: number; power: number; workload: string }>) {
  const map = new Map<string, typeof gpus>();
  for (const g of gpus) {
    const arr = map.get(g.node) ?? [];
    arr.push(g);
    map.set(g.node, arr);
  }
  return Array.from(map.entries());
}

export function SystemPulse({ sticky = false }: { sticky?: boolean }) {
  const { data, connected } = useSystemStream();
  const { config: lensConfig } = useLens();

  if (!data) {
    return (
      <div className="surface-instrument rounded-xl px-4 py-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <div className="h-2 w-2 animate-pulse rounded-full bg-primary" />
          Connecting to system stream...
        </div>
      </div>
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
  const nodeGroups = groupByNode(data.gpus);

  return (
    <div
      className={`surface-instrument rounded-xl px-4 py-3 transition-all duration-1000 ${sticky ? "sticky top-0 z-30" : ""}`}
      style={{
        boxShadow: intensity > 0.1
          ? `0 0 ${Math.round(intensity * 28)}px oklch(0.77 ${(0.02 + intensity * 0.06).toFixed(3)} ${glowHue} / ${(intensity * 0.25).toFixed(2)}), inset 0 1px 0 rgb(255 255 255 / 0.03)`
          : "inset 0 1px 0 rgb(255 255 255 / 0.03)",
        // Drive the CSS variable for downstream ambient effects
        ["--system-intensity" as string]: intensity.toFixed(2),
      }}
    >
      <div className="flex items-center gap-4 flex-wrap md:gap-6">
        {/* GPU utilization bars grouped by node */}
        <div className="flex items-end gap-3">
          {nodeGroups.map(([node, gpus]) => (
            <div key={node} className="flex flex-col items-center gap-0.5">
              <div className="flex items-end gap-1">
                {gpus.map((g, i) => (
                  <div key={i} className="flex flex-col items-center" title={`${g.name} (${node}) — ${g.workload || "idle"}`}>
                    <div className="w-3 h-8 rounded-sm bg-muted/40 overflow-hidden flex flex-col-reverse">
                      <div
                        className="w-full rounded-sm transition-all duration-700"
                        style={{
                          height: `${Math.max(4, g.utilization)}%`,
                          background:
                            g.utilization > 80
                              ? "linear-gradient(to top, var(--signal-danger), color-mix(in srgb, var(--signal-danger) 70%, var(--signal-warning)))"
                              : g.utilization > 50
                                ? "linear-gradient(to top, var(--signal-warning), color-mix(in srgb, var(--signal-warning) 70%, var(--signal-success)))"
                                : g.utilization > 5
                                  ? "linear-gradient(to top, var(--signal-success), color-mix(in srgb, var(--signal-success) 70%, white))"
                                  : "var(--signal-success)",
                          opacity: g.utilization > 5 ? 1 : 0.35,
                        }}
                      />
                    </div>
                    {g.workload && (
                      <span className="mt-0.5 text-[8px] text-muted-foreground/60 max-w-[28px] truncate leading-none">
                        {g.workload.split(/[\s/]/)[0]}
                      </span>
                    )}
                  </div>
                ))}
              </div>
              <span className="text-[9px] text-muted-foreground/50 uppercase tracking-wider leading-none mt-0.5">
                {node.replace(/^node/i, "").trim() || node}
              </span>
            </div>
          ))}
          <span className="text-[10px] text-muted-foreground/60 ml-0.5 self-center">{data.gpus.length} GPUs</span>
        </div>

        {/* VRAM */}
        <div className="text-xs">
          <span className="text-muted-foreground/60 text-[10px] uppercase tracking-wider">VRAM</span>{" "}
          <span className="font-mono font-medium tabular-nums">
            {totalVramUsed.toFixed(0)}/{totalVramTotal.toFixed(0)} GB
          </span>
        </div>

        {/* Power */}
        <div className="text-xs">
          <span className="text-muted-foreground/60 text-[10px] uppercase tracking-wider">Power</span>{" "}
          <span className="font-mono font-medium tabular-nums">{totalPower.toFixed(0)}W</span>
        </div>

        {/* Services */}
        <div className="text-xs">
          <span className="text-muted-foreground/60 text-[10px] uppercase tracking-wider">Svcs</span>{" "}
          <span className="font-mono font-medium tabular-nums">
            {data.services.up}/{data.services.total}
          </span>
          {data.services.down.length > 0 && (
            <span className="ml-1 text-[color:var(--signal-danger)]" title={data.services.down.join(", ")}>
              ({data.services.down.length} down)
            </span>
          )}
        </div>

        {/* Agents */}
        {data.agents.online && (
          <div className="text-xs">
            <span className="text-muted-foreground/60 text-[10px] uppercase tracking-wider">Agents</span>{" "}
            <span className="font-mono font-medium tabular-nums">{data.agents.count}</span>
          </div>
        )}

        {/* Tasks */}
        {data.tasks && (data.tasks.currently_running > 0 || data.tasks.by_status.pending > 0) && (
          <div className="text-xs">
            <span className="text-muted-foreground/60 text-[10px] uppercase tracking-wider">Tasks</span>{" "}
            <span className="font-mono font-medium tabular-nums">
              {data.tasks.currently_running} running
              {data.tasks.by_status.pending > 0 && `, ${data.tasks.by_status.pending} queued`}
            </span>
          </div>
        )}

        {/* Media streams */}
        {data.media && data.media.streamCount > 0 && (
          <div className="text-xs">
            <span className="text-muted-foreground/60 text-[10px] uppercase tracking-wider">Playing</span>{" "}
            <Badge variant="default" className="text-xs py-0 px-1.5">
              {data.media.streamCount} stream{data.media.streamCount !== 1 ? "s" : ""}
            </Badge>
          </div>
        )}

        {/* Downloads */}
        {data.media && data.media.downloadCount > 0 && (
          <div className="text-xs">
            <span className="text-muted-foreground/60 text-[10px] uppercase tracking-wider">DL</span>{" "}
            <Badge variant="outline" className="text-xs py-0 px-1.5 text-[color:var(--signal-warning)]">
              {data.media.downloadCount}
            </Badge>
          </div>
        )}

        {/* Connection indicator — animated line */}
        <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground/60">
          <div className="relative h-[2px] w-8 rounded-full bg-muted/30 overflow-hidden">
            <div
              className={`absolute inset-0 rounded-full ${
                connected
                  ? "bg-[color:var(--signal-success)] connection-line"
                  : "bg-[color:var(--signal-danger)] animate-pulse"
              }`}
            />
          </div>
          <span className="hidden sm:inline text-[10px]">
            {connected ? "Live" : "Reconnecting..."}
          </span>
        </div>
      </div>
    </div>
  );
}
