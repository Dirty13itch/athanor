import { z } from "zod";
import {
  type AgentInfo,
  type BackendSnapshot,
  type GpuHistoryResponse,
  type GpuSnapshot,
  type GpuSnapshotResponse,
  type ModelInventoryEntry,
  type ModelsSnapshot,
  type OverviewSnapshot,
  type ServiceHistorySeries,
  type ServiceSnapshot,
  type ServicesHistorySnapshot,
  type ServicesSnapshot,
} from "@/lib/contracts";
import {
  getFixtureAgentsSnapshot,
  getFixtureGpuHistory,
  getFixtureGpuSnapshot,
  getFixtureModelsSnapshot,
  getFixtureOverviewSnapshot,
  getFixtureServicesHistory,
  getFixtureServicesSnapshot,
  isDashboardFixtureMode,
} from "@/lib/dashboard-fixtures";
import { average } from "@/lib/format";
import { config, getNodeNameFromInstance, joinUrl, type MonitoredService } from "@/lib/config";
import { getRangeStepSeconds, getTimeWindow, type TimeWindowId } from "@/lib/ranges";

const prometheusInstantResponseSchema = z.object({
  status: z.string(),
  data: z.object({
    resultType: z.string(),
    result: z.array(
      z.object({
        metric: z.record(z.string(), z.string()),
        value: z.tuple([z.number(), z.string()]),
      })
    ),
  }),
});

const prometheusRangeResponseSchema = z.object({
  status: z.string(),
  data: z.object({
    resultType: z.string(),
    result: z.array(
      z.object({
        metric: z.record(z.string(), z.string()),
        values: z.array(z.tuple([z.number(), z.string()])),
      })
    ),
  }),
});

const backendModelsResponseSchema = z.object({
  data: z.array(
    z.object({
      id: z.string(),
    })
  ),
});

const agentsResponseSchema = z.object({
  agents: z.array(
    z.object({
      id: z.string(),
      name: z.string(),
      description: z.string(),
      icon: z.string(),
      tools: z.array(z.string()),
      status: z.enum(["ready", "unavailable"]),
    })
  ),
});

type PrometheusInstantResult = z.infer<typeof prometheusInstantResponseSchema>["data"]["result"][number];
type PrometheusRangeResult = z.infer<typeof prometheusRangeResponseSchema>["data"]["result"][number];

function nowIso() {
  return new Date().toISOString();
}

function parseNumber(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined) {
    return null;
  }

  const parsed = typeof value === "number" ? value : Number.parseFloat(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function buildHistoryPoints(values: [number, string][]) {
  return values.map(([timestamp, rawValue]) => ({
    timestamp: new Date(timestamp * 1000).toISOString(),
    value: parseNumber(rawValue),
  }));
}

async function fetchJson<T>(input: string, schema: z.ZodSchema<T>, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }

  return schema.parse(await response.json());
}

async function queryPrometheus(query: string): Promise<PrometheusInstantResult[]> {
  const url = `${config.prometheus.url}/api/v1/query?query=${encodeURIComponent(query)}`;
  const response = await fetchJson(url, prometheusInstantResponseSchema, {
    cache: "no-store",
    next: { revalidate: 15 },
  });
  return response.data.result;
}

async function queryPrometheusRange(query: string, window: TimeWindowId): Promise<PrometheusRangeResult[]> {
  const currentWindow = getTimeWindow(window);
  const end = Math.floor(Date.now() / 1000);
  const start = end - currentWindow.minutes * 60;
  const step = getRangeStepSeconds(window);
  const params = new URLSearchParams({
    query,
    start: start.toString(),
    end: end.toString(),
    step: step.toString(),
  });
  const url = `${config.prometheus.url}/api/v1/query_range?${params}`;
  const response = await fetchJson(url, prometheusRangeResponseSchema, {
    cache: "no-store",
    next: { revalidate: 15 },
  });
  return response.data.result;
}

function deriveServiceState(healthy: boolean, latencyMs: number | null): ServiceSnapshot["state"] {
  if (!healthy) {
    return "degraded";
  }

  if (latencyMs !== null && latencyMs > 1000) {
    return "warning";
  }

  return "healthy";
}

