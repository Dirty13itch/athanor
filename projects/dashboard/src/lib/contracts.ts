import { z } from "zod";

export const serviceCategorySchema = z.enum([
  "inference",
  "observability",
  "media",
  "experience",
  "platform",
]);

export const statusToneSchema = z.enum(["healthy", "warning", "degraded", "muted"]);

export const chartPointSchema = z.object({
  timestamp: z.string(),
  value: z.number().nullable(),
});

export const timelinePointSchema = z.object({
  timestamp: z.string(),
  availability: z.number().min(0).max(1).nullable(),
  latencyMs: z.number().nullable(),
});

export const clusterNodeSchema = z.object({
  id: z.string(),
  name: z.string(),
  ip: z.string(),
  role: z.string(),
  totalServices: z.number().int().nonnegative(),
  healthyServices: z.number().int().nonnegative(),
  degradedServices: z.number().int().nonnegative(),
  averageLatencyMs: z.number().nullable(),
  gpuUtilization: z.number().nullable(),
});

export const serviceSnapshotSchema = z.object({
  id: z.string(),
  name: z.string(),
  nodeId: z.string(),
  node: z.string(),
  category: serviceCategorySchema,
  description: z.string(),
  url: z.string().url(),
  healthy: z.boolean(),
  latencyMs: z.number().nullable(),
  checkedAt: z.string(),
  state: statusToneSchema,
});

export const serviceHistorySeriesSchema = z.object({
  serviceId: z.string(),
  serviceName: z.string(),
  nodeId: z.string(),
  category: serviceCategorySchema,
  points: z.array(timelinePointSchema),
});

export const gpuSnapshotSchema = z.object({
  id: z.string(),
  gpuName: z.string(),
  gpuBusId: z.string(),
  instance: z.string(),
  nodeId: z.string(),
  node: z.string(),
  utilization: z.number().nullable(),
  memoryUsedMiB: z.number().nullable(),
  memoryTotalMiB: z.number().nullable(),
  temperatureC: z.number().nullable(),
  powerW: z.number().nullable(),
});

export const gpuNodeSummarySchema = z.object({
  nodeId: z.string(),
  node: z.string(),
  gpuCount: z.number().int().nonnegative(),
  averageUtilization: z.number().nullable(),
  averageTemperature: z.number().nullable(),
  totalPowerW: z.number().nullable(),
  totalMemoryUsedMiB: z.number().nullable(),
  totalMemoryMiB: z.number().nullable(),
});

export const metricSeriesSchema = z.object({
  id: z.string(),
  label: z.string(),
  points: z.array(chartPointSchema),
});

export const externalToolSchema = z.object({
  id: z.string(),
  label: z.string(),
  description: z.string(),
  url: z.string().url(),
});

export const modelInventoryEntrySchema = z.object({
  id: z.string(),
  backendId: z.string(),
  backend: z.string(),
  target: z.string(),
  description: z.string(),
  available: z.boolean(),
});

export const backendSnapshotSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  nodeId: z.string(),
  url: z.string().url(),
  reachable: z.boolean(),
  modelCount: z.number().int().nonnegative(),
  models: z.array(z.string()),
});

export const agentInfoSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  icon: z.string(),
  tools: z.array(z.string()),
  status: z.enum(["ready", "unavailable"]),
});

export const alertSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  tone: statusToneSchema,
  href: z.string(),
});

export const overviewSnapshotSchema = z.object({
  generatedAt: z.string(),
  summary: z.object({
    totalServices: z.number().int().nonnegative(),
    healthyServices: z.number().int().nonnegative(),
    degradedServices: z.number().int().nonnegative(),
    averageLatencyMs: z.number().nullable(),
    averageGpuUtilization: z.number().nullable(),
    readyAgents: z.number().int().nonnegative(),
    totalAgents: z.number().int().nonnegative(),
    reachableBackends: z.number().int().nonnegative(),
    totalBackends: z.number().int().nonnegative(),
  }),
  nodes: z.array(clusterNodeSchema),
  services: z.array(serviceSnapshotSchema),
  serviceTrend: z.array(chartPointSchema),
  gpuTrend: z.array(chartPointSchema),
  backends: z.array(backendSnapshotSchema),
  agents: z.array(agentInfoSchema),
  alerts: z.array(alertSchema),
  hotspots: z.array(gpuSnapshotSchema),
  externalTools: z.array(externalToolSchema),
});

export const servicesSnapshotSchema = z.object({
  generatedAt: z.string(),
  summary: z.object({
    total: z.number().int().nonnegative(),
    healthy: z.number().int().nonnegative(),
    degraded: z.number().int().nonnegative(),
    averageLatencyMs: z.number().nullable(),
    slowestServiceId: z.string().nullable(),
    slowestServiceName: z.string().nullable(),
  }),
  nodes: z.array(clusterNodeSchema),
  services: z.array(serviceSnapshotSchema),
});

export const servicesHistorySnapshotSchema = z.object({
  generatedAt: z.string(),
  window: z.string(),
  aggregate: z.array(chartPointSchema),
  series: z.array(serviceHistorySeriesSchema),
});

