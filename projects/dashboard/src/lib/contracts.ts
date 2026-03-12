import { z } from "zod";

export const serviceCategorySchema = z.enum([
  "inference",
  "observability",
  "media",
  "experience",
  "platform",
  "knowledge",
  "home",
]);

export const statusToneSchema = z.enum(["healthy", "warning", "degraded", "muted"]);
export const taskPrioritySchema = z.enum(["critical", "high", "normal", "low"]);
export const taskStatusSchema = z.enum([
  "pending",
  "pending_approval",
  "running",
  "completed",
  "failed",
  "cancelled",
]);

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

export const projectSnapshotSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  headline: z.string(),
  status: z.string(),
  kind: z.enum(["core", "tenant", "domain", "scaffold"]),
  firstClass: z.boolean(),
  lens: z.string(),
  primaryRoute: z.string(),
  externalUrl: z.string().url().nullable(),
  agents: z.array(z.string()),
  needsCount: z.number().int().nonnegative(),
  constraints: z.array(z.string()),
  operatorChain: z.array(z.string()),
});

export const workforceTaskSchema = z.object({
  id: z.string(),
  agentId: z.string(),
  prompt: z.string(),
  priority: taskPrioritySchema,
  status: taskStatusSchema,
  createdAt: z.string(),
  startedAt: z.string().nullable(),
  completedAt: z.string().nullable(),
  durationMs: z.number().int().nullable(),
  requiresApproval: z.boolean(),
  source: z.string().nullable(),
  projectId: z.string().nullable(),
  planId: z.string().nullable(),
  rationale: z.string().nullable(),
  parentTaskId: z.string().nullable(),
  result: z.string().nullable(),
  error: z.string().nullable(),
  stepCount: z.number().int().nonnegative(),
});

export const workplanTaskSchema = z.object({
  taskId: z.string().nullable(),
  agentId: z.string(),
  projectId: z.string().nullable(),
  prompt: z.string(),
  priority: taskPrioritySchema,
  rationale: z.string().nullable(),
  requiresApproval: z.boolean(),
});

export const workplanSnapshotSchema = z.object({
  planId: z.string(),
  generatedAt: z.string(),
  timeContext: z.string().nullable(),
  focus: z.string(),
  taskCount: z.number().int().nonnegative(),
  tasks: z.array(workplanTaskSchema),
  error: z.string().nullable().optional(),
});

export const workforceGoalSchema = z.object({
  id: z.string(),
  text: z.string(),
  agentId: z.string(),
  priority: z.enum(["low", "normal", "high"]),
  createdAt: z.string(),
  active: z.boolean(),
});

export const workforceNotificationSchema = z.object({
  id: z.string(),
  agentId: z.string(),
  action: z.string(),
  category: z.string(),
  confidence: z.number().min(0).max(1),
  description: z.string(),
  tier: z.enum(["act", "notify", "ask"]),
  createdAt: z.string(),
  resolved: z.boolean(),
  resolution: z.string().nullable(),
});

export const workforceTrustEntrySchema = z.object({
  agentId: z.string(),
  trustScore: z.number(),
  trustGrade: z.string().nullable(),
  positiveFeedback: z.number().int().nonnegative(),
  negativeFeedback: z.number().int().nonnegative(),
  totalFeedback: z.number().int().nonnegative(),
  escalationCount: z.number().int().nonnegative(),
});

export const workspaceItemSnapshotSchema = z.object({
  id: z.string(),
  sourceAgent: z.string(),
  content: z.string(),
  priority: taskPrioritySchema,
  salience: z.number(),
  createdAt: z.string(),
  ttlSeconds: z.number().int().positive(),
  coalition: z.array(z.string()),
  projectId: z.string().nullable(),
});

export const workspaceSnapshotSchema = z.object({
  totalItems: z.number().int().nonnegative(),
  broadcastItems: z.number().int().nonnegative(),
  capacity: z.number().int().positive(),
  utilization: z.number().min(0).nullable(),
  competitionRunning: z.boolean(),
  agentsActive: z.array(
    z.object({
      agentId: z.string(),
      count: z.number().int().nonnegative(),
    })
  ),
  topItem: workspaceItemSnapshotSchema.nullable(),
  broadcast: z.array(workspaceItemSnapshotSchema),
});

