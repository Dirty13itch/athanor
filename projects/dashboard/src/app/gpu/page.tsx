import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { queryPrometheus, queryPrometheusRange, type PrometheusResult } from "@/lib/api";
import { config } from "@/lib/config";
import { Sparkline } from "@/components/sparkline";
import { ProgressBar } from "@/components/progress-bar";
import { AutoRefresh } from "@/components/auto-refresh";

export const revalidate = 15;

interface GpuData {
  gpu_name: string;
  gpu_bus_id: string;
  instance: string;
  gpuIndex: number;
  utilization: string | null;
  memoryUsed: string | null;
  memoryTotal: string | null;
  temperature: string | null;
  power: string | null;
  utilizationHistory: number[];
  tempHistory: number[];
}

async function getGpuMetrics(): Promise<GpuData[]> {
  const now = Math.floor(Date.now() / 1000);
  const oneHourAgo = now - 3600;

  const [utilization, memUsed, memTotal, temperature, power, utilHistory, tempHistory] = await Promise.all([
    queryPrometheus("DCGM_FI_DEV_GPU_UTIL").catch(() => [] as PrometheusResult[]),
    queryPrometheus("DCGM_FI_DEV_FB_USED").catch(() => [] as PrometheusResult[]),
    queryPrometheus("DCGM_FI_DEV_FB_FREE + DCGM_FI_DEV_FB_USED").catch(() => [] as PrometheusResult[]),
    queryPrometheus("DCGM_FI_DEV_GPU_TEMP").catch(() => [] as PrometheusResult[]),
    queryPrometheus("DCGM_FI_DEV_POWER_USAGE").catch(() => [] as PrometheusResult[]),
    queryPrometheusRange("DCGM_FI_DEV_GPU_UTIL", oneHourAgo, now, 60).catch(() => []),
    queryPrometheusRange("DCGM_FI_DEV_GPU_TEMP", oneHourAgo, now, 60).catch(() => []),
  ]);

  const gpuMap = new Map<string, GpuData>();

  for (const r of utilization) {
    const gpuId = r.metric.gpu ?? r.metric.gpu_bus_id ?? "0";
    const key = `${r.metric.instance}::${gpuId}`;
    if (!gpuMap.has(key)) {
      gpuMap.set(key, {
        gpu_name: r.metric.modelName ?? r.metric.gpu_name ?? "GPU",
        gpu_bus_id: r.metric.gpu_bus_id ?? r.metric.gpu ?? "",
        instance: r.metric.instance ?? "",
        gpuIndex: parseInt(r.metric.gpu ?? "0"),
        utilization: null,
        memoryUsed: null,
        memoryTotal: null,
        temperature: null,
        power: null,
        utilizationHistory: [],
        tempHistory: [],
      });
    }
    gpuMap.get(key)!.utilization = r.value[1];
  }

  const findVal = (results: PrometheusResult[], instance: string, busId: string) =>
    results.find(
      (r) =>
        r.metric.instance === instance &&
        (r.metric.gpu_bus_id === busId || r.metric.gpu === busId || r.metric.UUID === busId)
    )?.value[1] ?? null;

  const findHistory = (rangeResults: { metric: Record<string, string>; values: [number, string][] }[], instance: string, gpuId: string) => {
    const match = rangeResults.find(
      (r) => r.metric.instance === instance && (r.metric.gpu === gpuId || r.metric.gpu_bus_id === gpuId)
    );
    return match?.values.map(([, v]) => parseFloat(v)) ?? [];
  };

  for (const [key, gpu] of gpuMap) {
    const [inst, gpuId] = key.split("::");
    gpu.memoryUsed = findVal(memUsed, inst, gpu.gpu_bus_id || gpuId);
    gpu.memoryTotal = findVal(memTotal, inst, gpu.gpu_bus_id || gpuId);
    gpu.temperature = findVal(temperature, inst, gpu.gpu_bus_id || gpuId);
    gpu.power = findVal(power, inst, gpu.gpu_bus_id || gpuId);
    gpu.utilizationHistory = findHistory(utilHistory, inst, gpuId);
    gpu.tempHistory = findHistory(tempHistory, inst, gpuId);
  }

  return Array.from(gpuMap.values());
}

