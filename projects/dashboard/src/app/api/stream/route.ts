import { queryPrometheus, type PrometheusResult } from "@/lib/api";
import { agentServerHeaders, config, getNodeNameFromInstance } from "@/lib/config";

export const dynamic = "force-dynamic";

interface StreamPayload {
  gpus: {
    index: number;
    name: string;
    node: string;
    utilization: number;
    temperature: number;
    memUsedGB: number;
    memTotalGB: number;
    power: number;
    workload: string;
  }[];
  agents: { online: boolean; count: number; names: string[] };
  services: { up: number; total: number; down: string[] };
  tasks: Record<string, unknown> | null;
  notifications: { pending: number; total: number };
  timestamp: string;
}

async function fetchSnapshot(): Promise<StreamPayload> {
  // GPU metrics
  const [utilization, memUsed, memTotal, temperature, power] = await Promise.all([
    queryPrometheus("DCGM_FI_DEV_GPU_UTIL").catch(() => [] as PrometheusResult[]),
    queryPrometheus("DCGM_FI_DEV_FB_USED").catch(() => [] as PrometheusResult[]),
    queryPrometheus("DCGM_FI_DEV_FB_FREE + DCGM_FI_DEV_FB_USED").catch(() => [] as PrometheusResult[]),
    queryPrometheus("DCGM_FI_DEV_GPU_TEMP").catch(() => [] as PrometheusResult[]),
    queryPrometheus("DCGM_FI_DEV_POWER_USAGE").catch(() => [] as PrometheusResult[]),
  ]);

  const gpuMap = new Map<string, StreamPayload["gpus"][0]>();
  for (const r of utilization) {
    const instance = r.metric.instance ?? "";
    const gpuIdx = parseInt(r.metric.gpu ?? "0");
    const key = `${instance}::${gpuIdx}`;
    const ip = instance.split(":")[0];
    gpuMap.set(key, {
      index: gpuIdx,
      name: r.metric.modelName ?? r.metric.gpu_name ?? "GPU",
      node: getNodeNameFromInstance(instance),
      utilization: parseFloat(r.value[1]),
      temperature: 0,
      memUsedGB: 0,
      memTotalGB: 0,
      power: 0,
      workload: config.gpuWorkloads[ip]?.[gpuIdx] ?? "Unknown",
    });
  }

  const find = (results: PrometheusResult[], instance: string, gpu: string) =>
    results.find(
      (r) => r.metric.instance === instance && (r.metric.gpu === gpu || r.metric.gpu_bus_id === gpu)
    )?.value[1];

  for (const [key, g] of gpuMap) {
    const [inst, gpu] = key.split("::");
    g.temperature = parseFloat(find(temperature, inst, gpu) ?? "0");
    g.memUsedGB = parseFloat(find(memUsed, inst, gpu) ?? "0") / 1024;
    g.memTotalGB = parseFloat(find(memTotal, inst, gpu) ?? "0") / 1024;
    g.power = parseFloat(find(power, inst, gpu) ?? "0");
  }

  // Agent status
  let agents: StreamPayload["agents"] = { online: false, count: 0, names: [] };
  try {
    const res = await fetch(`${config.agentServer.url}/health`, {
      signal: AbortSignal.timeout(3000),
    });
    if (res.ok) {
      const data = await res.json();
      agents = { online: true, count: data.agents?.length ?? 0, names: data.agents ?? [] };
    }
  } catch { /* agent server down */ }

  // Service health
  let services: StreamPayload["services"] = { up: 0, total: 0, down: [] };
  try {
    const res = await fetch(`${config.agentServer.url}/v1/status/services`, {
      signal: AbortSignal.timeout(5000),
      headers: agentServerHeaders(),
    });
    if (res.ok) {
      const data = await res.json();
      const svcList = data.services ?? [];
      const downList = svcList.filter((s: { status: string }) => s.status !== "up");
      services = {
        up: svcList.length - downList.length,
        total: svcList.length,
        down: downList.map((s: { name: string }) => s.name),
      };
    }
  } catch { /* service check failed */ }

  // Task stats
  let tasks: StreamPayload["tasks"] = null;
  try {
    const res = await fetch(`${config.agentServer.url}/v1/tasks/stats`, {
      signal: AbortSignal.timeout(3000),
      headers: agentServerHeaders(),
    });
    if (res.ok) {
      tasks = await res.json();
    }
  } catch { /* task stats unavailable */ }

  // Workforce notification summary
  let notifications: StreamPayload["notifications"] = { pending: 0, total: 0 };
  try {
    const res = await fetch(`${config.agentServer.url}/v1/notifications?include_resolved=true`, {
      signal: AbortSignal.timeout(3000),
      headers: agentServerHeaders(),
    });
    if (res.ok) {
      const data = await res.json();
      notifications = {
        pending: typeof data.unread === "number" ? data.unread : 0,
        total: typeof data.count === "number" ? data.count : 0,
      };
    }
  } catch { /* notification summary unavailable */ }

  return {
    gpus: Array.from(gpuMap.values()),
    agents,
    services,
    tasks,
    notifications,
    timestamp: new Date().toISOString(),
  };
}

export async function GET() {
  const encoder = new TextEncoder();
  let cancelled = false;

  const stream = new ReadableStream({
    async start(controller) {
      // Send initial snapshot immediately
      try {
        const snapshot = await fetchSnapshot();
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(snapshot)}\n\n`));
      } catch {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ error: "fetch failed" })}\n\n`));
      }

      // Then push updates every 5 seconds
      const interval = setInterval(async () => {
        if (cancelled) {
          clearInterval(interval);
          return;
        }
        try {
          const snapshot = await fetchSnapshot();
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(snapshot)}\n\n`));
        } catch {
          // Skip this tick on error
        }
      }, 5000);

      // Clean up after 5 minutes to prevent resource leaks
      setTimeout(() => {
        cancelled = true;
        clearInterval(interval);
        try {
          controller.close();
        } catch { /* already closed */ }
      }, 5 * 60 * 1000);
    },
    cancel() {
      cancelled = true;
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
