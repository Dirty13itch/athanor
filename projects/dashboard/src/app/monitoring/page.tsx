import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { queryPrometheus, queryPrometheusRange, type PrometheusResult } from "@/lib/api";
import { config } from "@/lib/config";
import { ProgressBar } from "@/components/progress-bar";
import { Sparkline } from "@/components/sparkline";
import { AutoRefresh } from "@/components/auto-refresh";

export const revalidate = 15;

// --- Data fetching ---

interface NodeMetrics {
  name: string;
  ip: string;
  role: string;
  cpuUsage: number | null;
  cpuCores: number | null;
  memUsed: number | null;
  memTotal: number | null;
  diskUsed: number | null;
  diskTotal: number | null;
  networkRxRate: number | null;
  networkTxRate: number | null;
  uptime: number | null;
  load1: number | null;
  cpuHistory: number[];
  memHistory: number[];
}

function findByInstance(results: PrometheusResult[], ip: string): string | null {
  const r = results.find((r) => r.metric.instance?.includes(ip));
  return r ? r.value[1] : null;
}

function findHistoryByInstance(
  results: { metric: Record<string, string>; values: [number, string][] }[],
  ip: string
): number[] {
  const r = results.find((r) => r.metric.instance?.includes(ip));
  return r?.values.map(([, v]) => parseFloat(v)) ?? [];
}

async function getNodeMetrics(): Promise<NodeMetrics[]> {
  const now = Math.floor(Date.now() / 1000);
  const oneHourAgo = now - 3600;

  const [
    cpuUsage,
    memAvail,
    memTotal,
    diskUsed,
    diskTotal,
    netRx,
    netTx,
    uptime,
    load1,
    cpuHistory,
    memHistory,
  ] = await Promise.all([
    // CPU: 1 - idle rate
    queryPrometheus(
      '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
    ).catch(() => []),
    queryPrometheus("node_memory_MemAvailable_bytes").catch(() => []),
    queryPrometheus("node_memory_MemTotal_bytes").catch(() => []),
    // Root filesystem used
    queryPrometheus(
      'node_filesystem_size_bytes{mountpoint="/"} - node_filesystem_avail_bytes{mountpoint="/"}'
    ).catch(() => []),
    queryPrometheus('node_filesystem_size_bytes{mountpoint="/"}').catch(() => []),
    // Network receive rate (bytes/s, all interfaces except lo)
    queryPrometheus(
      'sum by (instance) (rate(node_network_receive_bytes_total{device!="lo"}[5m]))'
    ).catch(() => []),
    queryPrometheus(
      'sum by (instance) (rate(node_network_transmit_bytes_total{device!="lo"}[5m]))'
    ).catch(() => []),
    queryPrometheus("node_time_seconds - node_boot_time_seconds").catch(() => []),
    queryPrometheus("node_load1").catch(() => []),
    // History: CPU usage over 1 hour
    queryPrometheusRange(
      '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
      oneHourAgo,
      now,
      60
    ).catch(() => []),
    // History: Memory usage % over 1 hour
    queryPrometheusRange(
      "100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)",
      oneHourAgo,
      now,
      60
    ).catch(() => []),
  ]);

  return config.nodes
    .map((node) => {
      const mem_avail = findByInstance(memAvail, node.ip);
      const mem_total = findByInstance(memTotal, node.ip);

      return {
        name: node.name,
        ip: node.ip,
        role: node.role,
        cpuUsage: parseFloatSafe(findByInstance(cpuUsage, node.ip)),
        cpuCores: null, // Could query but not needed for display
        memUsed:
          mem_total && mem_avail
            ? parseFloat(mem_total) - parseFloat(mem_avail)
            : null,
        memTotal: parseFloatSafe(mem_total),
        diskUsed: parseFloatSafe(findByInstance(diskUsed, node.ip)),
        diskTotal: parseFloatSafe(findByInstance(diskTotal, node.ip)),
        networkRxRate: parseFloatSafe(findByInstance(netRx, node.ip)),
        networkTxRate: parseFloatSafe(findByInstance(netTx, node.ip)),
        uptime: parseFloatSafe(findByInstance(uptime, node.ip)),
        load1: parseFloatSafe(findByInstance(load1, node.ip)),
        cpuHistory: findHistoryByInstance(cpuHistory, node.ip),
        memHistory: findHistoryByInstance(memHistory, node.ip),
      };
    });
}

