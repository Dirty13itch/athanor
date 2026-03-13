"use client";
import { useQuery } from "@tanstack/react-query";
import { Download, Flame, Pin, RefreshCcw, Thermometer, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { MetricChart } from "@/components/metric-chart";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { StatusDot } from "@/components/status-dot";
import { getGpuHistory, getGpuSnapshot } from "@/lib/api";
import { type GpuHistoryResponse, type GpuSnapshotResponse } from "@/lib/contracts";
import { formatMiB, formatPercent, formatWatts } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import { isTimeWindow, TIME_WINDOWS } from "@/lib/ranges";
import { useUrlState } from "@/lib/url-state";

function exportSnapshot(snapshot: GpuSnapshotResponse) {
  const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `athanor-gpu-${new Date().toISOString()}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function toggleCompare(current: string, id: string) {
  const next = new Set(current ? current.split(",").filter(Boolean) : []);
  if (next.has(id)) {
    next.delete(id);
  } else if (next.size < 3) {
    next.add(id);
  }
  return Array.from(next).join(",");
}

export function GpuConsole({
  initialSnapshot,
  initialHistory,
}: {
  initialSnapshot: GpuSnapshotResponse;
  initialHistory: GpuHistoryResponse;
}) {
  const { getSearchValue, setSearchValue } = useUrlState();
  const windowValue = getSearchValue("window", "3h");
  const window = isTimeWindow(windowValue) ? windowValue : "3h";
  const highlight = getSearchValue("highlight", "");
  const compare = getSearchValue("compare", "");

  const snapshotQuery = useQuery({
    queryKey: queryKeys.gpuSnapshot,
    queryFn: getGpuSnapshot,
    initialData: initialSnapshot,
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
  });
  const historyQuery = useQuery({
    queryKey: queryKeys.gpuHistory(window),
    queryFn: () => getGpuHistory(window),
    initialData: window === initialHistory.window ? initialHistory : undefined,
  });

  if (snapshotQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Telemetry" title="GPU Metrics" description="GPU telemetry failed to load." />
        <ErrorPanel
          description={
            snapshotQuery.error instanceof Error
              ? snapshotQuery.error.message
              : "Failed to load GPU telemetry."
          }
        />
      </div>
    );
  }

  const snapshot = snapshotQuery.data ?? initialSnapshot;
  const history = historyQuery.data ?? initialHistory;
  const highlightedGpu =
    snapshot.gpus.find((gpu) => gpu.id === highlight) ??
    snapshot.gpus[0] ??
    null;
  const comparedGpuIds = compare ? compare.split(",").filter(Boolean) : [];
  const comparedGpus = snapshot.gpus.filter((gpu) => comparedGpuIds.includes(gpu.id));

  const nodeChartData = Array.from(
    new Set(history.nodes.flatMap((series) => series.points.map((point) => point.timestamp)))
  )
    .sort()
    .map((timestamp) => {
      const row: Record<string, string | number | null> = { timestamp };
      for (const series of history.nodes) {
        row[series.label] =
          series.points.find((point) => point.timestamp === timestamp)?.value ?? null;
      }
      return row;
    });

  const highlightedHistory = history.gpus.find((gpu) => gpu.id === highlightedGpu?.id) ?? null;
  const highlightedData = (highlightedHistory?.points ?? []).map((point) => ({
    timestamp: point.timestamp,
    utilization: point.utilization,
    temperature: point.temperatureC,
    power: point.powerW,
    memory: point.memoryRatio,
  }));

  const compareChartData = Array.from(
    new Set(
      history.gpus
        .filter((gpu) => comparedGpuIds.includes(gpu.id))
        .flatMap((gpu) => gpu.points.map((point) => point.timestamp))
    )
  )
    .sort()
    .map((timestamp) => {
      const row: Record<string, string | number | null> = { timestamp };
      for (const gpu of history.gpus.filter((series) => comparedGpuIds.includes(series.id))) {
        row[gpu.label] =
          gpu.points.find((point) => point.timestamp === timestamp)?.utilization ?? null;
      }
      return row;
    });

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Telemetry"
        title="GPU Metrics"
        description="Prometheus-backed fleet telemetry with time-range selection, hotspot triage, and side-by-side GPU comparison."
        actions={
          <>
            <Button variant="outline" onClick={() => exportSnapshot(snapshot)}>
              <Download className="mr-2 h-4 w-4" />
              Export snapshot
            </Button>
            <Button variant="outline" onClick={() => void snapshotQuery.refetch()} disabled={snapshotQuery.isFetching}>
              <RefreshCcw className={`mr-2 h-4 w-4 ${snapshotQuery.isFetching ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="GPUs" value={`${snapshot.summary.gpuCount}`} detail="Discovered from Prometheus and DCGM exporters." />
          <StatCard label="Average utilization" value={formatPercent(snapshot.summary.averageUtilization, 0)} detail="Fleet-wide utilization average." />
          <StatCard label="Average temperature" value={snapshot.summary.averageTemperature === null ? "--" : `${Math.round(snapshot.summary.averageTemperature)}C`} detail="Mean GPU core temperature." />
          <StatCard label="Power draw" value={formatWatts(snapshot.summary.totalPowerW)} detail="Total instantaneous GPU power." />
        </div>
      </PageHeader>

      <div className="flex flex-wrap gap-2">
        {TIME_WINDOWS.map((option) => (
          <Button
            key={option.id}
            size="sm"
            variant={window === option.id ? "default" : "outline"}
            onClick={() => setSearchValue("window", option.id)}
          >
            {option.label}
          </Button>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.3fr_1fr]">
        <Card className="surface-instrument">
          <CardHeader>
            <CardTitle className="text-lg">Node utilization trend</CardTitle>
            <CardDescription>Average GPU load by node across the selected time range.</CardDescription>
          </CardHeader>
          <CardContent>
            {nodeChartData.length > 0 ? (
              <MetricChart
                data={nodeChartData}
                series={history.nodes.map((series, index) => ({
                  dataKey: series.label,
                  label: series.label,
                        color: `var(--chart-cat-${(index % 3) + 1})`,
                }))}
                valueSuffix="%"
              />
            ) : (
              <EmptyState
                title="No node history yet"
                description="Prometheus range data for GPU utilization is not available for the selected window."
              />
            )}
          </CardContent>
        </Card>

        <Card className="surface-panel">
          <CardHeader>
            <CardTitle className="text-lg">Thermal and power hotspot</CardTitle>
            <CardDescription>Highest-pressure GPUs right now.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {snapshot.gpus.slice(0, 4).map((gpu) => (
              <button
                key={gpu.id}
                type="button"
                onClick={() => setSearchValue("highlight", gpu.id)}
                className={`w-full rounded-2xl border p-4 text-left transition ${
                  highlight === gpu.id
                    ? "surface-hero border"
                    : "surface-instrument border hover:bg-accent/40"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-medium">{gpu.gpuName}</p>
                    <p className="mt-1 text-sm text-muted-foreground">{gpu.node}</p>
                  </div>
                  <Badge variant="outline" className="status-badge">
                    {formatPercent(gpu.utilization, 0)}
                  </Badge>
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
                  <Metric label="Temp" value={gpu.temperatureC === null ? "--" : `${Math.round(gpu.temperatureC)}C`} icon={<Thermometer className="h-3.5 w-3.5" />} />
                  <Metric label="Power" value={formatWatts(gpu.powerW)} icon={<Zap className="h-3.5 w-3.5" />} />
                  <Metric label="VRAM" value={formatMiB(gpu.memoryUsedMiB)} icon={<Flame className="h-3.5 w-3.5" />} />
                </div>
              </button>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <Card className="surface-hero">
          <CardHeader>
            <CardTitle className="text-lg">Selected GPU drill-down</CardTitle>
            <CardDescription>
              {highlightedGpu ? `${highlightedGpu.gpuName} on ${highlightedGpu.node}` : "Select a GPU to inspect its time series."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {highlightedGpu ? (
              <>
                <div className="grid gap-4 sm:grid-cols-4">
                  <StatCard label="Utilization" value={formatPercent(highlightedGpu.utilization, 0)} />
                  <StatCard label="Temperature" value={highlightedGpu.temperatureC === null ? "--" : `${Math.round(highlightedGpu.temperatureC)}C`} />
                  <StatCard label="Power" value={formatWatts(highlightedGpu.powerW)} />
                  <StatCard label="VRAM" value={`${formatMiB(highlightedGpu.memoryUsedMiB)} / ${formatMiB(highlightedGpu.memoryTotalMiB)}`} />
                </div>
                {highlightedData.length > 0 ? (
                  <MetricChart
                    data={highlightedData}
                    series={[
                      { dataKey: "utilization", label: "Utilization", color: "var(--chart-cat-1)" },
                      { dataKey: "temperature", label: "Temperature", color: "var(--signal-danger)" },
                      { dataKey: "power", label: "Power", color: "var(--chart-cat-2)" },
                      { dataKey: "memory", label: "Memory ratio", color: "var(--chart-cat-3)" },
                    ]}
                  />
                ) : (
                  <EmptyState
                    title="No detailed history"
                    description="Prometheus has not returned range data for the selected GPU yet."
                  />
                )}
              </>
            ) : (
              <EmptyState title="No GPU selected" description="Pick a hotspot or a GPU card below to inspect detailed history." />
            )}
          </CardContent>
        </Card>

        <Card className="surface-instrument">
          <CardHeader>
            <CardTitle className="text-lg">Pinned comparison</CardTitle>
            <CardDescription>Pin up to three GPUs to compare utilization curves.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {compareChartData.length > 0 ? (
              <MetricChart
                data={compareChartData}
                series={comparedGpus.map((gpu, index) => ({
                  dataKey: gpu.gpuName,
                  label: gpu.gpuName,
                        color: `var(--chart-cat-${(index % 3) + 1})`,
                }))}
                valueSuffix="%"
              />
            ) : (
              <EmptyState
                title="No GPUs pinned"
                description="Use the pin action on individual GPUs to compare them side by side."
              />
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">GPU inventory</CardTitle>
          <CardDescription>Pin GPUs for comparison or focus one GPU for detailed history.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-2">
          {snapshot.gpus.length > 0 ? (
            snapshot.gpus.map((gpu) => {
              const isPinned = comparedGpuIds.includes(gpu.id);
              const isHighlighted = highlight === gpu.id;
              return (
                <div
                  key={gpu.id}
                  className={`rounded-2xl border p-4 ${
                    isHighlighted ? "surface-hero border" : "surface-instrument border"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">{gpu.gpuName}</p>
                      <p className="mt-1 text-sm text-muted-foreground">{gpu.node}</p>
                      <p className="mt-1 font-mono text-xs text-muted-foreground">{gpu.gpuBusId}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusDot tone={gpu.utilization !== null && gpu.utilization >= 85 ? "warning" : "healthy"} />
                      <Badge variant="outline" className="status-badge">
                        {formatPercent(gpu.utilization, 0)}
                      </Badge>
                    </div>
                  </div>
                  <div className="mt-4 grid gap-2 sm:grid-cols-2">
                    <Metric label="Temperature" value={gpu.temperatureC === null ? "--" : `${Math.round(gpu.temperatureC)}C`} />
                    <Metric label="Power" value={formatWatts(gpu.powerW)} />
                    <Metric label="VRAM used" value={formatMiB(gpu.memoryUsedMiB)} />
                    <Metric label="VRAM total" value={formatMiB(gpu.memoryTotalMiB)} />
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button size="sm" variant={isHighlighted ? "default" : "outline"} onClick={() => setSearchValue("highlight", gpu.id)}>
                      Focus
                    </Button>
                    <Button
                      size="sm"
                      variant={isPinned ? "default" : "outline"}
                      onClick={() => setSearchValue("compare", toggleCompare(compare, gpu.id) || null)}
                    >
                      <Pin className="mr-2 h-3.5 w-3.5" />
                      {isPinned ? "Pinned" : "Pin compare"}
                    </Button>
                  </div>
                </div>
              );
            })
          ) : (
            <EmptyState title="No GPUs found" description="DCGM exporter metrics are not available from Prometheus." />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="surface-metric rounded-xl border p-3">
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      <p className="mt-2 text-sm font-semibold">{value}</p>
    </div>
  );
}
