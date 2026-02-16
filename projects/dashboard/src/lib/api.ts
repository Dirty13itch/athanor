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

// --- vLLM Chat ---

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface ChatCompletionResponse {
  id: string;
  choices: {
    index: number;
    message: ChatMessage;
    finish_reason: string;
  }[];
  model: string;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export async function chatCompletion(
  messages: ChatMessage[],
  model?: string
): Promise<ChatCompletionResponse> {
  const url = `${config.vllm.url}${config.vllm.chatEndpoint}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: model ?? "default",
      messages,
      max_tokens: 2048,
      temperature: 0.7,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`vLLM chat failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function streamChatCompletion(
  messages: ChatMessage[],
  model?: string
): Promise<ReadableStream<Uint8Array>> {
  const url = `${config.vllm.url}${config.vllm.chatEndpoint}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: model ?? "default",
      messages,
      max_tokens: 2048,
      temperature: 0.7,
      stream: true,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`vLLM stream failed (${res.status}): ${text}`);
  }
  return res.body!;
}

export async function getModels(): Promise<string[]> {
  const url = `${config.vllm.url}${config.vllm.modelsEndpoint}`;
  const res = await fetch(url, { next: { revalidate: 60 } });
  if (!res.ok) return [];
  const data = await res.json();
  return data.data?.map((m: { id: string }) => m.id) ?? [];
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