export const workspaceSubscriptionSchema = z.object({
  agentId: z.string(),
  keywords: z.array(z.string()),
  sourceFilters: z.array(z.string()),
  threshold: z.number(),
  reactPromptTemplate: z.string(),
});

export const workforceAgentSnapshotSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  icon: z.string(),
  type: z.string(),
  status: z.enum(["ready", "unavailable"]),
  tools: z.array(z.string()),
  totalTasks: z.number().int().nonnegative(),
  runningTasks: z.number().int().nonnegative(),
  pendingTasks: z.number().int().nonnegative(),
  trustScore: z.number().nullable(),
  trustGrade: z.string().nullable(),
});

export const workplanScheduleSchema = z.object({
  morningRunHourLocal: z.number().int().nonnegative(),
  morningRunMinuteLocal: z.number().int().nonnegative(),
  refillIntervalHours: z.number().positive(),
  minPendingTasks: z.number().int().nonnegative(),
  nextRunAt: z.string(),
});

export const workforceScheduleEntrySchema = z.object({
  agentId: z.string(),
  intervalSeconds: z.number().int().nonnegative(),
  intervalHuman: z.string(),
  enabled: z.boolean(),
  lastRunAt: z.string().nullable(),
  nextRunInSeconds: z.number().int().nonnegative(),
  priority: z.string(),
});

export const projectPostureSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.string(),
  firstClass: z.boolean(),
  lens: z.string(),
  primaryRoute: z.string(),
  externalUrl: z.string().url().nullable(),
  needsCount: z.number().int().nonnegative(),
  mappedAgents: z.number().int().nonnegative(),
  totalTasks: z.number().int().nonnegative(),
  pendingTasks: z.number().int().nonnegative(),
  pendingApprovals: z.number().int().nonnegative(),
  runningTasks: z.number().int().nonnegative(),
  completedTasks: z.number().int().nonnegative(),
  failedTasks: z.number().int().nonnegative(),
  plannedTasks: z.number().int().nonnegative(),
  operatorChain: z.array(z.string()),
  topAgents: z.array(z.string()),
});

export const workforceConventionSchema = z.object({
  id: z.string(),
  type: z.string(),
  agentId: z.string(),
  description: z.string(),
  rule: z.string(),
  source: z.string(),
  occurrences: z.number().int().nonnegative(),
  status: z.string(),
  createdAt: z.string(),
  confirmedAt: z.string().nullable(),
});

export const workforceImprovementSummarySchema = z.object({
  totalProposals: z.number().int().nonnegative(),
  pending: z.number().int().nonnegative(),
  validated: z.number().int().nonnegative(),
  deployed: z.number().int().nonnegative(),
  failed: z.number().int().nonnegative(),
  benchmarkResults: z.number().int().nonnegative(),
  lastCycle: z
    .object({
      timestamp: z.string(),
      patternsConsumed: z.number().int().nonnegative(),
      proposalsGenerated: z.number().int().nonnegative(),
      benchmarks: z
        .object({
          passed: z.number().int().nonnegative(),
          total: z.number().int().nonnegative(),
          passRate: z.number(),
        })
        .nullable(),
    })
    .nullable(),
});