async function checkService(service: MonitoredService): Promise<ServiceSnapshot> {
  const start = Date.now();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  const checkedAt = nowIso();

  try {
    const response = await fetch(service.url, {
      signal: controller.signal,
      cache: "no-store",
    });
    const latencyMs = Date.now() - start;
    return {
      id: service.id,
      name: service.name,
      nodeId: service.nodeId,
      node: service.node,
      category: service.category,
      description: service.description,
      url: service.url,
      healthy: response.ok,
      latencyMs,
      checkedAt,
      state: deriveServiceState(response.ok, latencyMs),
    };
  } catch {
    return {
      id: service.id,
      name: service.name,
      nodeId: service.nodeId,
      node: service.node,
      category: service.category,
      description: service.description,
      url: service.url,
      healthy: false,
      latencyMs: null,
      checkedAt,
      state: "degraded",
    };
  } finally {
    clearTimeout(timeout);
  }
}

async function getBackendSnapshots(): Promise<BackendSnapshot[]> {
  return Promise.all(
    config.inferenceBackends.map(async (backend) => {
      try {
        const result = await fetchJson(joinUrl(backend.url, "/v1/models"), backendModelsResponseSchema, {
          cache: "no-store",
        });
        const models = result.data.map((entry) => entry.id);
        return {
          id: backend.id,
          name: backend.name,
          description: backend.description,
          nodeId: backend.nodeId,
          url: backend.url,
          reachable: true,
          modelCount: models.length,
          models,
        };
      } catch {
        return {
          id: backend.id,
          name: backend.name,
          description: backend.description,
          nodeId: backend.nodeId,
          url: backend.url,
          reachable: false,
          modelCount: 0,
          models: [],
        };
      }
    })
  );
}

async function getAgentInfos(): Promise<AgentInfo[]> {
  try {
    const result = await fetchJson(joinUrl(config.agentServer.url, "/v1/agents"), agentsResponseSchema, {
      cache: "no-store",
    });
    return result.agents;
  } catch {
    return [];
  }
}

function buildNodeSummaries(services: ServiceSnapshot[]) {
  return config.nodes.map((node) => {
    const nodeServices = services.filter((service) => service.nodeId === node.id);
    const healthyServices = nodeServices.filter((service) => service.healthy).length;
    const degradedServices = nodeServices.length - healthyServices;
    const averageLatencyMs = average(
      nodeServices.flatMap((service) => (service.latencyMs === null ? [] : [service.latencyMs]))
    );

    return {
      id: node.id,
      name: node.name,
      ip: node.ip,
      role: node.role,
      totalServices: nodeServices.length,
      healthyServices,
      degradedServices,
      averageLatencyMs,
      gpuUtilization: null,
    };
  });
}

interface PrometheusGpuEntry {
  id: string;
  gpuName: string;
  gpuBusId: string;
  instance: string;
  nodeId: string;
  node: string;
  utilization: number | null;
  memoryUsedMiB: number | null;
  memoryTotalMiB: number | null;
  temperatureC: number | null;
  powerW: number | null;
}

function mergeGpuMetric(
  store: Map<string, PrometheusGpuEntry>,
  result: PrometheusInstantResult,
  field: keyof Pick<
    PrometheusGpuEntry,
    "utilization" | "memoryUsedMiB" | "memoryTotalMiB" | "temperatureC" | "powerW"
  >
) {
  const instance = result.metric.instance ?? "";
  const gpuBusId = result.metric.gpu_bus_id ?? result.metric.gpu ?? result.metric.UUID ?? "";
  const id = `${instance}::${gpuBusId}`;
  const nodeName = getNodeNameFromInstance(instance);
  const node = config.nodes.find((candidate) => candidate.name === nodeName);
  const current = store.get(id) ?? {
    id,
    gpuName: result.metric.modelName ?? result.metric.gpu_name ?? "GPU",
    gpuBusId,
    instance,
    nodeId: node?.id ?? instance,
    node: nodeName,
    utilization: null,
    memoryUsedMiB: null,
    memoryTotalMiB: null,
    temperatureC: null,
    powerW: null,
  };

  current[field] = parseNumber(result.value[1]);
  store.set(id, current);
}

export async function getServicesSnapshot(): Promise<ServicesSnapshot> {
  if (isDashboardFixtureMode()) {
    return getFixtureServicesSnapshot();
  }

  const services = await Promise.all(config.services.map(checkService));
  const healthy = services.filter((service) => service.healthy).length;
  const slowestService = services
    .filter((service) => service.latencyMs !== null)
    .sort((left, right) => (right.latencyMs ?? 0) - (left.latencyMs ?? 0))[0];

  return {
    generatedAt: nowIso(),
    summary: {
      total: services.length,
      healthy,
      degraded: services.length - healthy,
      averageLatencyMs: average(
        services.flatMap((service) => (service.latencyMs === null ? [] : [service.latencyMs]))
      ),
      slowestServiceId: slowestService?.id ?? null,
      slowestServiceName: slowestService?.name ?? null,
    },
    nodes: buildNodeSummaries(services),
    services,
  };
}

