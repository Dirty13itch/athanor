"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusDot } from "@/components/status-dot";
import { Server } from "lucide-react";
import { formatPercent, formatLatency } from "@/lib/format";
import type { OverviewSnapshot } from "@/lib/contracts";

export function ClusterCompact({ nodes }: { nodes: OverviewSnapshot["nodes"] }) {
  return (
    <Card className="surface-panel border">
      <CardHeader className="px-4 pb-2 pt-4 sm:px-6 sm:pb-3 sm:pt-6">
        <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
          <Server className="h-4 w-4 text-primary sm:h-5 sm:w-5" />
          Cluster
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 sm:px-6">
        <div className="grid gap-2 sm:grid-cols-2">
          {nodes.map((node) => (
            <Link
              key={node.id}
              href={`/monitoring?node=${node.id}`}
              className="flex items-center gap-2.5 rounded-xl border px-2.5 py-2 surface-instrument transition hover:bg-accent/40 min-h-[44px] sm:gap-3 sm:px-3 sm:py-2.5"
            >
              <StatusDot
                tone={node.degradedServices > 0 ? "warning" : "healthy"}
                pulse={node.degradedServices > 0}
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold sm:text-sm">{node.name}</p>
                  <span className="font-mono text-[10px] text-muted-foreground sm:text-xs">{node.ip}</span>
                </div>
                <div className="mt-0.5 flex items-center gap-2 text-[11px] text-muted-foreground sm:gap-3 sm:text-xs">
                  <span>{node.healthyServices}/{node.totalServices} svcs</span>
                  <span className="hidden sm:inline">{formatLatency(node.averageLatencyMs)}</span>
                  {node.gpuUtilization != null && (
                    <span>GPU {formatPercent(node.gpuUtilization, 0)}</span>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