export const workforceSnapshotSchema = z.object({
  generatedAt: z.string(),
  summary: z.object({
    totalTasks: z.number().int().nonnegative(),
    pendingTasks: z.number().int().nonnegative(),
    pendingApprovals: z.number().int().nonnegative(),
    runningTasks: z.number().int().nonnegative(),
    completedTasks: z.number().int().nonnegative(),
    failedTasks: z.number().int().nonnegative(),
    activeGoals: z.number().int().nonnegative(),
    unreadNotifications: z.number().int().nonnegative(),
    avgTrustScore: z.number().nullable(),
    workspaceUtilization: z.number().nullable(),
    activeProjects: z.number().int().nonnegative(),
    queuedProjects: z.number().int().nonnegative(),
  }),
  workplan: z.object({
    current: workplanSnapshotSchema.nullable(),
    history: z.array(workplanSnapshotSchema),
    needsRefill: z.boolean(),
    schedule: workplanScheduleSchema,
  }),
  tasks: z.array(workforceTaskSchema),
  goals: z.array(workforceGoalSchema),
  trust: z.array(workforceTrustEntrySchema),
  notifications: z.array(workforceNotificationSchema),
  workspace: workspaceSnapshotSchema,
  subscriptions: z.array(workspaceSubscriptionSchema),
  conventions: z.object({
    proposed: z.array(workforceConventionSchema),
    confirmed: z.array(workforceConventionSchema),
  }),
  improvement: workforceImprovementSummarySchema.nullable(),
  agents: z.array(workforceAgentSnapshotSchema),
  projects: z.array(projectPostureSchema),
  schedules: z.array(workforceScheduleEntrySchema),
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
    activeProjects: z.number().int().nonnegative(),
    firstClassProjects: z.number().int().nonnegative(),
  }),
  nodes: z.array(clusterNodeSchema),
  services: z.array(serviceSnapshotSchema),
  serviceTrend: z.array(chartPointSchema),
  gpuTrend: z.array(chartPointSchema),
  backends: z.array(backendSnapshotSchema),
  agents: z.array(agentInfoSchema),
  projects: z.array(projectSnapshotSchema),
  alerts: z.array(alertSchema),
  hotspots: z.array(gpuSnapshotSchema),
  externalTools: z.array(externalToolSchema),
  workforce: workforceSnapshotSchema,
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

export const projectsSnapshotSchema = z.object({
  generatedAt: z.string(),
  projects: z.array(projectSnapshotSchema),
});

export const workforceSnapshotResponseSchema = workforceSnapshotSchema;

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

export const historyActivityItemSchema = z.object({
  id: z.string(),
  agentId: z.string(),
  projectId: z.string().nullable(),
  actionType: z.string(),
  inputSummary: z.string(),
  outputSummary: z.string().nullable(),
  toolsUsed: z.array(z.string()),
  durationMs: z.number().nullable(),
  timestamp: z.string(),
  relatedTaskId: z.string().nullable(),
  relatedThreadId: z.string().nullable(),
  reviewTaskId: z.string().nullable(),
  status: taskStatusSchema.nullable(),
  href: z.string(),
});

export const historyConversationItemSchema = z.object({
  id: z.string(),
  threadId: z.string(),
  agentId: z.string(),
  projectId: z.string().nullable(),
  userMessage: z.string(),
  assistantResponse: z.string().nullable(),
  toolsUsed: z.array(z.string()),
  durationMs: z.number().nullable(),
  timestamp: z.string(),
  relatedTaskId: z.string().nullable(),
  href: z.string(),
});

export const historyOutputItemSchema = z.object({
  id: z.string(),
  path: z.string(),
  fileName: z.string(),
  category: z.string(),
  sizeBytes: z.number().int().nonnegative(),
  modifiedAt: z.string(),
  projectId: z.string().nullable(),
  relatedTaskId: z.string().nullable(),
  previewAvailable: z.boolean(),
  href: z.string(),
});

export const historySnapshotSchema = z.object({
  generatedAt: z.string(),
  summary: z.object({
    activityCount: z.number().int().nonnegative(),
    conversationCount: z.number().int().nonnegative(),
    outputCount: z.number().int().nonnegative(),
    reviewCount: z.number().int().nonnegative(),
  }),
  projects: z.array(projectSnapshotSchema),
  agents: z.array(workforceAgentSnapshotSchema),
  tasks: z.array(workforceTaskSchema),
  activity: z.array(historyActivityItemSchema),
  conversations: z.array(historyConversationItemSchema),
  outputs: z.array(historyOutputItemSchema),
});

export const intelligencePatternSchema = z.object({
  type: z.string(),
  severity: z.enum(["high", "medium", "low"]).catch("low"),
  agentId: z.string().nullable().optional(),
  count: z.number().nullable().optional(),
  sampleErrors: z.array(z.string()).default([]),
  thumbsUp: z.number().nullable().optional(),
  thumbsDown: z.number().nullable().optional(),
  topics: z.record(z.string(), z.number()).default({}),
  dominantType: z.string().nullable().optional(),
  actions: z.record(z.string(), z.number()).default({}),
});

