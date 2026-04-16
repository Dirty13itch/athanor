// Tool result parsers for generative UI rendering

export type ToolRendererType = "gpu" | "services" | "task" | "code" | "generic";

export function getToolRenderer(toolName: string): ToolRendererType {
  const name = toolName.toLowerCase();
  if (name.includes("gpu") || name.includes("vram") || name.includes("dcgm")) return "gpu";
  if (name.includes("service") || name.includes("health") || name.includes("check")) return "services";
  if (name.includes("task") || name.includes("delegate") || name.includes("submit")) return "task";
  if (name.includes("code") || name.includes("read_file") || name.includes("write_file") || name.includes("run_command")) return "code";
  return "generic";
}

export interface GpuMetricParsed {
  label: string;
  value: number;
}

export function parseGpuMetrics(text: string): GpuMetricParsed[] | null {
  const results: GpuMetricParsed[] = [];
  // Match lines like "GPU 0 (RTX 5070 Ti): 12% util" or "RTX 5070 Ti: 12%"
  const gpuPattern = /GPU\s*(\d+)[^:]*:\s*(\d+)%/gi;
  const modelPattern = /((?:RTX|GTX|Arc)\s+[\w\s]+?):\s*(\d+)%/gi;
  const utilPattern = /utilization[:\s]+(\d+)%/gi;

  let match;
  while ((match = gpuPattern.exec(text)) !== null) {
    results.push({ label: `GPU ${match[1]}`, value: parseInt(match[2]) });
  }
  if (results.length > 0) return results;

  while ((match = modelPattern.exec(text)) !== null) {
    results.push({ label: match[1].trim(), value: parseInt(match[2]) });
  }
  if (results.length > 0) return results;

  while ((match = utilPattern.exec(text)) !== null) {
    results.push({ label: "GPU", value: parseInt(match[1]) });
  }

  return results.length > 0 ? results : null;
}

export interface ServiceHealthParsed {
  name: string;
  status: "up" | "down";
  node?: string;
}

export function parseServiceHealth(text: string): ServiceHealthParsed[] | null {
  const results: ServiceHealthParsed[] = [];
  const lines = text.split("\n");
  for (const line of lines) {
    const match = line.match(/[✅❌•\-\s]*([^(:—\n]+?)(?:\s*\(([^)]+)\))?\s*[—:\-]+\s*(up|down|online|offline|ok|error|unreachable)/i);
    if (match) {
      const status = ["up", "online", "ok"].includes(match[3].toLowerCase()) ? "up" as const : "down" as const;
      results.push({ name: match[1].trim(), status, node: match[2]?.trim() });
    }
  }
  return results.length > 0 ? results : null;
}

export interface TaskStatusParsed {
  id?: string;
  agent?: string;
  status: string;
  description?: string;
}

export function parseTaskStatus(text: string): TaskStatusParsed | null {
  const idMatch = text.match(/[Tt]ask\s+(?:created|submitted|id)?[:\s]+([a-f0-9-]+)/i)
    ?? text.match(/task[:\s]+([a-f0-9-]+)/i);
  const agentMatch = text.match(/(?:agent|delegated to)[:\s]+([a-z-]+)/i);
  const statusMatch = text.match(/status[:\s]+(completed|running|failed|pending|queued)/i);

  if (!idMatch && !statusMatch) return null;

  return {
    id: idMatch?.[1],
    agent: agentMatch?.[1],
    status: statusMatch?.[1] ?? "submitted",
    description: text.split("\n")[0].substring(0, 100),
  };
}
