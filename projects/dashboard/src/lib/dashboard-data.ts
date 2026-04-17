import { z } from "zod";
import {
  type AgentInfo,
  type BackendSnapshot,
  type GpuHistoryResponse,
  type GpuSnapshot,
  type GpuSnapshotResponse,
  judgePlaneSnapshotSchema,
  type JudgePlaneSnapshot,
  type ModelInventoryEntry,
  type ModelsSnapshot,
  type OverviewSnapshot,
  type ProjectPosture,
  type ProjectSnapshot,
  type ProjectsSnapshot,
  serviceHealthSnapshotSchema,
  type ServiceHistorySeries,
  type ServiceSnapshot,
  type ServicesHistorySnapshot,
  type ServicesSnapshot,
  type WorkforceAgentSnapshot,
  type WorkforceGoal,
  type WorkforceNotification,
  type WorkforceScheduleEntry,
  type WorkforceSnapshot,
  type WorkforceTask,
  type WorkplanSnapshot,
  type WorkplanTask,
} from "@/lib/contracts";
import {
  getFixtureAgentsSnapshot,
  getFixtureGpuHistory,
  getFixtureGpuSnapshot,
  getFixtureModelsSnapshot,
  getFixtureOverviewSnapshot,
  getFixtureServicesHistory,
  getFixtureServicesSnapshot,
  getFixtureWorkforceSnapshot,
  isDashboardFixtureMode,
} from "@/lib/dashboard-fixtures";
import { average, formatTemperatureF } from "@/lib/format";
import { buildNavAttentionSignals } from "@/lib/nav-attention";
import { loadSteadyStateFrontDoor } from "@/lib/operator-frontdoor";
import { agentServerHeaders, config, getNodeNameFromInstance, joinUrl, type MonitoredService } from "@/lib/config";
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

const passThroughHealthyServiceIds = new Set([
  "litellm-proxy",
  "qdrant",
  "neo4j",
  "prometheus",
  "grafana",
  "foundry-node-exporter",
  "workshop-node-exporter",
  "vault-node-exporter",
  "foundry-dcgm-exporter",
  "workshop-dcgm-exporter",
  "vault-open-webui",
  "comfyui",
  "workshop-open-webui",
  "eoq",
  "home-assistant",
  "speaches",
  "plex",
  "sonarr",
  "radarr",
  "tautulli",
  "prowlarr",
  "sabnzbd",
  "stash",
]);

const serviceWarningOverrides: Record<string, string> = {};

const rawAgentMetadataSchema = z.object({
  name: z.string(),
  description: z.string(),
  tools: z.array(z.string()).default([]),
  type: z.string().default("reactive"),
  status: z.string().default("planned"),
  schedule: z.string().nullable().optional(),
  status_note: z.string().nullable().optional(),
});

const agentsResponseSchema = z.object({
  agents: z.array(rawAgentMetadataSchema),
});

const rawWorkplanTaskSchema = z.object({
  task_id: z.string().optional(),
  agent: z.string(),
  project: z.string().optional(),
  prompt: z.string(),
  priority: z.string().optional(),
  rationale: z.string().optional(),
});

const rawWorkplanSchema = z.object({
  plan_id: z.string(),
  generated_at: z.coerce.number(),
  time_context: z.string().optional(),
  focus: z.string().optional(),
  tasks: z.array(rawWorkplanTaskSchema).default([]),
  task_count: z.number().int().nonnegative().default(0),
  error: z.string().optional(),
});

const workplanResponseSchema = z.object({
  current_plan: rawWorkplanSchema.nullable().optional(),
  history: z.array(rawWorkplanSchema).default([]),
  needs_refill: z.boolean().default(false),
});

const rawTaskSchema = z.object({
  id: z.string(),
  agent: z.string(),
  prompt: z.string(),
  priority: z.string().optional(),
  status: z.string().optional(),
  result: z.string().optional().default(""),
  error: z.string().optional().default(""),
  steps: z.array(z.object({}).passthrough()).default([]),
  created_at: z.coerce.number().default(0),
  started_at: z.coerce.number().default(0),
  completed_at: z.coerce.number().default(0),
  metadata: z.record(z.string(), z.unknown()).default({}),
  parent_task_id: z.string().optional().default(""),
});

const tasksResponseSchema = z.object({
  tasks: z.array(rawTaskSchema).default([]),
  count: z.number().int().nonnegative().default(0),
});

const schedulesResponseSchema = z.object({
  schedules: z
    .array(
      z.object({
        agent: z.string(),
        interval_seconds: z.number().int().nonnegative(),
        interval_human: z.string(),
        enabled: z.boolean(),
        last_run: z.number().nullable().optional(),
        next_run_in: z.number().int().nonnegative(),
        priority: z.string(),
      })
    )
    .default([]),
  scheduler_running: z.boolean().default(false),
});

const goalsResponseSchema = z.object({
  goals: z
    .array(
      z.object({
        id: z.string(),
        text: z.string(),
        agent: z.string().default("global"),
        priority: z.enum(["low", "normal", "high"]).catch("normal"),
        created_at: z.coerce.number().default(0),
        active: z.boolean().default(true),
      })
    )
    .default([]),
});

const trustResponseSchema = z.object({
  agents: z
    .record(
      z.string(),
      z.object({
        score: z.number().optional(),
        grade: z.string().optional(),
        feedback: z
          .object({
            up: z.number().int().nonnegative().default(0),
            down: z.number().int().nonnegative().default(0),
            total: z.number().int().nonnegative().default(0),
          })
          .optional(),
        escalation: z
          .object({
            approved: z.number().int().nonnegative().default(0),
            rejected: z.number().int().nonnegative().default(0),
            total: z.number().int().nonnegative().default(0),
          })
          .optional(),
        samples: z.number().int().nonnegative().optional(),
      })
    )
    .default({}),
  warning: z.string().optional(),
});

const notificationsResponseSchema = z.object({
  notifications: z
    .array(
      z.object({
        id: z.string(),
        agent: z.string(),
        action: z.string(),
        category: z.string().default("read"),
        confidence: z.coerce.number().default(0.5),
        description: z.string().default(""),
        tier: z.enum(["act", "notify", "ask"]).catch("notify"),
        created_at: z.coerce.number().default(0),
        resolved: z.boolean().default(false),
        resolution: z.string().optional().default(""),
      })
    )
    .default([]),
  count: z.number().int().nonnegative().default(0),
  unread: z.number().int().nonnegative().default(0),
});

const rawWorkspaceItemSchema = z.object({
  id: z.string(),
  source_agent: z.string().default("system"),
  content: z.string(),
  priority: z.string().default("normal"),
  salience: z.coerce.number().default(0),
  ttl: z.number().int().positive().default(300),
  created_at: z.coerce.number().default(0),
  metadata: z.record(z.string(), z.unknown()).default({}),
  coalition: z.array(z.string()).default([]),
});

const workspaceResponseSchema = z.object({
  broadcast: z.array(rawWorkspaceItemSchema).default([]),
  count: z.number().int().nonnegative().default(0),
});

const workspaceStatsResponseSchema = z.object({
  total_items: z.number().int().nonnegative().default(0),
  broadcast_items: z.number().int().nonnegative().default(0),
  capacity: z.number().int().positive().default(7),
  utilization: z.coerce.number().default(0),
  agents_active: z.record(z.string(), z.number().int().nonnegative()).default({}),
  top_item: rawWorkspaceItemSchema.nullable().optional(),
  competition_running: z.boolean().default(false),
});

const workspaceSubscriptionsResponseSchema = z.object({
  subscriptions: z
    .record(
      z.string(),
      z.object({
        agent_name: z.string(),
        keywords: z.array(z.string()).default([]),
        source_filters: z.array(z.string()).default([]),
        threshold: z.coerce.number().default(0.3),
        react_prompt_template: z.string().default(""),
      })
    )
    .default({}),
  count: z.number().int().nonnegative().default(0),
});

