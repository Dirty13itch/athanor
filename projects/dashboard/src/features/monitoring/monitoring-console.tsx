"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, RefreshCcw } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { LiveBadge } from "@/components/live-badge";
import { PageHeader } from "@/components/page-header";
import { ProgressBar } from "@/components/progress-bar";
import { Sparkline } from "@/components/sparkline";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { StatCard } from "@/components/stat-card";
import { getMonitoring } from "@/lib/api";
import { type MonitoringSnapshot } from "@/lib/contracts";
import { formatRelativeTime } from "@/lib/format";
import { LIVE_REFRESH_INTERVALS, liveQueryOptions } from "@/lib/live-updates";
import { queryKeys } from "@/lib/query-client";
import { useUrlState } from "@/lib/url-state";

function formatBytes(bytes: number | null) {
  if (bytes === null) {
    return "--";
  }
  if (bytes < 1024) {
    return `${bytes.toFixed(0)} B`;
  }
  if (bytes < 1024 ** 2) {
    return `${(bytes / 1024).toFixed(1)} KiB`;
  }
  if (bytes < 1024 ** 3) {
    return `${(bytes / 1024 ** 2).toFixed(1)} MiB`;
  }
  return `${(bytes / 1024 ** 3).toFixed(1)} GiB`;
}

function formatRate(bytes: number | null) {
  if (bytes === null) {
    return "--";
  }
  return `${formatBytes(bytes)}/s`;
}

function formatUptime(seconds: number | null) {
  if (seconds === null) {
    return "--";
  }
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  return days > 0 ? `${days}d ${hours}h` : `${hours}h`;
}