export async function getServicesHistory(window: TimeWindowId): Promise<ServicesHistorySnapshot> {
  if (isDashboardFixtureMode()) {
    return getFixtureServicesHistory(window);
  }

  try {
    const [availabilitySeries, latencySeries] = await Promise.all([
      queryPrometheusRange('avg_over_time(probe_success{job="blackbox-http"}[5m])', window),
      queryPrometheusRange('avg_over_time(probe_duration_seconds{job="blackbox-http"}[5m]) * 1000', window),
    ]);

    const byService = new Map<string, ServiceHistorySeries>();

    for (const service of config.services) {
      byService.set(service.id, {
        serviceId: service.id,
        serviceName: service.name,
        nodeId: service.nodeId,
        category: service.category,
        points: [],
      });
    }

    for (const series of availabilitySeries) {
      const serviceId = series.metric.service_id;
      if (!serviceId || !byService.has(serviceId)) {
        continue;
      }

      const current = byService.get(serviceId)!;
      current.points = series.values.map(([timestamp, rawValue]) => ({
        timestamp: new Date(timestamp * 1000).toISOString(),
        availability: parseNumber(rawValue),
        latencyMs: null,
      }));
    }

    for (const series of latencySeries) {
      const serviceId = series.metric.service_id;
      if (!serviceId || !byService.has(serviceId)) {
        continue;
      }

      const current = byService.get(serviceId)!;
      const lookup = new Map(current.points.map((point) => [point.timestamp, point]));
      for (const [timestamp, rawValue] of series.values) {
        const iso = new Date(timestamp * 1000).toISOString();
        const existing = lookup.get(iso);
        if (existing) {
          existing.latencyMs = parseNumber(rawValue);
        } else {
          current.points.push({
            timestamp: iso,
            availability: null,
            latencyMs: parseNumber(rawValue),
          });
        }
      }
      current.points.sort((left, right) => left.timestamp.localeCompare(right.timestamp));
    }

    const aggregateMap = new Map<string, number[]>();
    for (const series of byService.values()) {
      for (const point of series.points) {
        if (point.availability === null) {
          continue;
        }
        const current = aggregateMap.get(point.timestamp) ?? [];
        current.push(point.availability * 100);
        aggregateMap.set(point.timestamp, current);
      }
    }

    const aggregate = Array.from(aggregateMap.entries())
      .sort((left, right) => left[0].localeCompare(right[0]))
      .map(([timestamp, values]) => ({
        timestamp,
        value: average(values),
      }));

    return {
      generatedAt: nowIso(),
      window,
      aggregate,
      series: Array.from(byService.values()),
    };
  } catch {
    return {
      generatedAt: nowIso(),
      window,
      aggregate: [],
      series: [],
    };
  }
}