const conventionsResponseSchema = z.object({
  conventions: z
    .array(
      z.object({
        id: z.string(),
        type: z.string(),
        agent: z.string(),
        description: z.string(),
        rule: z.string(),
        source: z.string().default("manual"),
        occurrences: z.number().int().nonnegative().default(0),
        status: z.string().default("confirmed"),
        created_at: z.coerce.number().default(0),
        confirmed_at: z.coerce.number().nullable().optional(),
      })
    )
    .default([]),
  count: z.number().int().nonnegative().default(0),
  status: z.string().optional(),
});

const improvementSummaryResponseSchema = z.object({
  total_proposals: z.number().int().nonnegative().default(0),
  pending: z.number().int().nonnegative().default(0),
  validated: z.number().int().nonnegative().default(0),
  deployed: z.number().int().nonnegative().default(0),
  failed: z.number().int().nonnegative().default(0),
  benchmark_results: z.number().int().nonnegative().default(0),
  last_cycle: z
    .object({
      timestamp: z.string(),
      patterns_consumed: z.number().int().nonnegative().default(0),
      proposals_generated: z.number().int().nonnegative().default(0),
      benchmarks: z
        .object({
          passed: z.number().int().nonnegative().default(0),
          total: z.number().int().nonnegative().default(0),
          pass_rate: z.coerce.number().default(0),
        })
        .nullable()
        .optional(),
    })
    .nullable()
    .optional(),
});

const operatorStatusCountsSchema = z.record(z.string(), z.number().int().nonnegative()).default({});

const operatorSummarySectionSchema = z.object({
  total: z.number().int().nonnegative().default(0),
  by_status: operatorStatusCountsSchema,
});

const operatorTaskSummarySchema = z.object({
  total: z.number().int().nonnegative().default(0),
  by_status: operatorStatusCountsSchema,
  pending_approval: z.number().int().nonnegative().default(0),
  stale_lease: z.number().int().nonnegative().default(0),
  failed_actionable: z.number().int().nonnegative().default(0),
  failed_historical_repaired: z.number().int().nonnegative().default(0),
  failed_missing_detail: z.number().int().nonnegative().default(0),
});

const operatorSummaryResponseSchema = z
  .object({
    ideas: operatorSummarySectionSchema.default({ total: 0, by_status: {} }),
    inbox: operatorSummarySectionSchema.default({ total: 0, by_status: {} }),
    todos: operatorSummarySectionSchema.default({ total: 0, by_status: {} }),
    backlog: operatorSummarySectionSchema.default({ total: 0, by_status: {} }),
    runs: operatorSummarySectionSchema.default({ total: 0, by_status: {} }),
    approvals: operatorSummarySectionSchema.default({ total: 0, by_status: {} }),
    tasks: operatorTaskSummarySchema.default({
      total: 0,
      by_status: {},
      pending_approval: 0,
      stale_lease: 0,
      failed_actionable: 0,
      failed_historical_repaired: 0,
      failed_missing_detail: 0,
    }),
  })
  .passthrough();

const rawOperatorRunSchema = z
  .object({
    id: z.string(),
    task_id: z.string().optional().default(""),
    backlog_id: z.string().optional().default(""),
    agent_id: z.string().optional().default(""),
    workload_class: z.string().optional().default(""),
    provider_lane: z.string().optional().default(""),
    runtime_lane: z.string().optional().default(""),
    policy_class: z.string().optional().default(""),
    status: z.string().optional().default("pending"),
    summary: z.string().optional().default(""),
    created_at: z.coerce.number().default(0),
    updated_at: z.coerce.number().default(0),
    completed_at: z.coerce.number().default(0),
    step_count: z.number().int().nonnegative().default(0),
    approval_pending: z.boolean().default(false),
    latest_attempt: z
      .object({
        id: z.string().optional().default(""),
        runtime_host: z.string().optional().default(""),
        status: z.string().optional().default(""),
        heartbeat_at: z.coerce.number().default(0),
      })
      .nullable()
      .optional(),
    approvals: z.array(z.object({ id: z.string().optional().default(""), status: z.string().optional().default(""), privilege_class: z.string().optional().default("") }).passthrough()).default([]),
    metadata: z.record(z.string(), z.unknown()).default({}),
  })
  .passthrough();

const operatorRunsResponseSchema = z.object({
  runs: z.array(rawOperatorRunSchema).default([]),
  count: z.number().int().nonnegative().default(0),
});

const rawOperatorBacklogSchema = z
  .object({
    id: z.string(),
    title: z.string().optional().default(""),
    prompt: z.string().optional().default(""),
    owner_agent: z.string().optional().default(""),
    support_agents: z.array(z.string()).default([]),
    scope_type: z.string().optional().default("global"),
    scope_id: z.string().optional().default(""),
    work_class: z.string().optional().default(""),
    priority: z.union([z.number(), z.string()]).optional(),
    status: z.string().optional().default("captured"),
    approval_mode: z.string().optional().default("none"),
    dispatch_policy: z.string().optional().default("planner_eligible"),
    preconditions: z.array(z.string()).default([]),
    blocking_reason: z.string().optional().default(""),
    created_at: z.coerce.number().default(0),
    updated_at: z.coerce.number().default(0),
    completed_at: z.coerce.number().default(0),
    metadata: z.record(z.string(), z.unknown()).default({}),
  })
  .passthrough();

const operatorBacklogResponseSchema = z.object({
  backlog: z.array(rawOperatorBacklogSchema).default([]),
  count: z.number().int().nonnegative().default(0),
});

const rawOperatorTodoSchema = z
  .object({
    id: z.string(),
    title: z.string().optional().default(""),
    description: z.string().optional().default(""),
    category: z.string().optional().default("ops"),
    scope_type: z.string().optional().default("global"),
    scope_id: z.string().optional().default(""),
    priority: z.union([z.number(), z.string()]).optional(),
    status: z.string().optional().default("open"),
    energy_class: z.string().optional().default("focused"),
    created_at: z.coerce.number().default(0),
    updated_at: z.coerce.number().default(0),
    completed_at: z.coerce.number().default(0),
  })
  .passthrough();

const operatorTodosResponseSchema = z.object({
  todos: z.array(rawOperatorTodoSchema).default([]),
  count: z.number().int().nonnegative().default(0),
});

const rawOperatorInboxSchema = z
  .object({
    id: z.string(),
    kind: z.string().optional().default("notice"),
    severity: z.coerce.number().default(1),
    status: z.string().optional().default("new"),
    source: z.string().optional().default("system"),
    title: z.string().optional().default(""),
    description: z.string().optional().default(""),
    requires_decision: z.boolean().default(false),
    decision_type: z.string().optional().default(""),
    related_run_id: z.string().optional().default(""),
    snooze_until: z.coerce.number().default(0),
    created_at: z.coerce.number().default(0),
    updated_at: z.coerce.number().default(0),
    resolved_at: z.coerce.number().default(0),
  })
  .passthrough();

const operatorInboxResponseSchema = z.object({
  items: z.array(rawOperatorInboxSchema).default([]),
  count: z.number().int().nonnegative().default(0),
});

const rawOperatorIdeaSchema = z
  .object({
    id: z.string(),
    title: z.string().optional().default(""),
    note: z.string().optional().default(""),
    tags: z.array(z.string()).default([]),
    source: z.string().optional().default("operator"),
    confidence: z.coerce.number().default(0),
    energy_class: z.string().optional().default("focused"),
    scope_guess: z.string().optional().default("global"),
    status: z.string().optional().default("seed"),
    next_review_at: z.coerce.number().default(0),
    promoted_project_id: z.string().optional().default(""),
    created_at: z.coerce.number().default(0),
    updated_at: z.coerce.number().default(0),
  })
  .passthrough();

const operatorIdeasResponseSchema = z.object({
  ideas: z.array(rawOperatorIdeaSchema).default([]),
  count: z.number().int().nonnegative().default(0),
});