export function MonitoringConsole({ initialSnapshot }: { initialSnapshot: MonitoringSnapshot }) {
  const { getSearchValue, setSearchValue } = useUrlState();
  const node = getSearchValue("node", "all");
  const panel = getSearchValue("panel", "");

  const monitoringQuery = useQuery({
    queryKey: queryKeys.monitoring,
    queryFn: getMonitoring,
    initialData: initialSnapshot,
    ...liveQueryOptions(LIVE_REFRESH_INTERVALS.telemetry),
  });

  if (monitoringQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Domain Console" title="Monitoring" description="The monitoring snapshot failed to load." />
        <ErrorPanel
          description={
            monitoringQuery.error instanceof Error
              ? monitoringQuery.error.message
              : "Failed to load monitoring snapshot."
          }
        />
      </div>
    );
  }

  const snapshot = monitoringQuery.data ?? initialSnapshot;
  const visibleNodes = snapshot.nodes.filter((entry) => node === "all" || entry.id === node);
  const activeDashboard = snapshot.dashboards.find((entry) => entry.id === panel) ?? null;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Domain Console"
        title="Monitoring"
        description="Deep cluster monitoring with typed dashboard-owned data and Grafana-linked drawer previews."
        actions={
          <>
            <LiveBadge updatedAt={snapshot.generatedAt} intervalMs={LIVE_REFRESH_INTERVALS.telemetry} />
            <Button variant="outline" onClick={() => void monitoringQuery.refetch()} disabled={monitoringQuery.isFetching}>
              <RefreshCcw className={`mr-2 h-4 w-4 ${monitoringQuery.isFetching ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Reachable nodes" value={`${snapshot.summary.reachableNodes}/${snapshot.summary.totalNodes}`} detail="Nodes with live Prometheus samples." />
          <StatCard label="Average CPU" value={`${snapshot.summary.averageCpu?.toFixed(1) ?? "--"}%`} detail={`Updated ${formatRelativeTime(snapshot.generatedAt)}`} detailVolatile />
          <StatCard label="Fleet memory" value={`${formatBytes(snapshot.summary.totalMemUsed)} / ${formatBytes(snapshot.summary.totalMemTotal)}`} detail="Live aggregate memory footprint." />
          <StatCard label="Network" value={`${formatRate(snapshot.summary.networkRxRate)} in`} detail={`${formatRate(snapshot.summary.networkTxRate)} out`} />
        </div>
      </PageHeader>

      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Grafana drill-downs</CardTitle>
          <CardDescription>Use drawer previews for focused context, then jump to Grafana for full workflows.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button size="sm" variant={node === "all" ? "default" : "outline"} onClick={() => setSearchValue("node", null)}>
            All nodes
          </Button>
          {snapshot.nodes.map((entry) => (
            <Button
              key={entry.id}
              size="sm"
              variant={node === entry.id ? "default" : "outline"}
              onClick={() => setSearchValue("node", entry.id)}
            >
              {entry.name}
            </Button>
          ))}
          {snapshot.dashboards.map((entry) => (
            <Button key={entry.id} size="sm" variant="outline" onClick={() => setSearchValue("panel", entry.id)}>
              {entry.label}
            </Button>
          ))}
        </CardContent>
      </Card>

      {visibleNodes.length > 0 ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {visibleNodes.map((entry) => {
            const memRatio =
              entry.memUsed !== null && entry.memTotal ? (entry.memUsed / entry.memTotal) * 100 : 0;
            const diskRatio =
              entry.diskUsed !== null && entry.diskTotal ? (entry.diskUsed / entry.diskTotal) * 100 : 0;
            return (
              <Card key={entry.id} className="surface-panel">
                <CardHeader>
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <CardTitle className="text-lg">{entry.name}</CardTitle>
                      <CardDescription>{entry.role}</CardDescription>
                    </div>
                    <Badge
                      variant="outline"
                      className="status-badge"
                      data-tone={entry.cpuUsage !== null ? "success" : "danger"}
                    >
                      {entry.cpuUsage !== null ? "Reachable" : "Unreachable"}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <MetricRow label="CPU" value={`${entry.cpuUsage?.toFixed(1) ?? "--"}%`} />
                  <ProgressBar value={entry.cpuUsage ?? 0} />
                  <Sparkline data={entry.cpuHistory} width={420} height={28} fill className="w-full" color="var(--chart-cat-1)" />

                  <MetricRow label="Memory" value={`${formatBytes(entry.memUsed)} / ${formatBytes(entry.memTotal)}`} />
                  <ProgressBar value={memRatio} />
                  <Sparkline data={entry.memHistory} width={420} height={28} fill className="w-full" color="var(--chart-cat-2)" />

                  <MetricRow label="Disk" value={`${formatBytes(entry.diskUsed)} / ${formatBytes(entry.diskTotal)}`} />
                  <ProgressBar value={diskRatio} />

                  <div className="grid gap-3 md:grid-cols-2">
                    <MetricRow label="Uptime" value={formatUptime(entry.uptime)} />
                    <MetricRow label="Load" value={entry.load1?.toFixed(2) ?? "--"} />
                    <MetricRow label="Rx" value={formatRate(entry.networkRxRate)} />
                    <MetricRow label="Tx" value={formatRate(entry.networkTxRate)} />
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <EmptyState title="No nodes match the current filter" description="Clear the node filter to restore the full monitoring view." />
      )}

      <Sheet open={Boolean(activeDashboard)} onOpenChange={(open) => setSearchValue("panel", open ? panel : null)}>
        <SheetContent side="right" className="w-full max-w-xl overflow-y-auto border-l border-border/80 bg-background/95">
          {activeDashboard ? (
            <>
              <SheetHeader className="border-b border-border/80 px-6 py-5 text-left">
                <SheetTitle>{activeDashboard.label}</SheetTitle>
                <SheetDescription>{activeDashboard.description}</SheetDescription>
              </SheetHeader>
              <div className="space-y-6 p-6">
                <Card className="surface-instrument">
                  <CardHeader>
                    <CardTitle className="text-lg">Drawer preview</CardTitle>
                    <CardDescription>This drawer preserves route state and keeps the operator in the command center.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm text-muted-foreground">
                      Use this preview state for context, then jump out to Grafana for full panel interaction and exploration.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <Button asChild>
                        <a href={activeDashboard.url} target="_blank" rel="noopener noreferrer">
                          <ArrowUpRight className="mr-2 h-4 w-4" />
                          Open in Grafana
                        </a>
                      </Button>
                      <Button asChild variant="outline">
                        <Link href={node === "all" ? "/services" : `/services?node=${node}`}>Open services</Link>
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