export async function getGpuSnapshot(): Promise<GpuSnapshotResponse> {
  if (isDashboardFixtureMode()) {
    return getFixtureGpuSnapshot();
  }

  const [utilization, memoryUsed, memoryTotal, temperature, power] = await Promise.all([
    queryPrometheus("DCGM_FI_DEV_GPU_UTIL").catch(() => [] as PrometheusInstantResult[]),
    queryPrometheus("DCGM_FI_DEV_FB_USED").catch(() => [] as PrometheusInstantResult[]),
    queryPrometheus("DCGM_FI_DEV_FB_FREE + DCGM_FI_DEV_FB_USED").catch(
      () => [] as PrometheusInstantResult[]
    ),
    queryPrometheus("DCGM_FI_DEV_GPU_TEMP").catch(() => [] as PrometheusInstantResult[]),
    queryPrometheus("DCGM_FI_DEV_POWER_USAGE").catch(() => [] as PrometheusInstantResult[]),
  ]);

  const gpuMap = new Map<string, PrometheusGpuEntry>();

  for (const result of utilization) {
    mergeGpuMetric(gpuMap, result, "utilization");
  }
  for (const result of memoryUsed) {
    mergeGpuMetric(gpuMap, result, "memoryUsedMiB");
  }
  for (const result of memoryTotal) {
    mergeGpuMetric(gpuMap, result, "memoryTotalMiB");
  }
  for (const result of temperature) {
    mergeGpuMetric(gpuMap, result, "temperatureC");
  }
  for (const result of power) {
    mergeGpuMetric(gpuMap, result, "powerW");
  }

  const gpus: GpuSnapshot[] = Array.from(gpuMap.values()).sort((left, right) => {
    return (right.utilization ?? -1) - (left.utilization ?? -1);
  });

  const nodes = config.nodes.map((node) => {
    const nodeGpus = gpus.filter((gpu) => gpu.nodeId === node.id);
    const totalPowerW = nodeGpus.reduce((sum, gpu) => sum + (gpu.powerW ?? 0), 0);
    const totalMemoryUsedMiB = nodeGpus.reduce((sum, gpu) => sum + (gpu.memoryUsedMiB ?? 0), 0);
    const totalMemoryMiB = nodeGpus.reduce((sum, gpu) => sum + (gpu.memoryTotalMiB ?? 0), 0);
    return {
      nodeId: node.id,
      node: node.name,
      gpuCount: nodeGpus.length,
      averageUtilization: average(
        nodeGpus.flatMap((gpu) => (gpu.utilization === null ? [] : [gpu.utilization]))
      ),
      averageTemperature: average(
        nodeGpus.flatMap((gpu) => (gpu.temperatureC === null ? [] : [gpu.temperatureC]))
      ),
      totalPowerW: nodeGpus.length > 0 ? totalPowerW : null,
      totalMemoryUsedMiB: nodeGpus.length > 0 ? totalMemoryUsedMiB : null,
      totalMemoryMiB: nodeGpus.length > 0 ? totalMemoryMiB : null,
    };
  });

  return {
    generatedAt: nowIso(),
    summary: {
      gpuCount: gpus.length,
      averageUtilization: average(
        gpus.flatMap((gpu) => (gpu.utilization === null ? [] : [gpu.utilization]))
      ),
      averageTemperature: average(
        gpus.flatMap((gpu) => (gpu.temperatureC === null ? [] : [gpu.temperatureC]))
      ),
      totalPowerW: gpus.length > 0 ? gpus.reduce((sum, gpu) => sum + (gpu.powerW ?? 0), 0) : null,
      totalMemoryUsedMiB:
        gpus.length > 0 ? gpus.reduce((sum, gpu) => sum + (gpu.memoryUsedMiB ?? 0), 0) : null,
      totalMemoryMiB:
        gpus.length > 0 ? gpus.reduce((sum, gpu) => sum + (gpu.memoryTotalMiB ?? 0), 0) : null,
    },
    nodes,
    gpus,
  };
}

function groupGpuRangeSeries(results: PrometheusRangeResult[]) {
  const series = new Map<
    string,
    {
      id: string;
      label: string;
      nodeId: string;
      points: Map<string, { utilization: number | null; temperatureC: number | null; powerW: number | null; memoryRatio: number | null }>;
    }
  >();

  for (const result of results) {
    const instance = result.metric.instance ?? "";
    const gpuBusId = result.metric.gpu_bus_id ?? result.metric.gpu ?? result.metric.UUID ?? "";
    const key = `${instance}::${gpuBusId}`;
    const nodeName = getNodeNameFromInstance(instance);
    const node = config.nodes.find((candidate) => candidate.name === nodeName);
    if (!series.has(key)) {
      series.set(key, {
        id: key,
        label: (result.metric.modelName ?? result.metric.gpu_name ?? gpuBusId) || "GPU",
        nodeId: node?.id ?? nodeName,
        points: new Map(),
      });
    }
  }

  return series;
}