const rawOperatorApprovalSchema = z
  .object({
    id: z.string(),
    related_run_id: z.string().optional().default(""),
    related_task_id: z.string().optional().default(""),
    requested_action: z.string().optional().default(""),
    privilege_class: z.string().optional().default(""),
    reason: z.string().optional().default(""),
    status: z.string().optional().default("pending"),
    requested_at: z.coerce.number().default(0),
    decided_at: z.coerce.number().default(0),
    decided_by: z.string().optional().default(""),
    task_prompt: z.string().optional().default(""),
    task_agent_id: z.string().optional().default(""),
    task_priority: z.string().optional().default("normal"),
    task_status: z.string().optional().default("pending"),
    task_created_at: z.coerce.number().default(0),
    metadata: z.record(z.string(), z.unknown()).default({}),
  })
  .passthrough();

const operatorApprovalsResponseSchema = z.object({
  approvals: z.array(rawOperatorApprovalSchema).default([]),
  count: z.number().int().nonnegative().default(0),
});

const projectsResponseSchema = z.object({
  projects: z.record(
    z.string(),
    z.object({
      name: z.string(),
      headline: z.string().optional(),
      description: z.string(),
      status: z.string(),
      kind: z.enum(["core", "tenant", "domain", "scaffold"]).optional(),
      first_class: z.boolean().optional(),
      lens: z.string().optional(),
      primary_route: z.string().optional(),
      external_url: z.string().url().nullable().optional(),
      operators: z.array(z.string()).default([]),
      agents: z.array(z.string()),
      needs_count: z.number().int().nonnegative(),
      constraints: z.array(z.string()),
      location: z.string().optional(),
      tech: z.string().optional(),
    })
  ),
  count: z.number().int().nonnegative(),
});

type PrometheusInstantResult = z.infer<typeof prometheusInstantResponseSchema>["data"]["result"][number];
type PrometheusRangeResult = z.infer<typeof prometheusRangeResponseSchema>["data"]["result"][number];
type RawTask = z.infer<typeof rawTaskSchema>;
type RawWorkplan = z.infer<typeof rawWorkplanSchema>;
type RawWorkspaceItem = z.infer<typeof rawWorkspaceItemSchema>;
type RawConvention = z.infer<typeof conventionsResponseSchema>["conventions"][number];
type RawOperatorRun = z.infer<typeof rawOperatorRunSchema>;
type RawOperatorBacklog = z.infer<typeof rawOperatorBacklogSchema>;
type RawOperatorTodo = z.infer<typeof rawOperatorTodoSchema>;
type RawOperatorInbox = z.infer<typeof rawOperatorInboxSchema>;
type RawOperatorIdea = z.infer<typeof rawOperatorIdeaSchema>;
type RawOperatorApproval = z.infer<typeof rawOperatorApprovalSchema>;

const WORKPLAN_MORNING_HOUR_LOCAL = 7;
const WORKPLAN_MORNING_MINUTE_LOCAL = 0;
const WORKPLAN_REFILL_INTERVAL_HOURS = 2;
const WORKPLAN_MIN_PENDING_TASKS = 2;

const agentPresentation: Record<string, { name: string; icon: string }> = {
  "general-assistant": { name: "General Assistant", icon: "terminal" },
  "media-agent": { name: "Media Agent", icon: "film" },
  "home-agent": { name: "Home Agent", icon: "home" },
  "creative-agent": { name: "Creative Agent", icon: "sparkles" },
  "research-agent": { name: "Research Agent", icon: "search" },
  "knowledge-agent": { name: "Knowledge Agent", icon: "book-open" },
  "coding-agent": { name: "Coding Agent", icon: "code" },
  "stash-agent": { name: "Stash Agent", icon: "gallery-horizontal-end" },
  "data-curator": { name: "Data Curator", icon: "database" },
};

function nowIso() {
  return new Date().toISOString();
}

const fallbackJudgePlaneSnapshot: JudgePlaneSnapshot = {
  generated_at: nowIso(),
  status: "unavailable",
  role_id: "judge",
  label: "Judge Plane",
  champion: "Unavailable",
  challengers: [],
  workload_classes: [],
  summary: {
    recent_verdicts: 0,
    accept_count: 0,
    reject_count: 0,
    review_required: 0,
    acceptance_rate: 0,
    pending_review_queue: 0,
  },
  guardrails: [],
  recent_verdicts: [],
};

function unixToIso(timestamp: number | null | undefined): string | null {
  if (!timestamp || timestamp <= 0) {
    return null;
  }

  return new Date(timestamp * 1000).toISOString();
}

function normalizePriority(value: string | number | null | undefined): WorkforceTask["priority"] {
  if (typeof value === "number") {
    if (value >= 4) return "high";
    if (value <= 2) return "low";
    return "normal";
  }

  const candidate = typeof value === "string" ? value.trim().toLowerCase() : "";
  if (candidate === "critical" || candidate === "high" || candidate === "low" || candidate === "normal") {
    return candidate;
  }
  if (candidate) {
    const numeric = Number.parseInt(candidate, 10);
    if (!Number.isNaN(numeric)) {
      return normalizePriority(numeric);
    }
  }
  return "normal";
}

function normalizeTaskStatus(value: string | null | undefined): WorkforceTask["status"] {
  switch (value) {
    case "pending":
    case "pending_approval":
    case "running":
    case "stale_lease":
    case "completed":
    case "failed":
    case "cancelled":
      return value;
    default:
      return "pending";
  }
}

function normalizeText(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function getAgentName(agentId: string) {
  return agentPresentation[agentId]?.name ?? agentId;
}

function getAgentIcon(agentId: string) {
  return agentPresentation[agentId]?.icon ?? "bot";
}

function normalizeAgentStatus(status: string): AgentInfo["status"] {
  return status === "online" ? "ready" : "unavailable";
}

function getNextWorkplanRunIso(now = new Date()) {
  const next = new Date(now);
  next.setHours(WORKPLAN_MORNING_HOUR_LOCAL, WORKPLAN_MORNING_MINUTE_LOCAL, 0, 0);
  if (next <= now) {
    next.setDate(next.getDate() + 1);
  }
  return next.toISOString();
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
  const response = await fetch(input, {
    ...init,
    signal: init?.signal ?? AbortSignal.timeout(8000),
  });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }

  return schema.parse(await response.json());
}

async function fetchAgentJson<T>(path: string, schema: z.ZodSchema<T>, fallback: T): Promise<T> {
  try {
    return await fetchJson(joinUrl(config.agentServer.url, path), schema, {
      cache: "no-store",
      headers: agentServerHeaders(),
    });
  } catch {
    return fallback;
  }
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

function deriveServiceState(
  healthStatus: string | null,
  healthy: boolean,
  latencyMs: number | null,
  contractDrift = false
): ServiceSnapshot["state"] {
  if (contractDrift) {
    return "warning";
  }

  if (healthStatus === "down" || healthStatus === "degraded") {
    return "degraded";
  }

  if (healthStatus === "unknown") {
    return "muted";
  }

  if (!healthy) {
    return "degraded";
  }

  if (latencyMs !== null && latencyMs > 1000) {
    return "warning";
  }

  return "healthy";
}

async function tryParseServiceHealthSnapshot(response: Response) {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().includes("application/json")) {
    return null;
  }

  try {
    const payload = await response.clone().json();
    return serviceHealthSnapshotSchema.parse(payload);
  } catch {
    return null;
  }
}

async function isModelCatalogResponse(response: Response) {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().includes("application/json")) {
    return false;
  }

  try {
    const payload = await response.clone().json();
    return backendModelsResponseSchema.safeParse(payload).success;
  } catch {
    return false;
  }
}

function isHealthyHealthStatus(status: string) {
  return status === "healthy";
}

function getServiceHealthStatus(service: ServiceSnapshot) {
  return service.healthSnapshot?.status ?? (service.healthy ? "healthy" : "down");
}

function summarizeServiceStates(services: ServiceSnapshot[]) {
  const summary = {
    healthy: 0,
    warning: 0,
    degraded: 0,
  };

  for (const service of services) {
    if (service.state === "healthy") {
      summary.healthy += 1;
      continue;
    }

    if (service.state === "warning") {
      summary.warning += 1;
      continue;
    }

    summary.degraded += 1;
  }

  return summary;
}