export const gpuHistorySeriesSchema = z.object({
  id: z.string(),
  label: z.string(),
  nodeId: z.string(),
  points: z.array(
    z.object({
      timestamp: z.string(),
      utilization: z.number().nullable(),
      temperatureC: z.number().nullable(),
      powerW: z.number().nullable(),
      memoryRatio: z.number().nullable(),
    })
  ),
});

export const gpuSnapshotResponseSchema = z.object({
  generatedAt: z.string(),
  summary: z.object({
    gpuCount: z.number().int().nonnegative(),
    averageUtilization: z.number().nullable(),
    averageTemperature: z.number().nullable(),
    totalPowerW: z.number().nullable(),
    totalMemoryUsedMiB: z.number().nullable(),
    totalMemoryMiB: z.number().nullable(),
  }),
  nodes: z.array(gpuNodeSummarySchema),
  gpus: z.array(gpuSnapshotSchema),
});

export const gpuHistoryResponseSchema = z.object({
  generatedAt: z.string(),
  window: z.string(),
  nodes: z.array(metricSeriesSchema),
  gpus: z.array(gpuHistorySeriesSchema),
});

export const modelsSnapshotSchema = z.object({
  generatedAt: z.string(),
  backends: z.array(backendSnapshotSchema),
  models: z.array(modelInventoryEntrySchema),
});

export const agentsSnapshotSchema = z.object({
  generatedAt: z.string(),
  agents: z.array(agentInfoSchema),
});

export const chatStreamEventSchema = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("assistant_delta"),
    timestamp: z.string(),
    content: z.string(),
  }),
  z.object({
    type: z.literal("tool_start"),
    timestamp: z.string(),
    toolCallId: z.string(),
    name: z.string(),
    args: z.record(z.string(), z.unknown()).optional(),
  }),
  z.object({
    type: z.literal("tool_end"),
    timestamp: z.string(),
    toolCallId: z.string(),
    name: z.string(),
    output: z.string().optional(),
    durationMs: z.number().optional(),
    error: z.string().optional(),
  }),
  z.object({
    type: z.literal("done"),
    timestamp: z.string(),
    finishReason: z.string().optional(),
  }),
  z.object({
    type: z.literal("error"),
    timestamp: z.string(),
    message: z.string(),
  }),
]);

export const transcriptMessageSchema = z.object({
  id: z.string(),
  role: z.enum(["user", "assistant"]),
  content: z.string(),
  createdAt: z.string(),
  toolCalls: z
    .array(
      z.object({
        id: z.string(),
        name: z.string(),
        args: z.record(z.string(), z.unknown()).optional(),
        output: z.string().optional(),
        durationMs: z.number().optional(),
        status: z.enum(["running", "done", "error"]),
      })
    )
    .optional(),
});

export const directChatSessionSchema = z.object({
  id: z.string(),
  title: z.string(),
  modelId: z.string(),
  target: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
  messages: z.array(transcriptMessageSchema),
});

export const agentThreadSchema = z.object({
  id: z.string(),
  agentId: z.string(),
  title: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
  messages: z.array(transcriptMessageSchema),
});

export const uiPreferencesSchema = z.object({
  density: z.enum(["comfortable", "compact"]).default("comfortable"),
  lastSelectedAgentId: z.string().nullable().default(null),
  lastSelectedModelKey: z.string().nullable().default(null),
  dismissedHints: z.array(z.string()).default([]),
});

export type ServiceSnapshot = z.infer<typeof serviceSnapshotSchema>;
export type ServiceHistorySeries = z.infer<typeof serviceHistorySeriesSchema>;
export type ChartPoint = z.infer<typeof chartPointSchema>;
export type GpuSnapshot = z.infer<typeof gpuSnapshotSchema>;
export type GpuNodeSummary = z.infer<typeof gpuNodeSummarySchema>;
export type OverviewSnapshot = z.infer<typeof overviewSnapshotSchema>;
export type ServicesSnapshot = z.infer<typeof servicesSnapshotSchema>;
export type ServicesHistorySnapshot = z.infer<typeof servicesHistorySnapshotSchema>;
export type GpuSnapshotResponse = z.infer<typeof gpuSnapshotResponseSchema>;
export type GpuHistoryResponse = z.infer<typeof gpuHistoryResponseSchema>;
export type BackendSnapshot = z.infer<typeof backendSnapshotSchema>;
export type ModelInventoryEntry = z.infer<typeof modelInventoryEntrySchema>;
export type ModelsSnapshot = z.infer<typeof modelsSnapshotSchema>;
export type AgentInfo = z.infer<typeof agentInfoSchema>;
export type AgentsSnapshot = z.infer<typeof agentsSnapshotSchema>;
export type ChatStreamEvent = z.infer<typeof chatStreamEventSchema>;
export type TranscriptMessage = z.infer<typeof transcriptMessageSchema>;
export type DirectChatSession = z.infer<typeof directChatSessionSchema>;
export type AgentThread = z.infer<typeof agentThreadSchema>;
export type UiPreferences = z.infer<typeof uiPreferencesSchema>;
