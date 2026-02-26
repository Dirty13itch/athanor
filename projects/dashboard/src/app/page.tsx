import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { queryPrometheus, type PrometheusResult } from "@/lib/api";
import { config } from "@/lib/config";
import { GpuCard } from "@/components/gpu-card";
import { ActivityFeed, type ActivityItem } from "@/components/activity-feed";
import { UnifiedStream } from "@/components/unified-stream";
import { ProgressBar } from "@/components/progress-bar";
import { SystemPulse } from "@/components/system-pulse";
import { AgentCrewBar } from "@/components/agent-crew-bar";
import { HomeSections } from "@/components/home-sections";
import { DailyDigest } from "@/components/gen-ui/daily-digest";
import type { SectionId } from "@/lib/lens";

export const revalidate = 15;

// --- Data fetching ---

interface GpuMetric {
  gpuName: string;
  gpuIndex: number;
  instance: string;
  utilization: number;
  temperature: number;
  memoryUsed: number;
  memoryTotal: number;
  power: number;
}

async function getGpuMetrics(): Promise<GpuMetric[]> {
  const [utilization, memUsed, memTotal, temperature, power] = await Promise.all([
    queryPrometheus("DCGM_FI_DEV_GPU_UTIL").catch(() => [] as PrometheusResult[]),
    queryPrometheus("DCGM_FI_DEV_FB_USED").catch(() => [] as PrometheusResult[]),
    queryPrometheus("DCGM_FI_DEV_FB_FREE + DCGM_FI_DEV_FB_USED").catch(() => [] as PrometheusResult[]),
    queryPrometheus("DCGM_FI_DEV_GPU_TEMP").catch(() => [] as PrometheusResult[]),
    queryPrometheus("DCGM_FI_DEV_POWER_USAGE").catch(() => [] as PrometheusResult[]),
  ]);

  const gpuMap = new Map<string, GpuMetric>();

  for (const r of utilization) {
    const instance = r.metric.instance ?? "";
    const gpu = r.metric.gpu ?? r.metric.gpu_bus_id ?? "0";
    const key = `${instance}::${gpu}`;
    gpuMap.set(key, {
      gpuName: r.metric.modelName ?? r.metric.gpu_name ?? "GPU",
      gpuIndex: parseInt(r.metric.gpu ?? "0"),
      instance,
      utilization: parseFloat(r.value[1]),
      temperature: 0,
      memoryUsed: 0,
      memoryTotal: 0,
      power: 0,
    });
  }

  const find = (results: PrometheusResult[], instance: string, gpu: string) =>
    results.find(
      (r) => r.metric.instance === instance && (r.metric.gpu === gpu || r.metric.gpu_bus_id === gpu)
    )?.value[1];

  for (const [key, g] of gpuMap) {
    const [inst, gpu] = key.split("::");
    g.temperature = parseFloat(find(temperature, inst, gpu) ?? "0");
    g.memoryUsed = parseFloat(find(memUsed, inst, gpu) ?? "0");
    g.memoryTotal = parseFloat(find(memTotal, inst, gpu) ?? "0");
    g.power = parseFloat(find(power, inst, gpu) ?? "0");
  }

  return Array.from(gpuMap.values());
}


interface MediaStatus {
  plex_activity: { stream_count?: number; sessions?: { friendly_name?: string; full_title?: string; state?: string; progress_percent?: string }[] };
  sonarr_queue: { title?: string; sizeleft?: number; size?: number; status?: string }[];
  radarr_queue: { title?: string; sizeleft?: number; size?: number; status?: string }[];
  tv_library: { total?: number; episodes?: number; size_gb?: number };
  movie_library: { total?: number; has_file?: number; size_gb?: number };
  watch_history: { friendly_name?: string; full_title?: string; date?: string }[];
}