export const intelligenceAutonomyAdjustmentSchema = z.object({
  agentId: z.string(),
  category: z.string(),
  previous: z.number(),
  delta: z.number(),
  next: z.number(),
});

export const intelligenceAgentBehaviorSchema = z.object({
  agentId: z.string(),
  dominantTopic: z.string().nullable(),
  dominantType: z.string().nullable(),
  entityCount: z.number().nullable(),
  actions: z.record(z.string(), z.number()).default({}),
});

export const intelligenceReportSchema = z.object({
  timestamp: z.string(),
  periodHours: z.number().int().nonnegative(),
  eventCount: z.number().int().nonnegative(),
  activityCount: z.number().int().nonnegative(),
  patterns: z.array(intelligencePatternSchema),
  recommendations: z.array(z.string()),
  autonomyAdjustments: z.array(intelligenceAutonomyAdjustmentSchema),
  agentBehavior: z.array(intelligenceAgentBehaviorSchema),
});

export const learningSectionSchema = z.object({
  cache: z
    .object({
      totalEntries: z.number().nullable().optional(),
      hitRate: z.number().nullable().optional(),
      tokensSaved: z.number().nullable().optional(),
      avgSimilarity: z.number().nullable().optional(),
    })
    .nullable(),
  circuits: z
    .object({
      services: z.number().nullable().optional(),
      open: z.number().nullable().optional(),
      halfOpen: z.number().nullable().optional(),
      closed: z.number().nullable().optional(),
      totalFailures: z.number().nullable().optional(),
    })
    .nullable(),
  preferences: z
    .object({
      modelTaskPairs: z.number().nullable().optional(),
      totalSamples: z.number().nullable().optional(),
      avgCompositeScore: z.number().nullable().optional(),
      converged: z.number().nullable().optional(),
    })
    .nullable(),
  trust: z
    .object({
      agentsTracked: z.number().nullable().optional(),
      avgTrustScore: z.number().nullable().optional(),
      highTrust: z.number().nullable().optional(),
      lowTrust: z.number().nullable().optional(),
    })
    .nullable(),
  diagnosis: z
    .object({
      recentFailures: z.number().nullable().optional(),
      patternsDetected: z.number().nullable().optional(),
      autoRemediations: z.number().nullable().optional(),
    })
    .nullable(),
  memory: z
    .object({
      collections: z.number().nullable().optional(),
      totalPoints: z.number().nullable().optional(),
    })
    .nullable(),
  tasks: z
    .object({
      total: z.number().nullable().optional(),
      completed: z.number().nullable().optional(),
      failed: z.number().nullable().optional(),
      successRate: z.number().nullable().optional(),
    })
    .nullable(),
});

export const learningSnapshotSchema = z.object({
  timestamp: z.string(),
  metrics: learningSectionSchema,
  summary: z.object({
    overallHealth: z.number().nullable().optional(),
    dataPoints: z.number().nullable().optional(),
    positiveSignals: z.array(z.string()).default([]),
    assessment: z.string().nullable().optional(),
  }),
});

export const intelligenceSnapshotSchema = z.object({
  generatedAt: z.string(),
  projects: z.array(projectSnapshotSchema),
  agents: z.array(workforceAgentSnapshotSchema),
  report: intelligenceReportSchema.nullable(),
  learning: learningSnapshotSchema.nullable(),
  improvement: workforceImprovementSummarySchema.nullable(),
  reviewTasks: z.array(workforceTaskSchema),
});

export const memoryPreferenceSchema = z.object({
  score: z.number(),
  content: z.string(),
  signalType: z.string(),
  agentId: z.string(),
  category: z.string().nullable(),
  timestamp: z.string(),
});

export const memoryRecentItemSchema = z.object({
  id: z.union([z.string(), z.number()]),
  title: z.string(),
  url: z.string().nullable(),
  source: z.string().nullable(),
  category: z.string().nullable(),
  subcategory: z.string().nullable(),
  description: z.string().nullable(),
  indexedAt: z.string().nullable(),
});

