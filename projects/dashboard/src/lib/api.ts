import {
  agentsSnapshotSchema,
  gpuHistoryResponseSchema,
  gpuSnapshotResponseSchema,
  modelsSnapshotSchema,
  overviewSnapshotSchema,
  servicesHistorySnapshotSchema,
  servicesSnapshotSchema,
  type AgentsSnapshot,
  type GpuHistoryResponse,
  type GpuSnapshotResponse,
  type ModelsSnapshot,
  type OverviewSnapshot,
  type ServicesHistorySnapshot,
  type ServicesSnapshot,
} from "@/lib/contracts";
import { config } from "@/lib/config";
import { fetchJson } from "@/lib/http";

export interface PrometheusResult {
  metric: Record<string, string>;
  value: [number, string];
}

interface PrometheusResponse {
  status: string;
  data: {
    resultType: string;
    result: PrometheusResult[];
  };
}

export async function queryPrometheus(query: string): Promise<PrometheusResult[]> {
  const url = `${config.prometheus.url}/api/v1/query?query=${encodeURIComponent(query)}`;
  const res = await fetch(url, { next: { revalidate: 15 } });
  if (!res.ok) {
    throw new Error(`Prometheus query failed: ${res.status}`);
  }

  const data = (await res.json()) as PrometheusResponse;
  return data.data.result;
}

export async function queryPrometheusRange(
  query: string,
  start: number,
  end: number,
  step: number
): Promise<{ metric: Record<string, string>; values: [number, string][] }[]> {
  const params = new URLSearchParams({
    query,
    start: start.toString(),
    end: end.toString(),
    step: step.toString(),
  });

  const url = `${config.prometheus.url}/api/v1/query_range?${params}`;
  const res = await fetch(url, { next: { revalidate: 15 } });
  if (!res.ok) {
    throw new Error(`Prometheus range query failed: ${res.status}`);
  }

  const data = (await res.json()) as {
    data: { result: { metric: Record<string, string>; values: [number, string][] }[] };
  };
  return data.data.result;
}

export async function getOverview(): Promise<OverviewSnapshot> {
  return fetchJson("/api/overview", { cache: "no-store" }, overviewSnapshotSchema);
}

export async function getServices(): Promise<ServicesSnapshot> {
  return fetchJson("/api/services", { cache: "no-store" }, servicesSnapshotSchema);
}

export async function getServicesHistory(window: string): Promise<ServicesHistorySnapshot> {
  return fetchJson(
    `/api/services/history?window=${encodeURIComponent(window)}`,
    { cache: "no-store" },
    servicesHistorySnapshotSchema
  );
}

export async function getGpuSnapshot(): Promise<GpuSnapshotResponse> {
  return fetchJson("/api/gpu", { cache: "no-store" }, gpuSnapshotResponseSchema);
}

export async function getGpuHistory(window: string): Promise<GpuHistoryResponse> {
  return fetchJson(
    `/api/gpu/history?window=${encodeURIComponent(window)}`,
    { cache: "no-store" },
    gpuHistoryResponseSchema
  );
}

export async function getModels(): Promise<ModelsSnapshot> {
  return fetchJson("/api/models", { cache: "no-store" }, modelsSnapshotSchema);
}

export async function getAgents(): Promise<AgentsSnapshot> {
  return fetchJson("/api/agents", { cache: "no-store" }, agentsSnapshotSchema);
}
