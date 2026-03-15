"use client";

import { useDeferredValue, useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Copy, Download, ExternalLink, FileText, Power, RefreshCcw, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { LiveBadge } from "@/components/live-badge";
import { MetricChart } from "@/components/metric-chart";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { StatusDot } from "@/components/status-dot";
import { getServices, getServicesHistory, getContainers, restartContainer, getContainerLogs, type ContainerInfo } from "@/lib/api";
import { type ServicesHistorySnapshot, type ServicesSnapshot } from "@/lib/contracts";
import { config } from "@/lib/config";
import { compactText, formatCategoryLabel, formatLatency, formatRelativeTime } from "@/lib/format";
import { LIVE_REFRESH_INTERVALS, liveQueryOptions } from "@/lib/live-updates";
import { queryKeys } from "@/lib/query-client";
import { getTimeWindow, isTimeWindow, TIME_WINDOWS } from "@/lib/ranges";
import { useUrlState } from "@/lib/url-state";

type StatusFilter = "all" | "healthy" | "degraded";
type SortMode = "severity" | "latency" | "name";

// Map service IDs to their known Docker container names and nodes
const SERVICE_CONTAINER_MAP: Record<string, { container: string; node: string }> = {
  "workshop-worker": { container: "vllm-node2", node: "workshop" },
  "comfyui": { container: "comfyui", node: "workshop" },
  "workshop-open-webui": { container: "open-webui", node: "workshop" },
  "eoq": { container: "athanor-eoq", node: "workshop" },
  "workshop-node-exporter": { container: "node-exporter", node: "workshop" },
  "workshop-dcgm-exporter": { container: "dcgm-exporter", node: "workshop" },
  "coordinator": { container: "vllm-coordinator", node: "foundry" },
  "coder": { container: "vllm-coder", node: "foundry" },
  "agent-server": { container: "athanor-agents", node: "foundry" },
  "foundry-qdrant": { container: "qdrant", node: "foundry" },
  "foundry-node-exporter": { container: "node-exporter", node: "foundry" },
  "foundry-dcgm-exporter": { container: "dcgm-exporter", node: "foundry" },
  "litellm": { container: "litellm", node: "vault" },
  "langfuse": { container: "langfuse-web", node: "vault" },
  "vault-neo4j": { container: "neo4j", node: "vault" },
  "vault-redis": { container: "redis", node: "vault" },
  "prometheus": { container: "prometheus", node: "vault" },
  "grafana": { container: "grafana", node: "vault" },
  "plex": { container: "plex", node: "vault" },
  "sonarr": { container: "sonarr", node: "vault" },
  "radarr": { container: "radarr", node: "vault" },
  "stash": { container: "stash", node: "vault" },
  "vault-node-exporter": { container: "node-exporter", node: "vault" },
};

function toPrometheusLink(serviceId: string) {
  const expr = `probe_success{service_id="${serviceId}"}`;
  return `${config.prometheus.url}/graph?g0.expr=${encodeURIComponent(expr)}&g0.tab=0`;
}

function exportSnapshot(snapshot: ServicesSnapshot) {
  const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `athanor-services-${new Date().toISOString()}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function serviceSurfaceClass(healthy: boolean) {
  return healthy
    ? "surface-instrument border"
    : "surface-hero border";
}

export function ServicesConsole({
  initialSnapshot,
  initialHistory,
}: {
  initialSnapshot: ServicesSnapshot;
  initialHistory: ServicesHistorySnapshot;
}) {
  const { getSearchValue, setSearchValue } = useUrlState();
  const search = getSearchValue("search", "");
  const status = getSearchValue("status", "all") as StatusFilter;
  const node = getSearchValue("node", "all");
  const category = getSearchValue("category", "all");
  const sort = getSearchValue("sort", "severity") as SortMode;
  const serviceId = getSearchValue("service", "");
  const windowValue = getSearchValue("window", "3h");
  const window = isTimeWindow(windowValue) ? windowValue : "3h";
  const deferredSearch = useDeferredValue(search);

  const [restarting, setRestarting] = useState<string | null>(null);
  const [restartResult, setRestartResult] = useState<{ ok: boolean; error?: string } | null>(null);
  const [logs, setLogs] = useState<string | null>(null);
  const [logsLoading, setLogsLoading] = useState(false);

  const servicesQuery = useQuery({
    queryKey: queryKeys.services,
    queryFn: getServices,
    initialData: initialSnapshot,
    ...liveQueryOptions(LIVE_REFRESH_INTERVALS.telemetry),
  });
  const historyQuery = useQuery({
    queryKey: queryKeys.servicesHistory(window),
    queryFn: () => getServicesHistory(window),
    initialData: window === initialHistory.window ? initialHistory : undefined,
    ...liveQueryOptions(LIVE_REFRESH_INTERVALS.telemetry),
  });
  const containersQuery = useQuery({
    queryKey: ["containers"],
    queryFn: getContainers,
    ...liveQueryOptions(60_000),
  });

  const handleRestart = useCallback(async (containerName: string, node: string) => {
    setRestarting(containerName);
    setRestartResult(null);
    const result = await restartContainer(containerName, node);
    setRestartResult(result);
    setRestarting(null);
    if (result.ok) {
      setTimeout(() => void servicesQuery.refetch(), 3000);
    }
  }, [servicesQuery]);

  const handleViewLogs = useCallback(async (containerName: string, node: string) => {
    setLogsLoading(true);
    setLogs(null);
    const text = await getContainerLogs(containerName, 80, node);
    setLogs(text);
    setLogsLoading(false);
  }, []);

  if (servicesQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Operations"
          title="Services"
          description="Service monitoring failed to load."
          attentionHref="/services"
        />
        <ErrorPanel
          description={
            servicesQuery.error instanceof Error
              ? servicesQuery.error.message
              : "Failed to load services."
          }
        />
      </div>
    );
  }

  const snapshot = servicesQuery.data ?? initialSnapshot;
  const history = historyQuery.data ?? initialHistory;
  const normalizedSearch = deferredSearch.trim().toLowerCase();
  const visibleServices = snapshot.services
    .filter((service) => {
      if (status === "healthy" && !service.healthy) {
        return false;
      }
      if (status === "degraded" && service.healthy) {
        return false;
      }
      if (node !== "all" && service.nodeId !== node) {
        return false;
      }
      if (category !== "all" && service.category !== category) {
        return false;
      }
      if (!normalizedSearch) {
        return true;
      }
      return (
        service.name.toLowerCase().includes(normalizedSearch) ||
        service.url.toLowerCase().includes(normalizedSearch) ||
        service.description.toLowerCase().includes(normalizedSearch)
      );
    })
    .sort((left, right) => {
      if (sort === "name") {
        return left.name.localeCompare(right.name);
      }
      if (sort === "latency") {
        return (right.latencyMs ?? -1) - (left.latencyMs ?? -1);
      }
      if (left.healthy !== right.healthy) {
        return Number(left.healthy) - Number(right.healthy);
      }
      return (right.latencyMs ?? -1) - (left.latencyMs ?? -1);
    });

  const activeService = snapshot.services.find((service) => service.id === serviceId) ?? null;
  const activeHistory = history?.series.find((series) => series.serviceId === serviceId) ?? null;
  const availabilityData = (history?.aggregate ?? []).map((point) => ({
    timestamp: point.timestamp,
    availability: point.value,
  }));
  const serviceTrendData = (activeHistory?.points ?? []).map((point) => ({
    timestamp: point.timestamp,
    latency: point.latencyMs,
    availability: point.availability !== null ? point.availability * 100 : null,
  }));
  const nodeOptions = config.nodes.filter((clusterNode) =>
    snapshot.services.some((service) => service.nodeId === clusterNode.id)
  );
  const categoryOptions = Array.from(new Set(snapshot.services.map((service) => service.category)));

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Operations"
        title="Services"
        description="Operational service surface with persisted filters, history, deep links, and safe export/copy actions."
        attentionHref="/services"
        actions={
          <>
            <LiveBadge updatedAt={snapshot.generatedAt} intervalMs={LIVE_REFRESH_INTERVALS.telemetry} />
            <Button variant="outline" onClick={() => exportSnapshot(snapshot)}>
              <Download className="mr-2 h-4 w-4" />
              Export view
            </Button>
            <Button variant="outline" onClick={() => void servicesQuery.refetch()} disabled={servicesQuery.isFetching}>
              <RefreshCcw className={`mr-2 h-4 w-4 ${servicesQuery.isFetching ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Healthy"
            value={`${snapshot.summary.healthy}/${snapshot.summary.total}`}
            detail={snapshot.summary.degraded > 0 ? `${snapshot.summary.degraded} degraded services.` : "All probes healthy."}
            tone={snapshot.summary.degraded > 0 ? "warning" : "success"}
          />
          <StatCard
            label="Average latency"
            value={formatLatency(snapshot.summary.averageLatencyMs)}
            detail={`Last probe ${formatRelativeTime(snapshot.generatedAt)}.`}
            detailVolatile
          />
          <StatCard
            label="Visible services"
            value={`${visibleServices.length}`}
            detail="After all active filters."
          />
          <StatCard
            label="History window"
            value={getTimeWindow(window).label}
            detail="Prometheus probe trend range."
          />
        </div>
      </PageHeader>

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.35fr]">
        <Card className="surface-panel">
          <CardHeader>
            <CardTitle className="text-lg">Filters and controls</CardTitle>
            <CardDescription>All filter state is shareable in the URL for operator handoffs.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(event) => setSearchValue("search", event.target.value || null)}
                placeholder="Search name, URL, or service detail"
                className="surface-instrument pl-9"
                aria-label="Search services"
              />
            </div>

            <FilterRow
              label="Status"
              values={[
                { id: "all", label: "All" },
                { id: "healthy", label: "Healthy" },
                { id: "degraded", label: "Degraded" },
              ]}
              activeValue={status}
              onChange={(value) => setSearchValue("status", value === "all" ? null : value)}
            />

            <FilterRow
              label="Node"
              values={[{ id: "all", label: "All nodes" }, ...nodeOptions.map((option) => ({ id: option.id, label: option.name }))]}
              activeValue={node}
              onChange={(value) => setSearchValue("node", value === "all" ? null : value)}
            />

            <FilterRow
              label="Category"
              values={[
                { id: "all", label: "All categories" },
                ...categoryOptions.map((option) => ({
                  id: option,
                  label: formatCategoryLabel(option),
                })),
              ]}
              activeValue={category}
              onChange={(value) => setSearchValue("category", value === "all" ? null : value)}
            />

            <FilterRow
              label="Window"
              values={TIME_WINDOWS.map((option) => ({ id: option.id, label: option.label }))}
              activeValue={window}
              onChange={(value) => setSearchValue("window", value)}
            />

            <FilterRow
              label="Sort"
              values={[
                { id: "severity", label: "Severity" },
                { id: "latency", label: "Latency" },
                { id: "name", label: "Name" },
              ]}
              activeValue={sort}
              onChange={(value) => setSearchValue("sort", value === "severity" ? null : value)}
            />
          </CardContent>
        </Card>

        <Card className="surface-instrument">
          <CardHeader>
            <CardTitle className="text-lg">Availability trend</CardTitle>
            <CardDescription>Prometheus blackbox availability over the selected history window.</CardDescription>
          </CardHeader>
          <CardContent>
            {availabilityData.length > 0 ? (
              <MetricChart
                data={availabilityData}
                series={[{ dataKey: "availability", label: "Availability", color: "var(--chart-cat-1)" }]}
                mode="area"
                valueSuffix="%"
              />
            ) : (
              <EmptyState
                title="No history yet"
                description="Historical service probe data will appear after blackbox metrics are collected in Prometheus."
              />
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {snapshot.nodes.map((clusterNode) => (
          <Card key={clusterNode.id} className="surface-instrument">
            <CardContent className="p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-lg font-semibold">{clusterNode.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {clusterNode.healthyServices}/{clusterNode.totalServices} healthy
                  </p>
                </div>
                <StatusDot
                  tone={clusterNode.degradedServices > 0 ? "warning" : "healthy"}
                  pulse={clusterNode.degradedServices > 0}
                />
              </div>
              <div className="mt-4 grid gap-2 text-sm text-muted-foreground">
                <div className="flex items-center justify-between">
                  <span>Latency</span>
                  <span>{formatLatency(clusterNode.averageLatencyMs)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Services</span>
                  <span>{clusterNode.totalServices}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Service inventory</CardTitle>
          <CardDescription>Node and category segmented view with detail drill-down.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {visibleServices.length === 0 ? (
            <EmptyState
              title="No matching services"
              description="Adjust the filters or clear the search to widen the visible service set."
            />
          ) : (
            visibleServices.map((service) => (
              <button
                key={service.id}
                type="button"
                onClick={() => setSearchValue("service", service.id)}
                className={`w-full rounded-2xl p-4 text-left transition hover:bg-accent/40 ${serviceSurfaceClass(service.healthy)}`}
              >
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusDot tone={service.healthy ? "healthy" : "danger"} pulse={!service.healthy} />
                      <p className="text-base font-medium">{service.name}</p>
                      <Badge variant="secondary">{formatCategoryLabel(service.category)}</Badge>
                      <Badge variant="outline">{service.node}</Badge>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">{service.description}</p>
                    <p className="mt-2 truncate font-mono text-xs text-muted-foreground">{service.url}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge
                      variant="outline"
                      className="status-badge"
                      data-tone={service.healthy ? "success" : "danger"}
                    >
                      {service.healthy ? "Healthy" : "Degraded"}
                    </Badge>
                    <Badge variant="outline" className="status-badge">
                      {formatLatency(service.latencyMs)}
                    </Badge>
                  </div>
                </div>
              </button>
            ))
          )}
        </CardContent>
      </Card>

      <Sheet open={Boolean(activeService)} onOpenChange={(open) => {
        setSearchValue("service", open && activeService ? activeService.id : null);
        if (!open) { setLogs(null); setRestartResult(null); }
      }}>
        <SheetContent side="right" className="w-full max-w-xl overflow-y-auto border-l border-border/80 bg-background/95">
          {activeService ? (
            <>
              <SheetHeader className="border-b border-border/80 px-6 py-5 text-left">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <SheetTitle className="text-xl">{activeService.name}</SheetTitle>
                    <SheetDescription>{activeService.description}</SheetDescription>
                  </div>
                  <Badge variant={activeService.healthy ? "outline" : "destructive"}>
                    {activeService.healthy ? "Healthy" : "Degraded"}
                  </Badge>
                </div>
              </SheetHeader>

              <div className="space-y-6 p-6">
                <div className="grid gap-4 md:grid-cols-2">
                  <StatCard
                    label="Latency"
                    value={formatLatency(activeService.latencyMs)}
                    detail={`Checked ${formatRelativeTime(activeService.checkedAt)}`}
                    detailVolatile
                  />
                  <StatCard label="Category" value={formatCategoryLabel(activeService.category)} detail={activeService.node} />
                </div>

                <Card className="surface-instrument">
                  <CardHeader>
                    <CardTitle className="text-lg">Probe history</CardTitle>
                    <CardDescription>Availability and latency for the selected service.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {serviceTrendData.length > 0 ? (
                      <MetricChart
                        data={serviceTrendData}
                        series={[
                          { dataKey: "latency", label: "Latency", color: "var(--chart-cat-1)" },
                          { dataKey: "availability", label: "Availability", color: "var(--chart-cat-2)" },
                        ]}
                      />
                    ) : (
                      <EmptyState
                        title="No history for this service"
                        description="Prometheus has not collected probe data for the selected service yet."
                      />
                    )}
                  </CardContent>
                </Card>

                <Card className="border-border/70 bg-card/70">
                  <CardHeader>
                    <CardTitle className="text-lg">Safe actions</CardTitle>
                    <CardDescription>Convenience actions for inspection and handoff.</CardDescription>
                  </CardHeader>
                  <CardContent className="grid gap-3 sm:grid-cols-2">
                    <Button variant="outline" onClick={() => navigator.clipboard.writeText(activeService.url)}>
                      <Copy className="mr-2 h-4 w-4" />
                      Copy endpoint
                    </Button>
                    <Button asChild variant="outline">
                      <a href={activeService.url} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="mr-2 h-4 w-4" />
                        Open service
                      </a>
                    </Button>
                    <Button asChild variant="outline">
                      <a href={config.grafana.url} target="_blank" rel="noopener noreferrer">
                        <ArrowUpRight className="mr-2 h-4 w-4" />
                        Open Grafana
                      </a>
                    </Button>
                    <Button asChild variant="outline">
                      <a href={toPrometheusLink(activeService.id)} target="_blank" rel="noopener noreferrer">
                        <ArrowUpRight className="mr-2 h-4 w-4" />
                        Probe in Prometheus
                      </a>
                    </Button>
                  </CardContent>
                </Card>

                {(() => {
                  const mapped = SERVICE_CONTAINER_MAP[activeService.id];
                  const containerName = mapped?.container
                    ?? (containersQuery.data ?? []).find((c: ContainerInfo) =>
                      c.name.includes(activeService.id.replace(/-/g, ""))
                      || activeService.name.toLowerCase().includes(c.name.replace(/^athanor-/, ""))
                    )?.name;
                  const containerNode = mapped?.node
                    ?? (containersQuery.data ?? []).find((c: ContainerInfo) => c.name === containerName)?.node
                    ?? "workshop";
                  const container = containerName
                    ? (containersQuery.data ?? []).find((c: ContainerInfo) => c.name === containerName && c.node === containerNode)
                    : null;
                  const isProduction = containerNode === "foundry";

                  if (!containerName) return null;

                  return (
                    <Card className={isProduction ? "border-red-500/30 bg-red-950/10" : "border-amber-500/30 bg-amber-950/10"}>
                      <CardHeader>
                        <CardTitle className="text-lg">Container control</CardTitle>
                        <CardDescription>
                          Docker container: <code className="text-xs font-mono">{containerName}</code>
                          <Badge variant="outline" className="ml-2">{containerNode}</Badge>
                          {container && (
                            <Badge variant="outline" className="ml-2" data-tone={container.state === "running" ? "success" : "danger"}>
                              {container.state}
                            </Badge>
                          )}
                          {isProduction && (
                            <Badge variant="destructive" className="ml-2">Production — read-only</Badge>
                          )}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="grid gap-3 sm:grid-cols-2">
                          {!isProduction && (
                            <Button
                              variant="outline"
                              className="border-amber-500/30 text-amber-200 hover:bg-amber-900/30"
                              disabled={restarting === containerName}
                              onClick={() => void handleRestart(containerName, containerNode)}
                            >
                              <Power className="mr-2 h-4 w-4" />
                              {restarting === containerName ? "Restarting..." : "Restart"}
                            </Button>
                          )}
                          <Button
                            variant="outline"
                            disabled={logsLoading}
                            onClick={() => void handleViewLogs(containerName, containerNode)}
                          >
                            <FileText className="mr-2 h-4 w-4" />
                            {logsLoading ? "Loading..." : "View logs"}
                          </Button>
                        </div>
                        {restartResult && (
                          <p className={`text-sm ${restartResult.ok ? "text-green-400" : "text-red-400"}`}>
                            {restartResult.ok ? "Container restarted successfully." : restartResult.error}
                          </p>
                        )}
                        {logs !== null && (
                          <pre className="max-h-64 overflow-auto rounded-xl border border-border/50 bg-black/40 p-3 font-mono text-xs text-muted-foreground whitespace-pre-wrap">
                            {logs || "(no output)"}
                          </pre>
                        )}
                      </CardContent>
                    </Card>
                  );
                })()}

                <Card className="border-border/70 bg-card/70">
                  <CardHeader>
                    <CardTitle className="text-lg">Endpoint detail</CardTitle>
                    <CardDescription>Canonical URL for copy/paste and external tooling.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="rounded-2xl border border-border/70 bg-background/20 p-4 font-mono text-sm text-muted-foreground">
                      {compactText(activeService.url, 200)}
                    </p>
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

function FilterRow({
  label,
  values,
  activeValue,
  onChange,
}: {
  label: string;
  values: Array<{ id: string; label: string }>;
  activeValue: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
      <div className="flex flex-wrap gap-2">
        {values.map((value) => (
          <Button
            key={value.id}
            size="sm"
            variant={activeValue === value.id ? "default" : "outline"}
            onClick={() => onChange(value.id)}
          >
            {value.label}
          </Button>
        ))}
      </div>
    </div>
  );
}
