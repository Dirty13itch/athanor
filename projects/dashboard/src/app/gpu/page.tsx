import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { queryPrometheus, type PrometheusResult } from "@/lib/api";
import { AutoRefresh } from "@/components/auto-refresh";

export const revalidate = 15;

interface GpuData {
  gpu_name: string;
  gpu_bus_id: string;
  instance: string;
  utilization: string | null;
  memoryUsed: string | null;
  memoryTotal: string | null;
  temperature: string | null;
  power: string | null;
}

async function getGpuMetrics(): Promise<GpuData[]> {
  const [utilization, memUsed, memTotal, temperature, power] = await Promise.all([
    queryPrometheus("DCGM_FI_DEV_GPU_UTIL").catch(() => [] as PrometheusResult[]),
    queryPrometheus("DCGM_FI_DEV_FB_USED").catch(() => [] as PrometheusResult[]),
    queryPrometheus("DCGM_FI_DEV_FB_FREE + DCGM_FI_DEV_FB_USED").catch(() => [] as PrometheusResult[]),
    queryPrometheus("DCGM_FI_DEV_GPU_TEMP").catch(() => [] as PrometheusResult[]),
    queryPrometheus("DCGM_FI_DEV_POWER_USAGE").catch(() => [] as PrometheusResult[]),
  ]);

  const gpuMap = new Map<string, GpuData>();

  for (const r of utilization) {
    const key = `${r.metric.instance}::${r.metric.gpu_bus_id ?? r.metric.UUID ?? r.metric.gpu}`;
    if (!gpuMap.has(key)) {
      gpuMap.set(key, {
        gpu_name: r.metric.modelName ?? r.metric.gpu_name ?? "GPU",
        gpu_bus_id: r.metric.gpu_bus_id ?? r.metric.gpu ?? "",
        instance: r.metric.instance ?? "",
        utilization: null,
        memoryUsed: null,
        memoryTotal: null,
        temperature: null,
        power: null,
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

  for (const [, gpu] of gpuMap) {
    gpu.memoryUsed = findVal(memUsed, gpu.instance, gpu.gpu_bus_id);
    gpu.memoryTotal = findVal(memTotal, gpu.instance, gpu.gpu_bus_id);
    gpu.temperature = findVal(temperature, gpu.instance, gpu.gpu_bus_id);
    gpu.power = findVal(power, gpu.instance, gpu.gpu_bus_id);
  }

  return Array.from(gpuMap.values());
}

function nodeFromInstance(instance: string): string {
  if (instance.includes("192.168.1.244")) return "Node 1";
  if (instance.includes("192.168.1.225")) return "Node 2";
  return instance;
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

export default async function GpuPage() {
  let gpus: GpuData[] = [];
  let error: string | null = null;

  try {
    gpus = await getGpuMetrics();
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to fetch GPU metrics";
  }

  // Group by node
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
          Real-time DCGM metrics from Prometheus (auto-refreshes every 10s)
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

      {Array.from(byNode.entries()).map(([node, nodeGpus]) => (
        <div key={node} className="space-y-4">
          <h2 className="text-lg font-semibold">{node}</h2>
          <div className="grid gap-4 md:grid-cols-2">
            {nodeGpus.map((gpu, i) => (
              <Card key={`${gpu.instance}-${gpu.gpu_bus_id}-${i}`}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium">{gpu.gpu_name}</CardTitle>
                    <Badge variant="outline">{node}</Badge>
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
                      value={gpu.power ? `${parseFloat(gpu.power).toFixed(0)}W` : "--"}
                      colorClass="text-foreground"
                    />
                  </div>
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
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ))}
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