function parseFloatSafe(val: string | null): number | null {
  if (!val) return null;
  const n = parseFloat(val);
  return isNaN(n) ? null : n;
}

function formatBytes(bytes: number | null, decimals = 1): string {
  if (bytes === null) return "--";
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KiB", "MiB", "GiB", "TiB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(decimals)} ${sizes[i]}`;
}

function formatRate(bytesPerSec: number | null): string {
  if (bytesPerSec === null) return "--";
  if (bytesPerSec < 1024) return `${bytesPerSec.toFixed(0)} B/s`;
  if (bytesPerSec < 1024 * 1024) return `${(bytesPerSec / 1024).toFixed(1)} KiB/s`;
  if (bytesPerSec < 1024 * 1024 * 1024)
    return `${(bytesPerSec / (1024 * 1024)).toFixed(1)} MiB/s`;
  return `${(bytesPerSec / (1024 * 1024 * 1024)).toFixed(2)} GiB/s`;
}

function formatUptime(seconds: number | null): string {
  if (seconds === null) return "--";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  if (days > 0) return `${days}d ${hours}h`;
  const mins = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${mins}m`;
}

function usageColor(pct: number | null): string {
  if (pct === null) return "text-muted-foreground";
  if (pct > 80) return "text-red-400";
  if (pct > 50) return "text-yellow-400";
  return "text-green-400";
}

function sparklineColor(pct: number | null): string {
  if (pct === null) return "#22c55e";
  if (pct > 80) return "#ef4444";
  if (pct > 50) return "#eab308";
  return "#22c55e";
}

// --- Component ---