function isServiceDegraded(service: ServiceSnapshot) {
  return getServiceHealthStatus(service) !== "healthy";
}


function describeServiceCondition(service: ServiceSnapshot) {
  const healthStatus = service.healthSnapshot?.status;
  if (!healthStatus) {
    return `${service.node} is unreachable from the dashboard probe.`;
  }

  if (healthStatus === "healthy") {
    return service.lastError
      ? `${service.node} is healthy but still reported a recent issue: ${service.lastError}`
      : `${service.node} is reporting healthy service status.`;
  }

  if (service.lastError) {
    return `${service.node} reported ${healthStatus}: ${service.lastError}`;
  }

  const degradedDependencies = (service.dependencies ?? []).filter(
    (dependency) => dependency.status !== "healthy"
  );
  if (degradedDependencies.length > 0) {
    return `${service.node} reported ${healthStatus}; affected dependencies: ${degradedDependencies
      .map((dependency) => dependency.id)
      .join(", ")}.`;
  }

  return `${service.node} reported ${healthStatus} service status.`;
}

async function checkService(service: MonitoredService): Promise<ServiceSnapshot> {
  const start = Date.now();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), service.probeTimeoutMs ?? 5000);
  const checkedAt = nowIso();
  const requestHeaders: HeadersInit | undefined =
    service.headers && Object.keys(service.headers).length > 0
      ? service.headers
      : service.token
        ? { Authorization: `Bearer ${service.token}` }
        : undefined;

  try {
    const response = await fetch(service.url, {
      signal: controller.signal,
      cache: "no-store",
      headers: requestHeaders,
    });
    const latencyMs = Date.now() - start;
    const healthSnapshot = await tryParseServiceHealthSnapshot(response);
    const modelCatalogHealthy =
      !healthSnapshot && response.ok && (await isModelCatalogResponse(response));
    const passThroughHealthy =
      !healthSnapshot &&
      !modelCatalogHealthy &&
      response.ok &&
      passThroughHealthyServiceIds.has(service.id);
    const authGuardedPassThrough =
      !healthSnapshot &&
      !modelCatalogHealthy &&
      (response.status === 401 || response.status === 403) &&
      passThroughHealthyServiceIds.has(service.id);
    const contractDrift =
      !healthSnapshot &&
      !modelCatalogHealthy &&
      !passThroughHealthy &&
      !authGuardedPassThrough &&
      (response.ok || response.status === 401 || response.status === 403);
    const healthStatus =
      healthSnapshot?.status ?? (modelCatalogHealthy || passThroughHealthy || authGuardedPassThrough ? "healthy" : null);
    const healthy = healthSnapshot
      ? isHealthyHealthStatus(healthSnapshot.status)
      : modelCatalogHealthy || passThroughHealthy || authGuardedPassThrough;
    const warningOverride = serviceWarningOverrides[service.id] ?? null;
    const derivedState = deriveServiceState(healthStatus, healthy, latencyMs, contractDrift);
    return {
      id: service.id,
      name: service.name,
      nodeId: service.nodeId,
      node: service.node,
      category: service.category,
      description: service.description,
      url: service.url,
      healthy,
      latencyMs,
      checkedAt,
      state: warningOverride || authGuardedPassThrough ? "warning" : derivedState,
      authClass: healthSnapshot?.auth_class,
      startedAt: healthSnapshot?.started_at ?? null,
      actionsAllowed: healthSnapshot?.actions_allowed,
      lastError:
        warningOverride ??
        (authGuardedPassThrough ? "Service is reachable but requires auth for the health probe." : null) ??
        healthSnapshot?.last_error ??
        (contractDrift ? "Service health endpoint did not return the shared snapshot contract." : null),
      dependencies: healthSnapshot?.dependencies,
      healthSnapshot: healthSnapshot ?? undefined,
    };
  } catch (error) {
    const errorName =
      typeof error === "object" && error !== null && "name" in error && typeof error.name === "string"
        ? error.name
        : null;
    const errorMessage =
      error instanceof Error
        ? error.message
        : typeof error === "object" && error !== null && "message" in error && typeof error.message === "string"
          ? error.message
          : typeof error === "string"
            ? error
            : null;
    const isAbort =
      errorName === "AbortError" ||
      Boolean(errorMessage && errorMessage.toLowerCase().includes("aborted"));
    const message = isAbort
      ? `Probe timed out after ${service.probeTimeoutMs ?? 5000}ms`
      : errorMessage
        ? errorMessage
          : "Dashboard probe failed.";
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
      lastError: message,
    };
  } finally {
    clearTimeout(timeout);
  }
}

