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
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Server className="h-5 w-5 text-primary" />
          Cluster
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-2 sm:grid-cols-2">
          {nodes.map((node) => (
            <Link
              key={node.id}
              href={`/monitoring?node=${node.id}`}
              className="flex items-center gap-3 rounded-xl border px-3 py-2.5 surface-instrument transition hover:bg-accent/40"
            >
              <StatusDot
                tone={node.degradedServices > 0 ? "warning" : "healthy"}
                pulse={node.degradedServices > 0}
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold">{node.name}</p>
                  <span className="font-mono text-xs text-muted-foreground">{node.ip}</span>
                </div>
                <div className="mt-0.5 flex items-center gap-3 text-xs text-muted-foreground">
                  <span>{node.healthyServices}/{node.totalServices} svcs</span>
                  <span>{formatLatency(node.averageLatencyMs)}</span>
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