export const memoryCategorySchema = z.object({
  name: z.string(),
  count: z.number().int().nonnegative(),
});

export const memoryTopicSchema = z.object({
  name: z.string(),
  connections: z.number().int().nonnegative(),
});

export const memorySnapshotSchema = z.object({
  generatedAt: z.string(),
  projects: z.array(projectSnapshotSchema),
  summary: z.object({
    qdrantOnline: z.boolean(),
    neo4jOnline: z.boolean(),
    points: z.number().int().nonnegative(),
    vectors: z.number().int().nonnegative(),
    graphNodes: z.number().int().nonnegative(),
    graphRelationships: z.number().int().nonnegative(),
  }),
  preferences: z.array(memoryPreferenceSchema),
  recentItems: z.array(memoryRecentItemSchema),
  categories: z.array(memoryCategorySchema),
  topTopics: z.array(memoryTopicSchema),
  graphLabels: z.array(z.string()),
});

export const monitoringNodeSnapshotSchema = z.object({
  id: z.string(),
  name: z.string(),
  ip: z.string(),
  role: z.string(),
  cpuUsage: z.number().nullable(),
  memUsed: z.number().nullable(),
  memTotal: z.number().nullable(),
  diskUsed: z.number().nullable(),
  diskTotal: z.number().nullable(),
  networkRxRate: z.number().nullable(),
  networkTxRate: z.number().nullable(),
  uptime: z.number().nullable(),
  load1: z.number().nullable(),
  cpuHistory: z.array(z.number()),
  memHistory: z.array(z.number()),
});

export const monitoringSnapshotSchema = z.object({
  generatedAt: z.string(),
  summary: z.object({
    reachableNodes: z.number().int().nonnegative(),
    totalNodes: z.number().int().nonnegative(),
    averageCpu: z.number().nullable(),
    totalMemUsed: z.number().nullable(),
    totalMemTotal: z.number().nullable(),
    networkRxRate: z.number().nullable(),
    networkTxRate: z.number().nullable(),
  }),
  nodes: z.array(monitoringNodeSnapshotSchema),
  dashboards: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      description: z.string(),
      url: z.string().url(),
    })
  ),
});

export const mediaSessionSchema = z.object({
  friendlyName: z.string().nullable(),
  title: z.string().nullable(),
  state: z.string().nullable(),
  progressPercent: z.number().nullable(),
  transcodeDecision: z.string().nullable(),
  mediaType: z.string().nullable(),
  year: z.string().nullable(),
  thumb: z.string().nullable(),
});

export const mediaQueueItemSchema = z.object({
  id: z.string(),
  title: z.string().nullable(),
  source: z.string(),
  progressPercent: z.number().nullable(),
  status: z.string().nullable(),
  timeLeft: z.string().nullable(),
});

export const mediaCalendarItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  seriesTitle: z.string().nullable(),
  seasonNumber: z.number().nullable(),
  episodeNumber: z.number().nullable(),
  airDateUtc: z.string().nullable(),
  hasFile: z.boolean().nullable(),
});

export const mediaWatchItemSchema = z.object({
  id: z.string(),
  friendlyName: z.string().nullable(),
  title: z.string().nullable(),
  date: z.string().nullable(),
  duration: z.string().nullable(),
  watchedStatus: z.number().nullable(),
});

export const mediaLibrarySchema = z.object({
  total: z.number().nullable(),
  monitored: z.number().nullable(),
  episodes: z.number().nullable(),
  sizeGb: z.number().nullable(),
  hasFile: z.number().nullable().optional(),
});

export const mediaSnapshotSchema = z.object({
  generatedAt: z.string(),
  streamCount: z.number().int().nonnegative(),
  sessions: z.array(mediaSessionSchema),
  downloads: z.array(mediaQueueItemSchema),
  tvUpcoming: z.array(mediaCalendarItemSchema),
  movieUpcoming: z.array(mediaCalendarItemSchema),
  watchHistory: z.array(mediaWatchItemSchema),
  tvLibrary: mediaLibrarySchema.nullable(),
  movieLibrary: mediaLibrarySchema.nullable(),
  stash: z
    .object({
      sceneCount: z.number().nullable(),
      imageCount: z.number().nullable(),
      performerCount: z.number().nullable(),
      studioCount: z.number().nullable(),
      tagCount: z.number().nullable(),
      scenesSize: z.number().nullable(),
      scenesDuration: z.number().nullable(),
    })
    .nullable(),
  launchLinks: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      url: z.string().url(),
    })
  ),
});

