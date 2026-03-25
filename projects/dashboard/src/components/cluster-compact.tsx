"use client";

import Link from "next/link";
import { StatusDot } from "@/components/status-dot";
import { formatPercent } from "@/lib/format";
import type { OverviewSnapshot } from "@/lib/contracts";

export function ClusterCompact({ nodes }: { nodes: OverviewSnapshot["nodes"] }) {
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground/50">Cluster</p>
      {nodes.map((node) => {
        const gpuPct = node.gpuUtilization ?? 0;
        return (
          <Link
            key={node.id}
            href={`/monitoring?node=${node.id}`}
            className="flex items-center gap-2.5 rounded-md px-2 py-1 transition hover:bg-accent/40"
          >
            <StatusDot
              tone={node.degradedServices > 0 ? "warning" : "healthy"}
              pulse={node.degradedServices > 0}
            />
            <span className="text-xs font-medium w-20 truncate">{node.name}</span>
            <span className="font-mono text-[10px] text-muted-foreground/50 w-12">{node.ip}</span>
            <span className="text-[10px] text-muted-foreground/50 w-14">{node.healthyServices}/{node.totalServices} svc</span>
            {/* Thin inline GPU bar */}
            <div className="flex-1 h-1 rounded-full bg-muted/30 overflow-hidden min-w-[40px] max-w-[80px]">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{
                  width: `${Math.min(gpuPct, 100)}%`,
                  backgroundColor:
                    gpuPct >= 80
                      ? "var(--signal-warning)"
                      : gpuPct >= 1
                        ? "var(--signal-success)"
                        : "var(--text-disabled)",
                }}
              />
            </div>
            <span className="font-mono text-[10px] text-muted-foreground/50 w-8 text-right tabular-nums">
              {formatPercent(node.gpuUtilization, 0)}
            </span>
          </Link>
        );
      })}
    </div>
  );
}