export async function getGpuHistory(window: TimeWindowId): Promise<GpuHistoryResponse> {
  if (isDashboardFixtureMode()) {
    return getFixtureGpuHistory(window);
  }

  const [nodeUtilization, gpuUtilization, gpuTemperature, gpuPower, gpuMemoryRatio] = await Promise.all([
    queryPrometheusRange("avg by (instance) (DCGM_FI_DEV_GPU_UTIL)", window).catch(
      () => [] as PrometheusRangeResult[]
    ),
    queryPrometheusRange("DCGM_FI_DEV_GPU_UTIL", window).catch(() => [] as PrometheusRangeResult[]),
    queryPrometheusRange("DCGM_FI_DEV_GPU_TEMP", window).catch(() => [] as PrometheusRangeResult[]),
    queryPrometheusRange("DCGM_FI_DEV_POWER_USAGE", window).catch(() => [] as PrometheusRangeResult[]),
    queryPrometheusRange(
      "100 * DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_FREE + DCGM_FI_DEV_FB_USED)",
      window
    ).catch(() => [] as PrometheusRangeResult[]),
  ]);

  const nodes = nodeUtilization.map((series) => ({
    id: series.metric.instance ?? "unknown",
    label: getNodeNameFromInstance(series.metric.instance ?? ""),
    points: buildHistoryPoints(series.values),
  }));

  const grouped = groupGpuRangeSeries([
    ...gpuUtilization,
    ...gpuTemperature,
    ...gpuPower,
    ...gpuMemoryRatio,
  ]);

  for (const series of gpuUtilization) {
    const key = `${series.metric.instance ?? ""}::${
      series.metric.gpu_bus_id ?? series.metric.gpu ?? series.metric.UUID ?? ""
    }`;
    const current = grouped.get(key);
    if (!current) {
      continue;
    }

    for (const [timestamp, rawValue] of series.values) {
      const iso = new Date(timestamp * 1000).toISOString();
      current.points.set(iso, {
        ...(current.points.get(iso) ?? {
          utilization: null,
          temperatureC: null,
          powerW: null,
          memoryRatio: null,
        }),
        utilization: parseNumber(rawValue),
      });
    }
  }

  for (const series of gpuTemperature) {
    const key = `${series.metric.instance ?? ""}::${
      series.metric.gpu_bus_id ?? series.metric.gpu ?? series.metric.UUID ?? ""
    }`;
    const current = grouped.get(key);
    if (!current) {
      continue;
    }

    for (const [timestamp, rawValue] of series.values) {
      const iso = new Date(timestamp * 1000).toISOString();
      current.points.set(iso, {
        ...(current.points.get(iso) ?? {
          utilization: null,
          temperatureC: null,
          powerW: null,
          memoryRatio: null,
        }),
        temperatureC: parseNumber(rawValue),
      });
    }
  }

  for (const series of gpuPower) {
    const key = `${series.metric.instance ?? ""}::${
      series.metric.gpu_bus_id ?? series.metric.gpu ?? series.metric.UUID ?? ""
    }`;
    const current = grouped.get(key);
    if (!current) {
      continue;
    }

    for (const [timestamp, rawValue] of series.values) {
      const iso = new Date(timestamp * 1000).toISOString();
      current.points.set(iso, {
        ...(current.points.get(iso) ?? {
          utilization: null,
          temperatureC: null,
          powerW: null,
          memoryRatio: null,
        }),
        powerW: parseNumber(rawValue),
      });
    }
  }

  for (const series of gpuMemoryRatio) {
    const key = `${series.metric.instance ?? ""}::${
      series.metric.gpu_bus_id ?? series.metric.gpu ?? series.metric.UUID ?? ""
    }`;
    const current = grouped.get(key);
    if (!current) {
      continue;
    }

    for (const [timestamp, rawValue] of series.values) {
      const iso = new Date(timestamp * 1000).toISOString();
      current.points.set(iso, {
        ...(current.points.get(iso) ?? {
          utilization: null,
          temperatureC: null,
          powerW: null,
          memoryRatio: null,
        }),
        memoryRatio: parseNumber(rawValue),
      });
    }
  }

  return {
    generatedAt: nowIso(),
    window,
    nodes,
    gpus: Array.from(grouped.values()).map((series) => ({
      id: series.id,
      label: series.label,
      nodeId: series.nodeId,
      points: Array.from(series.points.entries())
        .sort((left, right) => left[0].localeCompare(right[0]))
        .map(([timestamp, point]) => ({
          timestamp,
          utilization: point.utilization,
          temperatureC: point.temperatureC,
          powerW: point.powerW,
          memoryRatio: point.memoryRatio,
        })),
    })),
  };
}

export async function getModelsSnapshot(): Promise<ModelsSnapshot> {
  if (isDashboardFixtureMode()) {
    return getFixtureModelsSnapshot();
  }

  const backends = await getBackendSnapshots();
  const models: ModelInventoryEntry[] = backends.flatMap((backend) =>
    backend.models.map((modelId) => ({
      id: modelId,
      backendId: backend.id,
      backend: backend.name,
      target: backend.id,
      description: backend.description,
      available: backend.reachable,
    }))
  );

  return {
    generatedAt: nowIso(),
    backends,
    models,
  };
}