export const galleryImageSchema = z.object({
  filename: z.string(),
  subfolder: z.string(),
  type: z.string(),
});

export const galleryHistoryItemSchema = z.object({
  id: z.string(),
  prompt: z.string(),
  outputPrefix: z.string(),
  timestamp: z.number(),
  outputImages: z.array(galleryImageSchema),
});

export const gallerySnapshotSchema = z.object({
  generatedAt: z.string(),
  queueRunning: z.number().int().nonnegative(),
  queuePending: z.number().int().nonnegative(),
  deviceName: z.string().nullable(),
  vramUsedGiB: z.number().nullable(),
  vramTotalGiB: z.number().nullable(),
  items: z.array(galleryHistoryItemSchema),
});

export const homeSetupStepSchema = z.object({
  id: z.string(),
  label: z.string(),
  status: z.enum(["complete", "pending", "blocked"]),
  note: z.string().nullable(),
});

export const homeSnapshotSchema = z.object({
  generatedAt: z.string(),
  online: z.boolean(),
  configured: z.boolean(),
  title: z.string(),
  summary: z.string(),
  setupSteps: z.array(homeSetupStepSchema),
  panels: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      description: z.string(),
      href: z.string(),
    })
  ),
});

export const executionRunArtifactSchema = z.object({
  label: z.string(),
  href: z.string(),
});

export const executionRunRecordSchema = z.object({
  id: z.string(),
  source_lane: z.string(),
  run_type: z.string(),
  task_id: z.string().nullable(),
  job_id: z.string().nullable(),
  agent: z.string().nullable(),
  provider: z.string(),
  lease_id: z.string().nullable(),
  status: z.string(),
  created_at: z.string().nullable(),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  artifact_refs: z.array(executionRunArtifactSchema),
  failure_reason: z.string().nullable(),
  summary: z.string(),
});

export const executionRunsResponseSchema = z.object({
  runs: z.array(executionRunRecordSchema),
  count: z.number().int().nonnegative(),
});

export const scheduledJobRecordSchema = z.object({
  id: z.string(),
  job_family: z.string(),
  title: z.string(),
  cadence: z.string(),
  trigger_mode: z.string(),
  last_run: z.string().nullable(),
  next_run: z.string().nullable(),
  current_state: z.string(),
  last_outcome: z.string().nullable(),
  owner_agent: z.string().nullable(),
  deep_link: z.string().nullable(),
});

export const scheduledJobsResponseSchema = z.object({
  jobs: z.array(scheduledJobRecordSchema),
  count: z.number().int().nonnegative(),
});

export const operatorStreamEventSchema = z.object({
  id: z.string(),
  timestamp: z.string(),
  severity: z.enum(["info", "success", "warning", "error"]),
  subsystem: z.string(),
  event_type: z.string(),
  subject: z.string(),
  summary: z.string(),
  deep_link: z.string().nullable(),
  related_run_id: z.string().nullable(),
});

export const operatorStreamResponseSchema = z.object({
  events: z.array(operatorStreamEventSchema),
  count: z.number().int().nonnegative(),
});

export const quotaOutcomeSummarySchema = z.object({
  outcome: z.string(),
  count: z.number().int().nonnegative(),
});

export const quotaLeaseSummarySchema = z.object({
  provider: z.string(),
  lane: z.string(),
  availability: z.string(),
  reserve_state: z.string(),
  limit: z.number().int().nonnegative(),
  remaining: z.number().int(),
  throttle_events: z.number().int().nonnegative(),
  recent_outcomes: z.array(quotaOutcomeSummarySchema),
  last_issued_at: z.string().nullable(),
  last_outcome_at: z.string().nullable(),
});