function nodeFromInstance(instance: string): string {
  if (instance.includes("192.168.1.244")) return "Foundry";
  if (instance.includes("192.168.1.225")) return "Workshop";
  return instance;
}

function getWorkload(instance: string, gpuIndex: number): string {
  const ip = instance.split(":")[0];
  return config.gpuWorkloads[ip]?.[gpuIndex] ?? "";
}

function getPowerLimit(instance: string, gpuIndex: number): number {
  const ip = instance.split(":")[0];
  return config.gpuPowerLimits[ip]?.[gpuIndex] ?? 300;
}

function formatMiB(val: string | null): string {
  if (!val) return "--";
  const mib = parseFloat(val);
  if (mib > 1024) return `${(mib / 1024).toFixed(1)} GiB`;
  return `${mib.toFixed(0)} MiB`;
}

function utilColor(val: string | null): string {
  if (!val) return "text-muted-foreground";
  const n = parseFloat(val);
  if (n > 80) return "text-red-400";
  if (n > 50) return "text-yellow-400";
  return "text-green-400";
}

function tempColor(val: string | null): string {
  if (!val) return "text-muted-foreground";
  const n = parseFloat(val);
  if (n > 80) return "text-red-400";
  if (n > 65) return "text-yellow-400";
  return "text-green-400";
}

function sparkColor(val: string | null): string {
  if (!val) return "#22c55e";
  const n = parseFloat(val);
  if (n > 80) return "#ef4444";
  if (n > 50) return "#eab308";
  return "#22c55e";
}