export default async function MonitoringPage() {
  let nodes: NodeMetrics[] = [];
  let error: string | null = null;

  try {
    nodes = await getNodeMetrics();
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to fetch metrics";
  }

  // Aggregate totals
  const totalMemUsed = nodes.reduce((s, n) => s + (n.memUsed ?? 0), 0);
  const totalMemTotal = nodes.reduce((s, n) => s + (n.memTotal ?? 0), 0);
  const avgCpu =
    nodes.length > 0
      ? nodes.reduce((s, n) => s + (n.cpuUsage ?? 0), 0) / nodes.length
      : 0;

  return (
    <div className="space-y-6">
      <AutoRefresh intervalMs={15000} />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Monitoring</h1>
          <p className="text-muted-foreground">
            Node health, CPU, memory, disk, and network (auto-refreshes every 15s)
          </p>
        </div>
        <a
          href={config.grafana.url}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent transition-colors"
        >
          Open Grafana
        </a>
      </div>

      {error && (
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Cluster summary */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center gap-8 flex-wrap">
            <div className="text-xs">
              <span className="text-muted-foreground">Nodes</span>{" "}
              <span className="font-mono font-medium">
                {nodes.filter((n) => n.cpuUsage !== null).length}/{nodes.length}
              </span>
            </div>
            <div className="text-xs">
              <span className="text-muted-foreground">Avg CPU</span>{" "}
              <span className={`font-mono font-medium ${usageColor(avgCpu)}`}>
                {avgCpu.toFixed(1)}%
              </span>
            </div>
            <div className="text-xs">
              <span className="text-muted-foreground">Total RAM</span>{" "}
              <span className="font-mono font-medium">
                {formatBytes(totalMemUsed)} / {formatBytes(totalMemTotal)}
              </span>
            </div>
            <div className="text-xs">
              <span className="text-muted-foreground">Network</span>{" "}
              <span className="font-mono font-medium">
                {formatRate(nodes.reduce((s, n) => s + (n.networkRxRate ?? 0), 0))} in /{" "}
                {formatRate(nodes.reduce((s, n) => s + (n.networkTxRate ?? 0), 0))} out
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Per-node cards */}
      <div className="grid gap-4 lg:grid-cols-2">
        {nodes.map((node) => {
          const memPct =
            node.memUsed && node.memTotal
              ? (node.memUsed / node.memTotal) * 100
              : null;
          const diskPct =
            node.diskUsed && node.diskTotal
              ? (node.diskUsed / node.diskTotal) * 100
              : null;

          return (
            <Card key={node.name}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium">{node.name}</CardTitle>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">
                      {node.role}
                    </Badge>
                    {node.cpuUsage !== null ? (
                      <div className="h-2 w-2 rounded-full bg-green-500" />
                    ) : (
                      <div className="h-2 w-2 rounded-full bg-red-500" />
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span className="font-mono">{node.ip}</span>
                  {node.uptime !== null && <span>Up {formatUptime(node.uptime)}</span>}
                  {node.load1 !== null && (
                    <span>
                      Load: <span className="font-mono">{node.load1.toFixed(2)}</span>
                    </span>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {/* CPU */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-muted-foreground">CPU</span>
                    <span
                      className={`font-mono font-medium ${usageColor(node.cpuUsage)}`}
                    >
                      {node.cpuUsage !== null ? `${node.cpuUsage.toFixed(1)}%` : "--"}
                    </span>
                  </div>
                  <ProgressBar
                    value={node.cpuUsage ?? 0}
                    max={100}
                    colorStops={[
                      { threshold: 80, color: "bg-red-500" },
                      { threshold: 50, color: "bg-yellow-500" },
                      { threshold: 0, color: "bg-green-500" },
                    ]}
                  />
                  {node.cpuHistory.length > 1 && (
                    <div className="mt-1">
                      <Sparkline
                        data={node.cpuHistory}
                        width={400}
                        height={24}
                        color={sparklineColor(node.cpuUsage)}
                        fill
                        className="w-full"
                      />
                    </div>
                  )}
                </div>

                {/* Memory */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-muted-foreground">Memory</span>
                    <span className="font-mono">
                      {formatBytes(node.memUsed)} / {formatBytes(node.memTotal)}
                      {memPct !== null && (
                        <span className={` ml-1 ${usageColor(memPct)}`}>
                          ({memPct.toFixed(0)}%)
                        </span>
                      )}
                    </span>
                  </div>
                  <ProgressBar
                    value={memPct ?? 0}
                    max={100}
                    colorStops={[
                      { threshold: 80, color: "bg-red-500" },
                      { threshold: 50, color: "bg-yellow-500" },
                      { threshold: 0, color: "bg-blue-500" },
                    ]}
                  />
                  {node.memHistory.length > 1 && (
                    <div className="mt-1">
                      <Sparkline
                        data={node.memHistory}
                        width={400}
                        height={24}
                        color={sparklineColor(memPct)}
                        fill
                        className="w-full"
                      />
                    </div>
                  )}
                </div>

                {/* Disk */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-muted-foreground">Disk (/)</span>
                    <span className="font-mono">
                      {formatBytes(node.diskUsed)} / {formatBytes(node.diskTotal)}
                      {diskPct !== null && (
                        <span className={` ml-1 ${usageColor(diskPct)}`}>
                          ({diskPct.toFixed(0)}%)
                        </span>
                      )}
                    </span>
                  </div>
                  <ProgressBar
                    value={diskPct ?? 0}
                    max={100}
                    colorStops={[
                      { threshold: 90, color: "bg-red-500" },
                      { threshold: 70, color: "bg-yellow-500" },
                      { threshold: 0, color: "bg-blue-500" },
                    ]}
                  />
                </div>

                {/* Network */}
                <div className="flex gap-6">
                  <div className="text-xs">
                    <span className="text-muted-foreground">Network In</span>{" "}
                    <span className="font-mono font-medium">
                      {formatRate(node.networkRxRate)}
                    </span>
                  </div>
                  <div className="text-xs">
                    <span className="text-muted-foreground">Network Out</span>{" "}
                    <span className="font-mono font-medium">
                      {formatRate(node.networkTxRate)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Grafana deep links */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Grafana Dashboards</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {config.grafanaDashboards.map((dashboard) => (
              <a
                key={dashboard.id}
                href={dashboard.url}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent transition-colors"
              >
                {dashboard.label}
              </a>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