export const subscriptionSummaryResponseSchema = z.object({
  policy_source: z.string(),
  provider_summaries: z.array(quotaLeaseSummarySchema),
  recent_leases: z.array(executionRunRecordSchema),
  count: z.number().int().nonnegative(),
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
export type ProjectSnapshot = z.infer<typeof projectSnapshotSchema>;
export type ProjectsSnapshot = z.infer<typeof projectsSnapshotSchema>;
export type WorkforceTask = z.infer<typeof workforceTaskSchema>;
export type WorkplanTask = z.infer<typeof workplanTaskSchema>;
export type WorkplanSnapshot = z.infer<typeof workplanSnapshotSchema>;
export type WorkforceGoal = z.infer<typeof workforceGoalSchema>;
export type WorkforceNotification = z.infer<typeof workforceNotificationSchema>;
export type WorkforceTrustEntry = z.infer<typeof workforceTrustEntrySchema>;
export type WorkspaceItemSnapshot = z.infer<typeof workspaceItemSnapshotSchema>;
export type WorkspaceSnapshot = z.infer<typeof workspaceSnapshotSchema>;
export type WorkspaceSubscription = z.infer<typeof workspaceSubscriptionSchema>;
export type WorkforceAgentSnapshot = z.infer<typeof workforceAgentSnapshotSchema>;
export type WorkforceScheduleEntry = z.infer<typeof workforceScheduleEntrySchema>;
export type ProjectPosture = z.infer<typeof projectPostureSchema>;
export type WorkforceConvention = z.infer<typeof workforceConventionSchema>;
export type WorkforceImprovementSummary = z.infer<typeof workforceImprovementSummarySchema>;
export type WorkforceSnapshot = z.infer<typeof workforceSnapshotSchema>;
export type ChatStreamEvent = z.infer<typeof chatStreamEventSchema>;
export type TranscriptMessage = z.infer<typeof transcriptMessageSchema>;
export type DirectChatSession = z.infer<typeof directChatSessionSchema>;
export type AgentThread = z.infer<typeof agentThreadSchema>;
export type UiPreferences = z.infer<typeof uiPreferencesSchema>;
export type HistoryActivityItem = z.infer<typeof historyActivityItemSchema>;
export type HistoryConversationItem = z.infer<typeof historyConversationItemSchema>;
export type HistoryOutputItem = z.infer<typeof historyOutputItemSchema>;
export type HistorySnapshot = z.infer<typeof historySnapshotSchema>;
export type IntelligencePattern = z.infer<typeof intelligencePatternSchema>;
export type IntelligenceReport = z.infer<typeof intelligenceReportSchema>;
export type LearningSnapshot = z.infer<typeof learningSnapshotSchema>;
export type IntelligenceSnapshot = z.infer<typeof intelligenceSnapshotSchema>;
export type MemoryPreference = z.infer<typeof memoryPreferenceSchema>;
export type MemoryRecentItem = z.infer<typeof memoryRecentItemSchema>;
export type MemorySnapshot = z.infer<typeof memorySnapshotSchema>;
export type MonitoringNodeSnapshot = z.infer<typeof monitoringNodeSnapshotSchema>;
export type MonitoringSnapshot = z.infer<typeof monitoringSnapshotSchema>;
export type MediaSnapshot = z.infer<typeof mediaSnapshotSchema>;
export type GallerySnapshot = z.infer<typeof gallerySnapshotSchema>;
export type HomeSnapshot = z.infer<typeof homeSnapshotSchema>;
export type ExecutionRunRecord = z.infer<typeof executionRunRecordSchema>;
export type ExecutionRunsResponse = z.infer<typeof executionRunsResponseSchema>;
export type ScheduledJobRecord = z.infer<typeof scheduledJobRecordSchema>;
export type ScheduledJobsResponse = z.infer<typeof scheduledJobsResponseSchema>;
export type OperatorStreamEvent = z.infer<typeof operatorStreamEventSchema>;
export type OperatorStreamResponse = z.infer<typeof operatorStreamResponseSchema>;
export type QuotaLeaseSummary = z.infer<typeof quotaLeaseSummarySchema>;
export type SubscriptionSummaryResponse = z.infer<typeof subscriptionSummaryResponseSchema>;