export async function getAgentsSnapshot() {
  if (isDashboardFixtureMode()) {
    return getFixtureAgentsSnapshot();
  }

  return {
    generatedAt: nowIso(),
    agents: await getAgentInfos(),
  };
}

function buildAlerts(
  services: ServiceSnapshot[],
  backends: BackendSnapshot[],
  agents: AgentInfo[],
  gpus: GpuSnapshot[]
) {
  const alerts: OverviewSnapshot["alerts"] = [];
  const degradedServices = services.filter((service) => !service.healthy);
  for (const service of degradedServices.slice(0, 3)) {
    alerts.push({
      id: `service-${service.id}`,
      title: service.name,
      description: `${service.node} is unreachable from the dashboard probe.`,
      tone: "degraded",
      href: `/services?service=${service.id}`,
    });
  }

  const hottest = gpus.find((gpu) => (gpu.temperatureC ?? 0) >= 75);
  if (hottest) {
    alerts.push({
      id: `gpu-${hottest.id}`,
      title: `${hottest.gpuName} is running hot`,
      description: `${hottest.node} is reporting ${Math.round(hottest.temperatureC ?? 0)}C.`,
      tone: "warning",
      href: `/gpu?highlight=${encodeURIComponent(hottest.id)}`,
    });
  }

  if (backends.every((backend) => !backend.reachable)) {
    alerts.push({
      id: "backends-offline",
      title: "Inference backends are unreachable",
      description: "Model inventory could not be discovered from either runtime.",
      tone: "degraded",
      href: "/chat",
    });
  }

  if (agents.length === 0) {
    alerts.push({
      id: "agents-unavailable",
      title: "Agent metadata unavailable",
      description: "The agent server did not return a roster for the dashboard.",
      tone: "warning",
      href: "/agents",
    });
  }

  if (alerts.length === 0) {
    alerts.push({
      id: "nominal",
      title: "Cluster nominal",
      description: "No active service incidents or GPU hotspots detected in the latest window.",
      tone: "healthy",
      href: "/services",
    });
  }

  return alerts;
}

export async function getOverviewSnapshot(window: TimeWindowId = "3h"): Promise<OverviewSnapshot> {
  if (isDashboardFixtureMode()) {
    return getFixtureOverviewSnapshot();
  }

  const [servicesSnapshot, servicesHistory, gpuSnapshot, gpuHistory, backends, agents] = await Promise.all([
    getServicesSnapshot(),
    getServicesHistory(window),
    getGpuSnapshot(),
    getGpuHistory(window),
    getBackendSnapshots(),
    getAgentInfos(),
  ]);

  const nodes = servicesSnapshot.nodes.map((node) => {
    const gpuNode = gpuSnapshot.nodes.find((gpu) => gpu.nodeId === node.id);
    return {
      ...node,
      gpuUtilization: gpuNode?.averageUtilization ?? null,
    };
  });

  const alerts = buildAlerts(servicesSnapshot.services, backends, agents, gpuSnapshot.gpus);
  const hotspots = [...gpuSnapshot.gpus].sort((left, right) => (right.utilization ?? -1) - (left.utilization ?? -1)).slice(0, 4);
  const serviceTrend = servicesHistory.aggregate;
  const gpuTrend = gpuHistory.nodes.length > 0
    ? gpuHistory.nodes[0].points.map((point, index) => ({
        timestamp: point.timestamp,
        value: average(gpuHistory.nodes.map((series) => series.points[index]?.value ?? null).filter((value): value is number => value !== null)),
      }))
    : [];

  return {
    generatedAt: nowIso(),
    summary: {
      totalServices: servicesSnapshot.summary.total,
      healthyServices: servicesSnapshot.summary.healthy,
      degradedServices: servicesSnapshot.summary.degraded,
      averageLatencyMs: servicesSnapshot.summary.averageLatencyMs,
      averageGpuUtilization: gpuSnapshot.summary.averageUtilization,
      readyAgents: agents.filter((agent) => agent.status === "ready").length,
      totalAgents: agents.length,
      reachableBackends: backends.filter((backend) => backend.reachable).length,
      totalBackends: backends.length,
    },
    nodes,
    services: servicesSnapshot.services,
    serviceTrend,
    gpuTrend,
    backends,
    agents,
    alerts,
    hotspots,
    externalTools: config.externalTools,
  };
}
