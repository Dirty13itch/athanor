import { config } from "./config";

// --- Prometheus ---

export interface PrometheusResult {
  metric: Record<string, string>;
  value: [number, string];
}

export interface PrometheusResponse {
  status: string;
  data: {
    resultType: string;
    result: PrometheusResult[];
  };
}

export async function queryPrometheus(query: string): Promise<PrometheusResult[]> {
  const url = `${config.prometheus.url}/api/v1/query?query=${encodeURIComponent(query)}`;
  const res = await fetch(url, { next: { revalidate: 15 } });
  if (!res.ok) throw new Error(`Prometheus query failed: ${res.status}`);
  const data: PrometheusResponse = await res.json();
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
  if (!res.ok) throw new Error(`Prometheus range query failed: ${res.status}`);
  const data = await res.json();
  return data.data.result;
}

// --- Chat ---
// Chat completion and model listing are now handled by API routes:
//   /api/chat    — proxies to selected backend with streaming
//   /api/models  — aggregates models from all inference backends

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

// --- Service Health ---

export interface ServiceStatus {
  name: string;
  node: string;
  url: string;
  healthy: boolean;
  latencyMs: number | null;
}

export async function checkServiceHealth(
  service: { name: string; url: string; node: string }
): Promise<ServiceStatus> {
  const start = Date.now();
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    const res = await fetch(service.url, {
      signal: controller.signal,
      next: { revalidate: 0 },
    });
    clearTimeout(timeout);
    return {
      ...service,
      healthy: res.ok,
      latencyMs: Date.now() - start,
    };
  } catch {
    return {
      ...service,
      healthy: false,
      latencyMs: null,
    };
  }
}

export async function checkAllServices(): Promise<ServiceStatus[]> {
  return Promise.all(config.services.map(checkServiceHealth));
}