export default async function GpuPage() {
  let gpus: GpuData[] = [];
  let error: string | null = null;

  try {
    gpus = await getGpuMetrics();
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to fetch GPU metrics";
  }

  const byNode = new Map<string, GpuData[]>();
  for (const gpu of gpus) {
    const node = nodeFromInstance(gpu.instance);
    const group = byNode.get(node) ?? [];
    group.push(gpu);
    byNode.set(node, group);
  }

  return (
    <div className="space-y-6">
      <AutoRefresh intervalMs={10000} />

      <div>
        <h1 className="text-2xl font-bold tracking-tight">GPU Metrics</h1>
        <p className="text-muted-foreground">
          Real-time DCGM metrics with 1-hour sparkline history (auto-refreshes every 10s)
        </p>
      </div>

      {error && (
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-destructive">{error}</p>
            <p className="text-xs text-muted-foreground mt-1">
              Ensure Prometheus is running at http://192.168.1.203:9090 and DCGM exporters are active.
            </p>
          </CardContent>
        </Card>
      )}

      {gpus.length === 0 && !error && (
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-muted-foreground">No GPU metrics found. DCGM exporters may not be running.</p>
          </CardContent>
        </Card>
      )}

      {Array.from(byNode.entries()).map(([node, nodeGpus]) => {
        const nodeConfig = config.nodes.find((n) => n.name === node);
        const nodeTotalPower = nodeGpus.reduce((sum, g) => sum + parseFloat(g.power ?? "0"), 0);
        const nodePsuWatts = nodeConfig?.psuWatts ?? 0;

        return (
          <div key={node} className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">{node}</h2>
                {nodeConfig && (
                  <p className="text-xs text-muted-foreground">
                    {nodeConfig.role} — {nodeGpus.length} GPUs, {nodeConfig.vram} GB VRAM
                  </p>
                )}
              </div>
              {nodePsuWatts > 0 && (
                <div className="text-right w-48">
                  <div className="flex justify-between text-xs text-muted-foreground mb-1">
                    <span>Power Budget</span>
                    <span className="font-mono">{nodeTotalPower.toFixed(0)}W / {nodePsuWatts}W</span>
                  </div>
                  <ProgressBar
                    value={nodeTotalPower}
                    max={nodePsuWatts}
                    colorStops={[
                      { threshold: 80, color: "bg-red-500" },
                      { threshold: 60, color: "bg-yellow-500" },
                      { threshold: 0, color: "bg-green-500" },
                    ]}
                  />
                </div>
              )}
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              {nodeGpus.map((gpu, i) => {
                const workload = getWorkload(gpu.instance, gpu.gpuIndex);
                const powerLimit = getPowerLimit(gpu.instance, gpu.gpuIndex);

                return (
                  <Card key={`${gpu.instance}-${gpu.gpu_bus_id}-${i}`}>
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-medium">{gpu.gpu_name}</CardTitle>
                        <div className="flex items-center gap-2">
                          {workload && (
                            <Badge variant="outline" className="text-xs">{workload}</Badge>
                          )}
                          <Badge variant="outline">{node}</Badge>
                        </div>
                      </div>
                      <CardDescription className="font-mono text-xs">{gpu.gpu_bus_id}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 gap-4">
                        <Metric
                          label="Utilization"
                          value={gpu.utilization ? `${parseFloat(gpu.utilization).toFixed(0)}%` : "--"}
                          colorClass={utilColor(gpu.utilization)}
                        />
                        <Metric
                          label="Temperature"
                          value={gpu.temperature ? `${parseFloat(gpu.temperature).toFixed(0)}C` : "--"}
                          colorClass={tempColor(gpu.temperature)}
                        />
                        <Metric
                          label="Memory Used"
                          value={formatMiB(gpu.memoryUsed)}
                          colorClass="text-foreground"
                        />
                        <Metric
                          label="Power"
                          value={gpu.power ? `${parseFloat(gpu.power).toFixed(0)}W / ${powerLimit}W` : "--"}
                          colorClass="text-foreground"
                        />
                      </div>

                      {/* Sparklines */}
                      {(gpu.utilizationHistory.length > 1 || gpu.tempHistory.length > 1) && (
                        <div className="mt-3 grid grid-cols-2 gap-3">
                          {gpu.utilizationHistory.length > 1 && (
                            <div>
                              <p className="text-xs text-muted-foreground mb-1">Utilization (1h)</p>
                              <Sparkline
                                data={gpu.utilizationHistory}
                                width={180}
                                height={28}
                                color={sparkColor(gpu.utilization)}
                                fill
                                className="w-full"
                              />
                            </div>
                          )}
                          {gpu.tempHistory.length > 1 && (
                            <div>
                              <p className="text-xs text-muted-foreground mb-1">Temperature (1h)</p>
                              <Sparkline
                                data={gpu.tempHistory}
                                width={180}
                                height={28}
                                color={sparkColor(gpu.temperature)}
                                fill
                                className="w-full"
                              />
                            </div>
                          )}
                        </div>
                      )}

                      {/* VRAM Bar */}
                      {gpu.memoryUsed && gpu.memoryTotal && (
                        <div className="mt-3">
                          <div className="flex justify-between text-xs text-muted-foreground mb-1">
                            <span>VRAM</span>
                            <span>{formatMiB(gpu.memoryUsed)} / {formatMiB(gpu.memoryTotal)}</span>
                          </div>
                          <div className="h-2 rounded-full bg-muted overflow-hidden">
                            <div
                              className="h-full rounded-full bg-primary"
                              style={{
                                width: `${Math.min(100, (parseFloat(gpu.memoryUsed) / parseFloat(gpu.memoryTotal)) * 100)}%`,
                              }}
                            />
                          </div>
                        </div>
                      )}

                      {/* Power Bar */}
                      {gpu.power && (
                        <div className="mt-2">
                          <div className="flex justify-between text-xs text-muted-foreground mb-1">
                            <span>Power</span>
                            <span>{parseFloat(gpu.power).toFixed(0)}W / {powerLimit}W</span>
                          </div>
                          <ProgressBar
                            value={parseFloat(gpu.power)}
                            max={powerLimit}
                            colorStops={[
                              { threshold: 90, color: "bg-red-500" },
                              { threshold: 70, color: "bg-yellow-500" },
                              { threshold: 0, color: "bg-blue-500" },
                            ]}
                          />
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Metric({ label, value, colorClass }: { label: string; value: string; colorClass: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`text-lg font-semibold font-mono ${colorClass}`}>{value}</p>
    </div>
  );
}