async function getMediaStatus(): Promise<MediaStatus | null> {
  try {
    const res = await fetch(`${config.agentServer.url}/v1/status/media`, {
      signal: AbortSignal.timeout(8000),
      next: { revalidate: 30 },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

interface ComfyUIStatus {
  queue_running: unknown[];
  queue_pending: unknown[];
}

async function getComfyUIQueue(): Promise<ComfyUIStatus | null> {
  try {
    const res = await fetch(`${config.comfyui.url}/queue`, {
      signal: AbortSignal.timeout(3000),
      next: { revalidate: 15 },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

interface ServiceHealth {
  name: string;
  node: string;
  status: string;
}

async function getServiceHealth(): Promise<ServiceHealth[]> {
  try {
    const res = await fetch(`${config.agentServer.url}/v1/status/services`, {
      signal: AbortSignal.timeout(8000),
      next: { revalidate: 30 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.services ?? [];
  } catch {
    return [];
  }
}

function nodeFromInstance(instance: string): string {
  if (instance.includes("192.168.1.244")) return "Foundry";
  if (instance.includes("192.168.1.225")) return "Workshop";
  return instance;
}

function getWorkload(instance: string, gpuIndex: number): string {
  const ip = instance.split(":")[0];
  return config.gpuWorkloads[ip]?.[gpuIndex] ?? "Unknown";
}

function getPowerLimit(instance: string, gpuIndex: number): number {
  const ip = instance.split(":")[0];
  return config.gpuPowerLimits[ip]?.[gpuIndex] ?? 300;
}

// --- Component ---

export default async function DashboardPage() {
  const [gpus, media, comfyQueue, services] = await Promise.all([
    getGpuMetrics(),
    getMediaStatus(),
    getComfyUIQueue(),
    getServiceHealth(),
  ]);

  // Group GPUs by node
  const gpusByNode = new Map<string, GpuMetric[]>();
  for (const gpu of gpus) {
    const node = nodeFromInstance(gpu.instance);
    const group = gpusByNode.get(node) ?? [];
    group.push(gpu);
    gpusByNode.set(node, group);
  }

  const servicesUp = services.filter((s) => s.status === "up").length;
  const servicesTotal = services.length;

  // Plex activity
  const plexSessions = media?.plex_activity?.sessions ?? [];
  const plexStreamCount = media?.plex_activity?.stream_count ?? 0;

  // Download queue
  const downloads = [
    ...(media?.sonarr_queue ?? []).map((d) => ({ ...d, source: "Sonarr" })),
    ...(media?.radarr_queue ?? []).map((d) => ({ ...d, source: "Radarr" })),
  ];

  // ComfyUI
  const comfyRunning = comfyQueue?.queue_running?.length ?? 0;
  const comfyPending = comfyQueue?.queue_pending?.length ?? 0;

  // Build activity feed from watch history + downloads
  const activityItems: ActivityItem[] = [];
  for (const w of media?.watch_history ?? []) {
    activityItems.push({
      type: "stream",
      source: "Plex",
      title: w.full_title ?? "Unknown",
      detail: `${w.friendly_name ?? "Someone"} watched`,
      timestamp: w.date ? new Date(parseInt(String(w.date)) * 1000).toISOString() : new Date().toISOString(),
      link: "/media",
    });
  }

  // Build section map for lens-driven reordering
  const sections: Record<SectionId, React.ReactNode> = {
    pulse: <SystemPulse />,
    crew: <AgentCrewBar />,
    gpus: (
      <div className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3 space-y-4">
          {Array.from(gpusByNode.entries()).map(([node, nodeGpus]) => {
            const nodeConfig = config.nodes.find((n) => n.name === node);
            return (
              <div key={node}>
                <div className="flex items-center gap-2 mb-2">
                  <h2 className="text-sm font-semibold">{node}</h2>
                  <span className="text-xs text-muted-foreground">
                    {nodeConfig?.role} — {nodeGpus.length} GPUs, {(nodeConfig?.vram ?? 0)} GB VRAM
                  </span>
                </div>
                <div className={`grid gap-2 ${nodeGpus.length > 3 ? "grid-cols-2 sm:grid-cols-3 lg:grid-cols-5" : "grid-cols-2"}`}>
                  {nodeGpus.map((gpu, i) => (
                    <GpuCard
                      key={`${gpu.instance}-${gpu.gpuIndex}-${i}`}
                      name={gpu.gpuName}
                      node={node}
                      workload={getWorkload(gpu.instance, gpu.gpuIndex)}
                      utilization={gpu.utilization}
                      temperature={gpu.temperature}
                      power={gpu.power}
                      powerLimit={getPowerLimit(gpu.instance, gpu.gpuIndex)}
                      memoryUsed={gpu.memoryUsed}
                      memoryTotal={gpu.memoryTotal}
                      compact
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    ),
    workloads: (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Inference */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Inference</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span>Qwen3-32B TP=4</span>
              <Badge variant="outline" className="text-xs">Foundry</Badge>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span>Qwen3-14B</span>
              <Badge variant="outline" className="text-xs">Workshop</Badge>
            </div>
          </CardContent>
        </Card>

        {/* Creative */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Creative</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between text-xs">
              <span>ComfyUI (Flux dev)</span>
              {comfyRunning > 0 ? (
                <Badge className="text-xs">{comfyRunning} generating</Badge>
              ) : comfyPending > 0 ? (
                <Badge variant="outline" className="text-xs">{comfyPending} queued</Badge>
              ) : comfyQueue ? (
                <span className="text-muted-foreground">Idle</span>
              ) : (
                <Badge variant="destructive" className="text-xs">Offline</Badge>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Media */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Media</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span>Plex</span>
              {plexStreamCount > 0 ? (
                <span className="text-green-400">{plexStreamCount} stream{plexStreamCount > 1 ? "s" : ""}</span>
              ) : (
                <span className="text-muted-foreground">No streams</span>
              )}
            </div>
            {plexSessions.map((s, i) => (
              <div key={i} className="text-xs text-muted-foreground ml-2">
                {s.friendly_name}: {s.full_title} ({s.progress_percent}%)
              </div>
            ))}
            {downloads.length > 0 ? (
              <div className="space-y-1">
                {downloads.slice(0, 3).map((d, i) => {
                  const pct = d.size ? ((d.size - (d.sizeleft ?? 0)) / d.size) * 100 : 0;
                  return (
                    <div key={i} className="text-xs">
                      <div className="flex justify-between">
                        <span className="truncate max-w-[180px]">{d.title}</span>
                        <span className="text-muted-foreground">{pct.toFixed(0)}%</span>
                      </div>
                      <ProgressBar value={pct} className="mt-0.5" />
                    </div>
                  );
                })}
                {downloads.length > 3 && (
                  <p className="text-xs text-muted-foreground">+{downloads.length - 3} more</p>
                )}
              </div>
            ) : media ? (
              <p className="text-xs text-muted-foreground">No active downloads</p>
            ) : null}
          </CardContent>
        </Card>

        {/* Services summary */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Services</CardTitle>
            <CardDescription>{servicesUp}/{servicesTotal} online</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-1">
              {services.map((s) => (
                <div
                  key={s.name}
                  className="flex items-center gap-1 text-xs"
                  title={`${s.name} (${s.node})`}
                >
                  <div className={`h-1.5 w-1.5 rounded-full ${s.status === "up" ? "bg-green-500" : "bg-red-500"}`} />
                  <span className="text-muted-foreground">{s.name.split("(")[0].trim()}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    ),
    stream: (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Activity Stream</CardTitle>
        </CardHeader>
        <CardContent>
          <UnifiedStream limit={10} />
        </CardContent>
      </Card>
    ),
    watches: activityItems.length > 0 ? (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Recent Watches</CardTitle>
        </CardHeader>
        <CardContent>
          <ActivityFeed items={activityItems.slice(0, 5)} />
        </CardContent>
      </Card>
    ) : null,
    links: (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Quick Links</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            <a
              href="/chat"
              className="rounded-md border border-border px-3 py-1.5 text-xs font-medium hover:bg-accent transition-colors"
            >
              Chat with Agent
            </a>
            {config.quickLinks.map((link) => (
              <a
                key={link.name}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent transition-colors"
              >
                {link.name}
              </a>
            ))}
          </div>
        </CardContent>
      </Card>
    ),
    digest: <DailyDigest />,
  };

  return <HomeSections sections={sections} />;
}
