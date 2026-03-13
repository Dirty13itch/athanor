import {
  agentsSnapshotSchema,
  executionRunsResponseSchema,
  gallerySnapshotSchema,
  governorResponseSchema,
  gpuHistoryResponseSchema,
  gpuSnapshotResponseSchema,
  historySnapshotSchema,
  homeSnapshotSchema,
  intelligenceSnapshotSchema,
  mediaSnapshotSchema,
  memorySnapshotSchema,
  modelGovernanceSnapshotSchema,
  modelsSnapshotSchema,
  monitoringSnapshotSchema,
  operatorTestsSnapshotSchema,
  operatorStreamResponseSchema,
  operationsReadinessSnapshotSchema,
  overviewSnapshotSchema,
  judgePlaneResponseSchema,
  scheduledJobsResponseSchema,
  servicesHistorySnapshotSchema,
  servicesSnapshotSchema,
  subscriptionSummaryResponseSchema,
  systemMapSnapshotSchema,
  workforceSnapshotResponseSchema,
  type AgentsSnapshot,
  type ExecutionRunsResponse,
  type GallerySnapshot,
  type GovernorSnapshot,
  type GpuHistoryResponse,
  type GpuSnapshotResponse,
  type HistorySnapshot,
  type HomeSnapshot,
  type IntelligenceSnapshot,
  type MediaSnapshot,
  type MemorySnapshot,
  type ModelGovernanceSnapshot,
  type ModelsSnapshot,
  type MonitoringSnapshot,
  type OperatorTestsSnapshot,
  type OperatorStreamResponse,
  type OperationsReadinessSnapshot,
  type OverviewSnapshot,
  type JudgePlaneSnapshot,
  type ScheduledJobsResponse,
  type ServicesHistorySnapshot,
  type ServicesSnapshot,
  type SubscriptionSummaryResponse,
  type SystemMapSnapshot,
  type WorkforceSnapshot,
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

export async function getModelGovernance(): Promise<ModelGovernanceSnapshot> {
  return fetchJson("/api/models/governance", { cache: "no-store" }, modelGovernanceSnapshotSchema);
}

export async function getAgents(): Promise<AgentsSnapshot> {
  return fetchJson("/api/agents", { cache: "no-store" }, agentsSnapshotSchema);
}

export async function getSystemMap(): Promise<SystemMapSnapshot> {
  return fetchJson("/api/system-map", { cache: "no-store" }, systemMapSnapshotSchema);
}

export async function getGovernor(): Promise<GovernorSnapshot> {
  return fetchJson("/api/governor", { cache: "no-store" }, governorResponseSchema);
}

export async function getOperationsReadiness(): Promise<OperationsReadinessSnapshot> {
  return fetchJson(
    "/api/governor/operations",
    { cache: "no-store" },
    operationsReadinessSnapshotSchema
  );
}

export async function getOperatorTests(): Promise<OperatorTestsSnapshot> {
  return fetchJson(
    "/api/governor/operator-tests",
    { cache: "no-store" },
    operatorTestsSnapshotSchema
  );
}

export async function getWorkforce(): Promise<WorkforceSnapshot> {
  return fetchJson("/api/workforce", { cache: "no-store" }, workforceSnapshotResponseSchema);
}

export async function getOperatorStream(limit = 12): Promise<OperatorStreamResponse> {
  return fetchJson(
    `/api/activity/operator-stream?limit=${encodeURIComponent(String(limit))}`,
    { cache: "no-store" },
    operatorStreamResponseSchema
  );
}

export async function getExecutionRuns(limit = 25): Promise<ExecutionRunsResponse> {
  return fetchJson(
    `/api/workforce/runs?limit=${encodeURIComponent(String(limit))}`,
    { cache: "no-store" },
    executionRunsResponseSchema
  );
}

export async function getScheduledJobs(limit = 25): Promise<ScheduledJobsResponse> {
  return fetchJson(
    `/api/workforce/scheduled?limit=${encodeURIComponent(String(limit))}`,
    { cache: "no-store" },
    scheduledJobsResponseSchema
  );
}

export async function getSubscriptionSummary(limit = 10): Promise<SubscriptionSummaryResponse> {
  return fetchJson(
    `/api/subscriptions/summary?limit=${encodeURIComponent(String(limit))}`,
    { cache: "no-store" },
    subscriptionSummaryResponseSchema
  );
}

export async function getHistory(): Promise<HistorySnapshot> {
  return fetchJson("/api/history", { cache: "no-store" }, historySnapshotSchema);
}

export async function getIntelligence(): Promise<IntelligenceSnapshot> {
  return fetchJson("/api/intelligence", { cache: "no-store" }, intelligenceSnapshotSchema);
}

export async function getJudgePlane(limit = 12): Promise<JudgePlaneSnapshot> {
  return fetchJson(
    `/api/review/judges?limit=${encodeURIComponent(String(limit))}`,
    { cache: "no-store" },
    judgePlaneResponseSchema
  );
}

export async function getMemory(): Promise<MemorySnapshot> {
  return fetchJson("/api/memory", { cache: "no-store" }, memorySnapshotSchema);
}

export async function getMonitoring(): Promise<MonitoringSnapshot> {
  return fetchJson("/api/monitoring", { cache: "no-store" }, monitoringSnapshotSchema);
}

export async function getMediaOverview(): Promise<MediaSnapshot> {
  return fetchJson("/api/media/overview", { cache: "no-store" }, mediaSnapshotSchema);
}

export async function getGalleryOverview(): Promise<GallerySnapshot> {
  return fetchJson("/api/gallery/overview", { cache: "no-store" }, gallerySnapshotSchema);
}

export async function getHomeOverview(): Promise<HomeSnapshot> {
  return fetchJson("/api/home/overview", { cache: "no-store" }, homeSnapshotSchema);
}