async function getBackendSnapshots(): Promise<BackendSnapshot[]> {
  const litellmApiKey = process.env.ATHANOR_LITELLM_API_KEY?.trim() || "";

  return Promise.all(
    config.inferenceBackends.map(async (backend) => {
      try {
        const headers =
          backend.id === "litellm-proxy" && litellmApiKey
            ? { Authorization: `Bearer ${litellmApiKey}` }
            : undefined;
        const result = await fetchJson(joinUrl(backend.url, "/v1/models"), backendModelsResponseSchema, {
          cache: "no-store",
          headers,
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

async function getAgentDescriptors(): Promise<Array<AgentInfo & { type: string; schedule?: string | null }>> {
  try {
    const result = await fetchJson(joinUrl(config.agentServer.url, "/v1/agents"), agentsResponseSchema, {
      cache: "no-store",
      headers: agentServerHeaders(),
    });
      return result.agents.map((agent): AgentInfo & { type: string; schedule?: string | null } => ({
        id: agent.name,
        name: getAgentName(agent.name),
        description: agent.description,
        icon: getAgentIcon(agent.name),
        tools: agent.tools,
        status: normalizeAgentStatus(agent.status),
        type: agent.type,
        schedule: agent.schedule ?? null,
      }));
  } catch {
    return [];
  }
}

async function getAgentInfos(): Promise<AgentInfo[]> {
  return getAgentDescriptors();
}

function isActiveProjectStatus(status: string) {
  return ["active", "active_development", "operational", "planning"].includes(status);
}

export async function getProjectsSnapshot(): Promise<ProjectsSnapshot> {
  const registryById = new Map<string, (typeof config.projectRegistry)[number]>(
    config.projectRegistry.map((project) => [project.id, project])
  );

  try {
    const result = await fetchJson(joinUrl(config.agentServer.url, "/v1/projects"), projectsResponseSchema, {
      cache: "no-store",
      headers: agentServerHeaders(),
    });

    const liveProjects = Object.entries(result.projects).map(([id, project]): ProjectSnapshot => {
      const registry = registryById.get(id);
      return {
        id,
        name: project.name,
        description: project.description,
        headline: project.headline ?? registry?.headline ?? project.description,
        status: project.status ?? registry?.status ?? "planning",
        kind: project.kind ?? registry?.kind ?? "domain",
        firstClass: project.first_class ?? registry?.firstClass ?? false,
        lens: (project.lens as ProjectSnapshot["lens"] | undefined) ?? registry?.lens ?? "default",
        primaryRoute: project.primary_route ?? registry?.primaryRoute ?? "/backlog",
        externalUrl: registry?.externalUrl ?? project.external_url ?? null,
        agents: project.agents,
        needsCount: project.needs_count,
        constraints: project.constraints,
        operatorChain: project.operators.length > 0 ? project.operators : registry?.operators ?? ["Claude"],
      };
    });

    for (const registry of config.projectRegistry) {
      if (liveProjects.some((project) => project.id === registry.id)) {
        continue;
      }

      liveProjects.push({
        id: registry.id,
        name: registry.name,
        description: registry.headline,
        headline: registry.headline,
        status: registry.status,
        kind: registry.kind,
        firstClass: registry.firstClass,
        lens: registry.lens,
        primaryRoute: registry.primaryRoute,
        externalUrl: registry.externalUrl,
        agents: [],
        needsCount: 0,
        constraints: [],
        operatorChain: registry.operators,
      });
    }

    liveProjects.sort((left, right) => {
      if (left.firstClass !== right.firstClass) {
        return left.firstClass ? -1 : 1;
      }

      return left.name.localeCompare(right.name);
    });

    return {
      generatedAt: nowIso(),
      projects: liveProjects,
    };
  } catch {
    return {
      generatedAt: nowIso(),
      projects: config.projectRegistry.map((project) => ({
        id: project.id,
        name: project.name,
        description: project.headline,
        headline: project.headline,
        status: project.status,
        kind: project.kind,
        firstClass: project.firstClass,
        lens: project.lens,
        primaryRoute: project.primaryRoute,
        externalUrl: project.externalUrl,
        agents: [],
        needsCount: 0,
        constraints: [],
        operatorChain: project.operators,
      })),
    };
  }
}

function normalizeTask(rawTask: RawTask): WorkforceTask {
  const metadata = rawTask.metadata ?? {};
  const status = normalizeTaskStatus(rawTask.status);

  return {
    id: rawTask.id,
    agentId: rawTask.agent,
    prompt: rawTask.prompt,
    priority: normalizePriority(rawTask.priority),
    status,
    createdAt: unixToIso(rawTask.created_at) ?? nowIso(),
    startedAt: unixToIso(rawTask.started_at),
    completedAt: unixToIso(rawTask.completed_at),
    durationMs:
      rawTask.started_at > 0 && rawTask.completed_at > 0
        ? Math.max(0, Math.round((rawTask.completed_at - rawTask.started_at) * 1000))
        : null,
    requiresApproval: Boolean(metadata.requires_approval) || status === "pending_approval",
    source: normalizeText(metadata.source),
    projectId: normalizeText(metadata.project),
    planId: normalizeText(metadata.plan_id),
    rationale: normalizeText(metadata.rationale),
    parentTaskId: normalizeText(rawTask.parent_task_id),
    result: normalizeText(rawTask.result),
    error: normalizeText(rawTask.error),
    stepCount: rawTask.steps.length,
  };
}

function normalizeWorkplanTask(rawTask: z.infer<typeof rawWorkplanTaskSchema>, tasksById: Map<string, WorkforceTask>): WorkplanTask {
  const linkedTask = rawTask.task_id ? tasksById.get(rawTask.task_id) : null;

  return {
    taskId: rawTask.task_id ?? null,
    agentId: rawTask.agent,
    projectId: normalizeText(rawTask.project),
    prompt: rawTask.prompt,
    priority: normalizePriority(rawTask.priority),
    rationale: normalizeText(rawTask.rationale),
    requiresApproval: linkedTask?.requiresApproval ?? false,
  };
}

function normalizeWorkplan(rawPlan: RawWorkplan, tasksById: Map<string, WorkforceTask>): WorkplanSnapshot {
  return {
    planId: rawPlan.plan_id,
    generatedAt: unixToIso(rawPlan.generated_at) ?? nowIso(),
    timeContext: normalizeText(rawPlan.time_context),
    focus: rawPlan.focus ?? "",
    taskCount: rawPlan.task_count,
    tasks: rawPlan.tasks.map((task) => normalizeWorkplanTask(task, tasksById)),
    error: normalizeText(rawPlan.error) ?? undefined,
  };
}

function normalizeCanonicalRunStatus(run: RawOperatorRun): WorkforceTask["status"] {
  const status = String(run.status ?? "").trim().toLowerCase();
  if (status === "running") return "running";
  if (status === "completed") return "completed";
  if (status === "failed") return "failed";
  if (status === "cancelled") return "cancelled";
  if (status === "stale_lease") return "stale_lease";
  if (status === "waiting_approval" || status === "pending_approval") return "pending_approval";
  if (status === "blocked" && (run.approval_pending || (run.approvals ?? []).some((approval) => approval.status === "pending"))) {
    return "pending_approval";
  }
  return "pending";
}

function normalizeBacklogStatus(backlog: RawOperatorBacklog): WorkforceTask["status"] {
  const status = String(backlog.status ?? "").trim().toLowerCase();
  if (status === "waiting_approval") return "pending_approval";
  if (status === "blocked") return backlog.approval_mode !== "none" ? "pending_approval" : "stale_lease";
  if (status === "completed") return "completed";
  if (status === "failed") return "failed";
  if (status === "cancelled" || status === "archived") return "cancelled";
  return "pending";
}

function normalizeOperatorRunTask(rawRun: RawOperatorRun): WorkforceTask {
  const metadata = rawRun.metadata ?? {};
  const startedAt = rawRun.latest_attempt?.heartbeat_at ? unixToIso(rawRun.latest_attempt.heartbeat_at) : null;
  const completedAt = unixToIso(rawRun.completed_at);
  const createdAt = unixToIso(rawRun.created_at) ?? nowIso();
  return {
    id: rawRun.id,
    agentId: rawRun.agent_id || rawRun.runtime_lane || "unknown",
    prompt: rawRun.summary || String(metadata.prompt ?? rawRun.task_id ?? rawRun.id),
    priority: normalizePriority(metadata.priority as string | number | null | undefined),
    status: normalizeCanonicalRunStatus(rawRun),
    createdAt,
    startedAt,
    completedAt,
    durationMs:
      rawRun.completed_at > 0 && rawRun.created_at > 0
        ? Math.max(0, Math.round((rawRun.completed_at - rawRun.created_at) * 1000))
        : null,
    requiresApproval: Boolean(rawRun.approval_pending) || (rawRun.approvals ?? []).some((approval) => approval.status === "pending"),
    source: normalizeText(rawRun.provider_lane || rawRun.policy_class),
    projectId: normalizeText((metadata.project_id as string | undefined) ?? (metadata.scope_id as string | undefined)),
    planId: normalizeText(rawRun.backlog_id),
    rationale: normalizeText(rawRun.workload_class),
    parentTaskId: normalizeText(rawRun.task_id),
    result: normalizeText(String(metadata.result ?? "")),
    error: normalizeText(String(metadata.error ?? "")),
    stepCount: rawRun.step_count,
  };
}

function normalizeBacklogTask(rawBacklog: RawOperatorBacklog): WorkforceTask {
  const metadata = rawBacklog.metadata ?? {};
  const scopeProjectId =
    rawBacklog.scope_type === "project"
      ? normalizeText(rawBacklog.scope_id)
      : normalizeText(metadata.project_id as string | undefined);
  return {
    id: `backlog:${rawBacklog.id}`,
    agentId: rawBacklog.owner_agent || "unknown",
    prompt: rawBacklog.prompt || rawBacklog.title || rawBacklog.id,
    priority: normalizePriority(rawBacklog.priority),
    status: normalizeBacklogStatus(rawBacklog),
    createdAt: unixToIso(rawBacklog.created_at) ?? nowIso(),
    startedAt: null,
    completedAt: unixToIso(rawBacklog.completed_at),
    durationMs: null,
    requiresApproval: rawBacklog.approval_mode !== "none",
    source: normalizeText(rawBacklog.work_class),
    projectId: scopeProjectId,
    planId: rawBacklog.id,
    rationale: normalizeText(rawBacklog.blocking_reason) ?? normalizeText(rawBacklog.title),
    parentTaskId: null,
    result: null,
    error: normalizeText(rawBacklog.blocking_reason),
    stepCount: 0,
  };
}

function buildSyntheticWorkplan(
  backlogItems: RawOperatorBacklog[],
  tasksById: Map<string, WorkforceTask>
): WorkplanSnapshot | null {
  const queued = backlogItems
    .filter((item) => !["completed", "cancelled", "archived"].includes(String(item.status ?? "").toLowerCase()))
    .sort((left, right) => {
      return (
        Number(right.priority ?? 0) - Number(left.priority ?? 0) ||
        (right.updated_at ?? 0) - (left.updated_at ?? 0)
      );
    })
    .slice(0, 8);

  if (queued.length === 0) {
    return null;
  }

  return {
    planId: "canonical-backlog-plan",
    generatedAt: nowIso(),
    timeContext: "canonical operator backlog",
    focus: "Canonical operator backlog",
    taskCount: queued.length,
    tasks: queued.map((item) => {
      const syntheticTaskId = `backlog:${item.id}`;
      const linkedTask = tasksById.get(syntheticTaskId);
      return {
        taskId: linkedTask?.id ?? syntheticTaskId,
        agentId: item.owner_agent || "unknown",
        projectId: item.scope_type === "project" ? normalizeText(item.scope_id) : null,
        prompt: item.prompt || item.title || item.id,
        priority: normalizePriority(item.priority),
        rationale: normalizeText(item.title) ?? normalizeText(item.blocking_reason),
        requiresApproval: item.approval_mode !== "none",
      };
    }),
  };
}

function buildSyntheticGoals(todos: RawOperatorTodo[]): WorkforceGoal[] {
  return todos
    .filter((todo) => !["done", "cancelled", "someday"].includes(String(todo.status ?? "").toLowerCase()))
    .map((todo) => {
      const priority = normalizePriority(todo.priority);
      return {
        id: todo.id,
        text: todo.description || todo.title || todo.id,
        agentId: todo.scope_type === "agent" ? todo.scope_id || "global" : "global",
        priority: priority === "critical" ? "high" : priority,
        createdAt: unixToIso(todo.created_at) ?? nowIso(),
        active: true,
      };
    })
    .sort((left, right) => right.createdAt.localeCompare(left.createdAt));
}

function normalizeInboxNotification(item: RawOperatorInbox): WorkforceNotification {
  const severity = Number(item.severity ?? 1);
  const confidence = severity >= 3 ? 0.95 : severity === 2 ? 0.75 : 0.55;
  const resolved = ["resolved", "converted"].includes(String(item.status ?? "").toLowerCase());
  return {
    id: item.id,
    agentId: String(item.source ?? "operator"),
    action: item.title || item.kind || item.id,
    category: item.kind || "notice",
    confidence,
    description: item.description || item.title || "",
    tier: item.requires_decision ? "ask" : "notify",
    createdAt: unixToIso(item.created_at) ?? nowIso(),
    resolved,
    resolution: resolved ? String(item.status ?? "") : null,
  };
}

function normalizeApprovalNotification(approval: RawOperatorApproval): WorkforceNotification {
  const resolved = String(approval.status ?? "") !== "pending";
  return {
    id: approval.id,
    agentId: approval.task_agent_id || "operator",
    action: approval.requested_action || "approval_request",
    category: "approval",
    confidence: 0.98,
    description: approval.reason || approval.task_prompt || approval.id,
    tier: "ask",
    createdAt: unixToIso(approval.requested_at) ?? nowIso(),
    resolved,
    resolution: resolved ? String(approval.status ?? "") : null,
  };
}

function buildSyntheticSchedules(
  agents: Array<AgentInfo & { type: string; schedule?: string | null }>
): WorkforceScheduleEntry[] {
  return agents
    .filter((agent) => typeof agent.schedule === "string" && agent.schedule.trim().length > 0)
    .map((agent) => ({
      agentId: agent.id,
      intervalSeconds: 0,
      intervalHuman: agent.schedule?.trim() || "event-driven",
      enabled: true,
      lastRunAt: null,
      nextRunInSeconds: 0,
      priority: agent.type === "proactive" ? "normal" : "manual",
    }))
    .sort((left, right) => left.agentId.localeCompare(right.agentId));
}

function normalizeWorkspaceItem(rawItem: RawWorkspaceItem) {
  return {
    id: rawItem.id,
    sourceAgent: rawItem.source_agent,
    content: rawItem.content,
    priority: normalizePriority(rawItem.priority),
    salience: rawItem.salience,
    createdAt: unixToIso(rawItem.created_at) ?? nowIso(),
    ttlSeconds: rawItem.ttl,
    coalition: rawItem.coalition,
    projectId: normalizeText(rawItem.metadata.project),
  };
}

function normalizeConvention(rawConvention: RawConvention) {
  return {
    id: rawConvention.id,
    type: rawConvention.type,
    agentId: rawConvention.agent,
    description: rawConvention.description,
    rule: rawConvention.rule,
    source: rawConvention.source,
    occurrences: rawConvention.occurrences,
    status: rawConvention.status,
    createdAt: unixToIso(rawConvention.created_at) ?? nowIso(),
    confirmedAt: unixToIso(rawConvention.confirmed_at ?? null),
  };
}

function buildProjectPostures(
  projects: ProjectSnapshot[],
  tasks: WorkforceTask[],
  currentPlan: WorkplanSnapshot | null
): ProjectPosture[] {
  return projects.map((project) => {
    const projectTasks = tasks.filter((task) => task.projectId === project.id);
    const plannedTasks = currentPlan?.tasks.filter((task) => task.projectId === project.id).length ?? 0;
    const topAgents = Array.from(
      projectTasks.reduce((counts, task) => {
        counts.set(task.agentId, (counts.get(task.agentId) ?? 0) + 1);
        return counts;
      }, new Map<string, number>())
    )
      .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
      .slice(0, 3)
      .map(([agentId]) => agentId);

    return {
      id: project.id,
      name: project.name,
      status: project.status,
      firstClass: project.firstClass,
      lens: project.lens,
      primaryRoute: project.primaryRoute,
      externalUrl: project.externalUrl,
      needsCount: project.needsCount,
      mappedAgents: project.agents.length,
      totalTasks: projectTasks.length,
      pendingTasks: projectTasks.filter((task) => task.status === "pending").length,
      pendingApprovals: projectTasks.filter((task) => task.status === "pending_approval").length,
      runningTasks: projectTasks.filter((task) => task.status === "running").length,
      completedTasks: projectTasks.filter((task) => task.status === "completed").length,
      failedTasks: projectTasks.filter((task) => task.status === "failed").length,
      plannedTasks,
      operatorChain: project.operatorChain,
      topAgents,
    };
  });
}

function buildWorkforceAgents(
  agents: Array<AgentInfo & { type: string }>,
  tasks: WorkforceTask[],
  trustAgents: z.infer<typeof trustResponseSchema>["agents"]
): WorkforceAgentSnapshot[] {
  return agents
    .map((agent) => {
      const agentTasks = tasks.filter((task) => task.agentId === agent.id);
      const trust = trustAgents[agent.id];

      return {
        id: agent.id,
        name: agent.name,
        description: agent.description,
        icon: agent.icon,
        type: agent.type,
        status: agent.status,
        tools: agent.tools,
        totalTasks: agentTasks.length,
        runningTasks: agentTasks.filter((task) => task.status === "running").length,
        pendingTasks: agentTasks.filter((task) => task.status === "pending" || task.status === "pending_approval").length,
        trustScore: trust?.score ?? null,
        trustGrade: trust?.grade ?? null,
      };
    })
    .sort((left, right) => {
      if (left.status !== right.status) {
        return left.status === "ready" ? -1 : 1;
      }
      return left.name.localeCompare(right.name);
    });
}

function buildTrustEntries(trustAgents: z.infer<typeof trustResponseSchema>["agents"]) {
  return Object.entries(trustAgents)
    .map(([agentId, trust]) => ({
      agentId,
      trustScore: trust.score ?? 0,
      trustGrade: trust.grade ?? null,
      positiveFeedback: trust.feedback?.up ?? 0,
      negativeFeedback: trust.feedback?.down ?? 0,
      totalFeedback: trust.feedback?.total ?? 0,
      escalationCount: trust.escalation?.total ?? 0,
    }))
    .sort((left, right) => right.trustScore - left.trustScore || left.agentId.localeCompare(right.agentId));
}

export async function getWorkforceSnapshot(): Promise<WorkforceSnapshot> {
  if (isDashboardFixtureMode()) {
    return getFixtureWorkforceSnapshot();
  }

  const [
    operatorSummary,
    operatorRunsResult,
    operatorBacklogResult,
    operatorTodosResult,
    operatorInboxResult,
    operatorApprovalsResult,
    trustResult,
    workspaceResult,
    workspaceStatsResult,
    workspaceSubscriptionsResult,
    proposedConventionsResult,
    confirmedConventionsResult,
    improvementResult,
    agentDescriptors,
    projectsSnapshot,
  ] =
    await Promise.all([
      fetchAgentJson("/v1/operator/summary", operatorSummaryResponseSchema, {
        ideas: { total: 0, by_status: {} },
        inbox: { total: 0, by_status: {} },
        todos: { total: 0, by_status: {} },
        backlog: { total: 0, by_status: {} },
        runs: { total: 0, by_status: {} },
        approvals: { total: 0, by_status: {} },
        tasks: {
          total: 0,
          by_status: {},
          pending_approval: 0,
          stale_lease: 0,
          failed_actionable: 0,
          failed_historical_repaired: 0,
          failed_missing_detail: 0,
        },
      }),
      fetchAgentJson("/v1/operator/runs?limit=50", operatorRunsResponseSchema, {
        runs: [],
        count: 0,
      }),
      fetchAgentJson("/v1/operator/backlog?limit=120", operatorBacklogResponseSchema, {
        backlog: [],
        count: 0,
      }),
      fetchAgentJson("/v1/operator/todos?limit=120", operatorTodosResponseSchema, {
        todos: [],
        count: 0,
      }),
      fetchAgentJson("/v1/operator/inbox?limit=120", operatorInboxResponseSchema, {
        items: [],
        count: 0,
      }),
      fetchAgentJson("/v1/operator/approvals?limit=120", operatorApprovalsResponseSchema, {
        approvals: [],
        count: 0,
      }),
      fetchAgentJson("/v1/trust", trustResponseSchema, { agents: {} }),
      fetchAgentJson("/v1/workspace", workspaceResponseSchema, {
        broadcast: [],
        count: 0,
      }),
      fetchAgentJson("/v1/workspace/stats", workspaceStatsResponseSchema, {
        total_items: 0,
        broadcast_items: 0,
        capacity: 7,
        utilization: 0,
        agents_active: {},
        top_item: null,
        competition_running: false,
      }),
      fetchAgentJson("/v1/workspace/subscriptions", workspaceSubscriptionsResponseSchema, {
        subscriptions: {},
        count: 0,
      }),
      fetchAgentJson("/v1/conventions?status=proposed", conventionsResponseSchema, {
        conventions: [],
        count: 0,
        status: "proposed",
      }),
      fetchAgentJson("/v1/conventions", conventionsResponseSchema, {
        conventions: [],
        count: 0,
        status: "confirmed",
      }),
      fetchAgentJson("/v1/improvement/summary", improvementSummaryResponseSchema, {
        total_proposals: 0,
        pending: 0,
        validated: 0,
        deployed: 0,
        failed: 0,
        benchmark_results: 0,
        last_cycle: null,
      }),
      getAgentDescriptors(),
      getProjectsSnapshot(),
    ]);

  const canonicalRunTasks = operatorRunsResult.runs.map(normalizeOperatorRunTask);
  const linkedBacklogIds = new Set(
    operatorRunsResult.runs
      .map((run) => normalizeText(run.backlog_id))
      .filter((value): value is string => value !== null)
  );
  const backlogTasks = operatorBacklogResult.backlog
    .filter((item) => !linkedBacklogIds.has(item.id))
    .map(normalizeBacklogTask);
  const tasks = [...canonicalRunTasks, ...backlogTasks].sort((left, right) => {
    const statusOrder: Record<WorkforceTask["status"], number> = {
      pending_approval: 0,
      running: 1,
      stale_lease: 2,
      pending: 3,
      failed: 4,
      completed: 5,
      cancelled: 6,
    };
    return (
      statusOrder[left.status] - statusOrder[right.status] ||
      right.createdAt.localeCompare(left.createdAt)
      );
    });
  const tasksById = new Map(tasks.map((task) => [task.id, task]));
  const currentPlan = buildSyntheticWorkplan(operatorBacklogResult.backlog, tasksById);
  const history: WorkplanSnapshot[] = [];
  const goals = buildSyntheticGoals(operatorTodosResult.todos);
  const notifications = [
    ...operatorInboxResult.items.map(normalizeInboxNotification),
    ...operatorApprovalsResult.approvals.map(normalizeApprovalNotification),
  ].sort((left, right) => right.createdAt.localeCompare(left.createdAt));
  const workspace = {
    totalItems: workspaceStatsResult.total_items,
    broadcastItems: workspaceStatsResult.broadcast_items,
    capacity: workspaceStatsResult.capacity,
    utilization: workspaceStatsResult.utilization,
    competitionRunning: workspaceStatsResult.competition_running,
    agentsActive: Object.entries(workspaceStatsResult.agents_active)
      .map(([agentId, count]) => ({ agentId, count }))
      .sort((left, right) => right.count - left.count || left.agentId.localeCompare(right.agentId)),
    topItem: workspaceStatsResult.top_item ? normalizeWorkspaceItem(workspaceStatsResult.top_item) : null,
    broadcast: workspaceResult.broadcast.map(normalizeWorkspaceItem),
  };
  const projectPostures = buildProjectPostures(projectsSnapshot.projects, tasks, currentPlan);
  const workforceAgents = buildWorkforceAgents(agentDescriptors, tasks, trustResult.agents);
  const trustEntries = buildTrustEntries(trustResult.agents);
  const subscriptions = Object.values(workspaceSubscriptionsResult.subscriptions)
    .map((subscription) => ({
      agentId: subscription.agent_name,
      keywords: subscription.keywords,
      sourceFilters: subscription.source_filters,
      threshold: subscription.threshold,
      reactPromptTemplate: subscription.react_prompt_template,
    }))
    .sort((left, right) => left.agentId.localeCompare(right.agentId));
  const conventions = {
    proposed: proposedConventionsResult.conventions
      .map(normalizeConvention)
      .sort((left, right) => right.createdAt.localeCompare(left.createdAt)),
    confirmed: confirmedConventionsResult.conventions
      .map(normalizeConvention)
      .sort((left, right) => right.createdAt.localeCompare(left.createdAt)),
  };
  const improvement = {
    totalProposals: improvementResult.total_proposals,
    pending: improvementResult.pending,
    validated: improvementResult.validated,
    deployed: improvementResult.deployed,
    failed: improvementResult.failed,
    benchmarkResults: improvementResult.benchmark_results,
    lastCycle: improvementResult.last_cycle
      ? {
          timestamp: improvementResult.last_cycle.timestamp,
          patternsConsumed: improvementResult.last_cycle.patterns_consumed,
          proposalsGenerated: improvementResult.last_cycle.proposals_generated,
          benchmarks: improvementResult.last_cycle.benchmarks
            ? {
                passed: improvementResult.last_cycle.benchmarks.passed,
                total: improvementResult.last_cycle.benchmarks.total,
                passRate: improvementResult.last_cycle.benchmarks.pass_rate,
              }
            : null,
        }
      : null,
    };
  const trustValues = Object.values(trustResult.agents)
    .map((entry) => entry.score)
    .filter((value): value is number => typeof value === "number");
  const pendingApprovals =
    operatorSummary.approvals.total > 0
      ? operatorSummary.approvals.total
      : tasks.filter((task) => task.status === "pending_approval").length;
  const unreadNotifications =
    operatorSummary.inbox.by_status.new ?? notifications.filter((notification) => !notification.resolved).length;
  const activeGoalCount =
    goals.filter((goal) => goal.active).length || operatorSummary.todos.total || operatorSummary.ideas.total;
  const schedules = buildSyntheticSchedules(agentDescriptors);

  return {
    generatedAt: nowIso(),
    summary: {
      totalTasks: tasks.length,
      pendingTasks: tasks.filter((task) => task.status === "pending").length,
      pendingApprovals,
      runningTasks: tasks.filter((task) => task.status === "running").length,
      completedTasks: tasks.filter((task) => task.status === "completed").length,
      failedTasks: tasks.filter((task) => task.status === "failed").length,
      activeGoals: activeGoalCount,
      unreadNotifications,
      avgTrustScore: average(trustValues),
      workspaceUtilization: workspace.utilization,
      activeProjects: projectPostures.filter((project) => isActiveProjectStatus(project.status)).length,
      queuedProjects: projectPostures.filter(
        (project) => project.pendingTasks + project.pendingApprovals + project.runningTasks > 0
      ).length,
    },
    workplan: {
      current: currentPlan,
      history,
      needsRefill: (operatorSummary.backlog.by_status.ready ?? 0) < WORKPLAN_MIN_PENDING_TASKS,
      schedule: {
        morningRunHourLocal: WORKPLAN_MORNING_HOUR_LOCAL,
        morningRunMinuteLocal: WORKPLAN_MORNING_MINUTE_LOCAL,
        refillIntervalHours: WORKPLAN_REFILL_INTERVAL_HOURS,
        minPendingTasks: WORKPLAN_MIN_PENDING_TASKS,
        nextRunAt: getNextWorkplanRunIso(),
      },
    },
    tasks,
    goals,
    trust: trustEntries,
    notifications,
    workspace,
    subscriptions,
    conventions,
    improvement,
    agents: workforceAgents,
    projects: projectPostures,
    schedules,
  };
}

function buildNodeSummaries(services: ServiceSnapshot[]) {
  return config.nodes.map((node) => {
    const nodeServices = services.filter((service) => service.nodeId === node.id);
    const summary = summarizeServiceStates(nodeServices);
    const averageLatencyMs = average(
      nodeServices.flatMap((service) => (service.latencyMs === null ? [] : [service.latencyMs]))
    );

    return {
      id: node.id,
      name: node.name,
      ip: node.ip,
      role: node.role,
      totalServices: nodeServices.length,
      healthyServices: summary.healthy,
      warningServices: summary.warning,
      degradedServices: summary.degraded,
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
  const summary = summarizeServiceStates(services);
  const slowestService = services
    .filter((service) => service.latencyMs !== null)
    .sort((left, right) => (right.latencyMs ?? 0) - (left.latencyMs ?? 0))[0];

  return {
    generatedAt: nowIso(),
    summary: {
      total: services.length,
      healthy: summary.healthy,
      warning: summary.warning,
      degraded: summary.degraded,
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

export const __testing = {
  checkService,
  deriveServiceState,
  tryParseServiceHealthSnapshot,
  isModelCatalogResponse,
  passThroughHealthyServiceIds,
};

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

  // Cross-reference with LiteLLM health to get per-model availability
  let healthyModels = new Set<string>();
  try {
    const litellmApiKey = process.env.ATHANOR_LITELLM_API_KEY?.trim() || "";
    const litellmUrl = config.services.find(s => s.id === "litellm-proxy")?.url || config.inferenceBackends.find(b => b.id === "litellm-proxy")?.url;
    if (litellmUrl) {
      const resp = await fetch(joinUrl(litellmUrl, "/health"), {
        headers: litellmApiKey ? { Authorization: `Bearer ${litellmApiKey}` } : undefined,
        cache: "no-store",
        signal: AbortSignal.timeout(5000),
      });
      if (resp.ok) {
        const health = await resp.json();
        for (const entry of health?.healthy_endpoints ?? []) {
          if (entry?.model) healthyModels.add(entry.model);
        }
      }
    }
  } catch { /* health check optional */ }

  const models: ModelInventoryEntry[] = backends.flatMap((backend) =>
    backend.models.map((modelId) => ({
      id: modelId,
      backendId: backend.id,
      backend: backend.name,
      target: backend.id,
      description: backend.description,
      available: backend.reachable && (healthyModels.size === 0 || healthyModels.has(modelId)),
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
  gpus: GpuSnapshot[],
  projects: ProjectSnapshot[]
) {
  const alerts: OverviewSnapshot["alerts"] = [];
  const degradedServices = services.filter((service) => isServiceDegraded(service));
  for (const service of degradedServices.slice(0, 3)) {
    alerts.push({
      id: `service-${service.id}`,
      title: service.name,
      description: describeServiceCondition(service),
      tone: service.state === "muted" ? "warning" : "degraded",
      href: `/services?service=${service.id}`,
    });
  }

  const hottest = gpus.find((gpu) => (gpu.temperatureC ?? 0) >= 75);
  if (hottest) {
    alerts.push({
      id: `gpu-${hottest.id}`,
      title: `${hottest.gpuName} is running hot`,
      description: `${hottest.node} is reporting ${formatTemperatureF(hottest.temperatureC)}.`,
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

  const firstClassProjects = projects.filter((project) => project.firstClass);
  if (firstClassProjects.length === 0) {
    alerts.push({
      id: "projects-unavailable",
      title: "Project platform data unavailable",
      description: "The dashboard could not resolve the first-class project registry.",
      tone: "warning",
      href: "/backlog",
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

  const [
    servicesSnapshot,
    servicesHistory,
    gpuSnapshot,
    gpuHistory,
    backends,
    agents,
    projectsSnapshot,
    workforce,
    judgePlane,
    steadyStateFrontDoor,
  ] = await Promise.all([
    getServicesSnapshot(),
    getServicesHistory(window),
    getGpuSnapshot(),
    getGpuHistory(window),
    getBackendSnapshots(),
    getAgentInfos(),
    getProjectsSnapshot(),
    getWorkforceSnapshot(),
    fetchAgentJson("/v1/review/judges?limit=12", judgePlaneSnapshotSchema, fallbackJudgePlaneSnapshot),
    loadSteadyStateFrontDoor(),
  ]);
  const steadyState = steadyStateFrontDoor.snapshot;
  const steadyStateReadStatus = steadyStateFrontDoor.status;

  const generatedAt = nowIso();

  const nodes = servicesSnapshot.nodes.map((node) => {
    const gpuNode = gpuSnapshot.nodes.find((gpu) => gpu.nodeId === node.id);
    return {
      ...node,
      gpuUtilization: gpuNode?.averageUtilization ?? null,
    };
  });

  const alerts = buildAlerts(
    servicesSnapshot.services,
    backends,
    agents,
    gpuSnapshot.gpus,
    projectsSnapshot.projects
  );
  const hotspots = [...gpuSnapshot.gpus].sort((left, right) => (right.utilization ?? -1) - (left.utilization ?? -1)).slice(0, 4);
  const serviceTrend = servicesHistory.aggregate;
  const gpuTrend = gpuHistory.nodes.length > 0
    ? gpuHistory.nodes[0].points.map((point, index) => ({
        timestamp: point.timestamp,
        value: average(gpuHistory.nodes.map((series) => series.points[index]?.value ?? null).filter((value): value is number => value !== null)),
      }))
    : [];
  const navAttention = buildNavAttentionSignals({
    workforce,
    services: servicesSnapshot.services,
    agents,
    judge: judgePlane,
    updatedAt: generatedAt,
  });

  return {
    generatedAt,
    summary: {
      totalServices: servicesSnapshot.summary.total,
      healthyServices: servicesSnapshot.summary.healthy,
      warningServices: servicesSnapshot.summary.warning,
      degradedServices: servicesSnapshot.summary.degraded,
      averageLatencyMs: servicesSnapshot.summary.averageLatencyMs,
      averageGpuUtilization: gpuSnapshot.summary.averageUtilization,
      readyAgents: agents.filter((agent) => agent.status === "ready").length,
      totalAgents: agents.length,
      reachableBackends: backends.filter((backend) => backend.reachable).length,
      totalBackends: backends.length,
      activeProjects: projectsSnapshot.projects.filter((project) => isActiveProjectStatus(project.status)).length,
      firstClassProjects: projectsSnapshot.projects.filter((project) => project.firstClass).length,
    },
    nodes,
    services: servicesSnapshot.services,
    serviceTrend,
    gpuTrend,
    backends,
    agents,
    projects: projectsSnapshot.projects,
    alerts,
    hotspots,
    externalTools: config.externalTools,
    navAttention,
    workforce,
    steadyState,
    steadyStateReadStatus,
  };
}
