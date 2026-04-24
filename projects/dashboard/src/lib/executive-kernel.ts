import { access, readFile } from "node:fs/promises";
import path from "node:path";
import { z } from "zod";
import {
  executiveKernelSummarySchema,
  executionJobProjectionSchema,
  executionProgramProjectionSchema,
  executionResultProjectionSchema,
  executionReviewProjectionSchema,
  executionSessionProjectionSchema,
  governorSnapshotSchema,
  scheduledJobsResponseSchema,
  type BuilderFrontDoorSummary,
  type BuilderExecutionSession,
  type ExecutionJobProjection,
  type ExecutionProgramProjection,
  type ExecutionResultProjection,
  type ExecutionReviewProjection,
  type ExecutionSessionProjection,
  type ExecutiveKernelSummary,
  type GovernorSnapshot,
  type ScheduledJobRecord,
  type SteadyStateSnapshot,
} from "@/lib/contracts";
import { buildBootstrapSyntheticApprovals, type BootstrapProgramsPayload } from "@/lib/bootstrap-approvals";
import { agentServerHeaders, config, joinUrl } from "@/lib/config";
import {
  listBuilderSyntheticApprovals,
  listBuilderSyntheticRuns,
  readBuilderSession,
  readBuilderSummary,
} from "@/lib/builder-store";
import { loadSteadyStateFrontDoor } from "@/lib/operator-frontdoor";

const executiveKernelRegistrySchema = z
  .object({
    version: z.string(),
    updated_at: z.string().optional(),
    status: z.string().optional(),
    source_of_truth: z.string().optional(),
    kernel_mode: z.string(),
    first_live_family: z.string(),
    dispatch_order: z.array(z.string()),
    dispatch_defaults: z.object({
      implementation_lane: z.string(),
      audit_lane: z.string(),
      mechanic_lane: z.string(),
      github_lane: z.string(),
      bulk_lane: z.string(),
      recommendation: z.string().optional(),
    }),
  })
  .passthrough();

const capacityTelemetrySchema = z
  .object({
    capacity_summary: z
      .object({
        harvestable_scheduler_slot_count: z.number().int().nonnegative().default(0),
      })
      .passthrough()
      .default({ harvestable_scheduler_slot_count: 0 }),
    gpu_samples: z
      .array(
        z
          .object({
            gpu_id: z.string().optional(),
            protected_reserve: z.boolean().default(false),
          })
          .passthrough(),
      )
      .default([]),
  })
  .passthrough();

const capabilityLeaderRecordSchema = z
  .object({
    subject_id: z.string(),
    subject_kind: z.string(),
    task_class: z.string(),
    reserve_class: z.string().nullable().optional(),
    capability_score: z.number(),
    demotion_state: z.string().default("healthy"),
  })
  .passthrough();

const capabilitySnapshotSchema = z
  .object({
    version: z.string(),
    generated_at: z.string().optional(),
    source_of_truth: z.string().optional(),
    providers: z.array(capabilityLeaderRecordSchema).default([]),
    local_endpoints: z.array(capabilityLeaderRecordSchema).default([]),
    degraded_subjects: z.array(z.record(z.string(), z.unknown())).default([]),
  })
  .passthrough();

type ExecutiveKernelRegistry = z.infer<typeof executiveKernelRegistrySchema>;
type CapacityTelemetry = z.infer<typeof capacityTelemetrySchema>;
type CapabilitySnapshot = z.infer<typeof capabilitySnapshotSchema>;

interface ExecutiveKernelBuildInput {
  builderFrontDoor: BuilderFrontDoorSummary;
  steadyState: SteadyStateSnapshot | null;
  governor: GovernorSnapshot | null;
  scheduledJobs: ScheduledJobRecord[];
  bootstrapPrograms: BootstrapProgramRecord[];
  registry: ExecutiveKernelRegistry;
  capacityTelemetry: CapacityTelemetry;
  capabilitySnapshot: CapabilitySnapshot | null;
  frontDoorUrl: string;
  updatedAt: string;
  errors?: string[];
}

interface ExecutiveKernelLoadOptions {
  builderFrontDoor?: BuilderFrontDoorSummary;
  steadyState?: SteadyStateSnapshot | null;
}

interface ExecutionProjectionFilters {
  status?: string | null;
  family?: string | null;
}

interface ExecutionJobFilters extends ExecutionProjectionFilters {
  limit?: number | null;
}

interface ExecutionResultFilters extends ExecutionProjectionFilters {
  limit?: number | null;
  outcome?: string | null;
}

interface ExecutionReviewFilters extends ExecutionProjectionFilters {
  limit?: number | null;
}

interface ExecutionReviewFeed {
  available: boolean;
  degraded: boolean;
  source: string;
  detail: string | null;
  reviews: ExecutionReviewProjection[];
  count: number;
}

const bootstrapProgramSliceCountsSchema = z
  .object({
    total: z.number().int().nonnegative().default(0),
    queued: z.number().int().nonnegative().default(0),
    active: z.number().int().nonnegative().default(0),
    blocked: z.number().int().nonnegative().default(0),
    completed: z.number().int().nonnegative().default(0),
  })
  .passthrough();

const bootstrapProgramRecordSchema = z
  .object({
    id: z.string(),
    label: z.string(),
    objective: z.string().optional().default(""),
    phase_scope: z.string().optional().default(""),
    status: z.string(),
    current_family: z.string().optional().default(""),
    next_slice_id: z.string().optional().default(""),
    recommended_host_id: z.string().optional().default(""),
    waiting_on_approval_family: z.string().optional().default(""),
    waiting_on_approval_slice_id: z.string().optional().default(""),
    pending_integrations: z.number().int().nonnegative().optional().default(0),
    slice_counts: bootstrapProgramSliceCountsSchema.default({
      total: 0,
      queued: 0,
      active: 0,
      blocked: 0,
      completed: 0,
    }),
    created_at: z.string().optional().default(""),
    updated_at: z.string().optional().default(""),
  })
  .passthrough();

const bootstrapProgramsResponseSchema = z
  .object({
    programs: z.array(bootstrapProgramRecordSchema).default([]),
  })
  .passthrough();

const bootstrapSliceRecordSchema = z
  .object({
    id: z.string(),
    program_id: z.string(),
    family: z.string(),
    objective: z.string(),
    status: z.string(),
    host_id: z.string().optional().default(""),
    current_ref: z.string().optional().default(""),
    worktree_path: z.string().optional().default(""),
    files_touched: z.array(z.string()).optional().default([]),
    validation_status: z.string().optional().default("pending"),
    open_risks: z.array(z.string()).optional().default([]),
    next_step: z.string().optional().default(""),
    stop_reason: z.string().optional().default(""),
    resume_instructions: z.string().optional().default(""),
    depth_level: z.number().int().optional().default(1),
    priority: z.number().int().optional().default(3),
    phase_scope: z.string().optional().default(""),
    continuation_mode: z.string().optional().default(""),
    metadata: z.record(z.string(), z.unknown()).optional().default({}),
    catalog_slice_id: z.string().optional().default(""),
    family_seed_slice_id: z.string().optional().default(""),
    execution_mode: z.string().optional().default(""),
    completion_evidence_paths: z.array(z.string()).optional().default([]),
    blocking_packet_id: z.string().optional().default(""),
    claimed_at: z.string().optional().default(""),
    completed_at: z.string().optional().default(""),
    created_at: z.string().optional().default(""),
    updated_at: z.string().optional().default(""),
  })
  .passthrough();

const bootstrapSlicesResponseSchema = z
  .object({
    slices: z.array(bootstrapSliceRecordSchema).default([]),
  })
  .passthrough();

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

const operatorApprovalsResponseSchema = z
  .object({
    approvals: z.array(rawOperatorApprovalSchema).default([]),
    count: z.number().int().nonnegative().default(0),
  })
  .passthrough();

type BootstrapProgramRecord = z.infer<typeof bootstrapProgramRecordSchema>;
type BootstrapSliceRecord = z.infer<typeof bootstrapSliceRecordSchema>;
type RawOperatorApproval = z.infer<typeof rawOperatorApprovalSchema>;

const DEFAULT_EXECUTIVE_KERNEL_REGISTRY: ExecutiveKernelRegistry = {
  version: "2026-04-17.1",
  updated_at: "2026-04-17T00:00:00.000Z",
  status: "active",
  source_of_truth: "config/automation-backbone/executive-kernel-registry.json",
  kernel_mode: "hybrid_sessions_plus_programs",
  first_live_family: "builder",
  dispatch_order: [
    "privacy_gate",
    "execution_family",
    "reserve_class",
    "adapter",
    "verification_and_recovery",
  ],
  dispatch_defaults: {
    implementation_lane: "codex_cloudsafe",
    audit_lane: "gemini_audit_cloudsafe",
    mechanic_lane: "aider_repo_mechanic",
    github_lane: "github_async_delegate",
    bulk_lane: "sovereign_bulk",
    recommendation:
      "Use owned local capacity first when quality is sufficient, protect interactive and creative reserves, burn subscription windows intentionally before reset, and leave metered APIs for overflow only.",
  },
};

function nowIso() {
  return new Date().toISOString();
}

function normalizedString(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function executiveKernelRegistryPaths() {
  return [
    path.resolve(process.cwd(), "config", "automation-backbone", "executive-kernel-registry.json"),
    path.resolve(process.cwd(), "..", "..", "config", "automation-backbone", "executive-kernel-registry.json"),
  ];
}

function capacityTelemetryPaths() {
  return [
    path.resolve(process.cwd(), "reports", "truth-inventory", "capacity-telemetry.json"),
    path.resolve(process.cwd(), "..", "..", "reports", "truth-inventory", "capacity-telemetry.json"),
  ];
}

function capabilitySnapshotPaths() {
  return [
    path.resolve(process.cwd(), "reports", "truth-inventory", "capability-intelligence.json"),
    path.resolve(process.cwd(), "..", "..", "reports", "truth-inventory", "capability-intelligence.json"),
  ];
}

async function readJsonFromCandidates<T>(candidates: string[], schema: z.ZodSchema<T>): Promise<T | null> {
  for (const candidate of candidates) {
    try {
      await access(candidate);
    } catch {
      continue;
    }

    try {
      const raw = await readFile(candidate, "utf-8");
      return schema.parse(JSON.parse(raw));
    } catch {
      return null;
    }
  }

  return null;
}

async function fetchOptionalAgentJson<T>(agentPath: string, schema: z.ZodSchema<T>): Promise<T | null> {
  const result = await fetchOptionalAgentJsonEnvelope(agentPath, schema);
  return result.data;
}

async function fetchOptionalAgentJsonEnvelope<T>(
  agentPath: string,
  schema: z.ZodSchema<T>,
): Promise<{ available: boolean; data: T | null }> {
  try {
    const response = await fetch(joinUrl(config.agentServer.url, agentPath), {
      cache: "no-store",
      headers: agentServerHeaders(),
      signal: AbortSignal.timeout(8_000),
    });
    if (!response.ok) {
      return {
        available: false,
        data: null,
      };
    }
    return {
      available: true,
      data: schema.parse(await response.json()),
    };
  } catch {
    return {
      available: false,
      data: null,
    };
  }
}

function isActiveExecutionProgram(program: ExecutionProgramProjection) {
  if (program.paused) {
    return false;
  }
  return ["running", "active", "scheduled", "queued", "pending_approval", "waiting_approval"].includes(program.current_state);
}

function isRunningExecutionProgram(program: ExecutionProgramProjection) {
  return ["running", "active"].includes(program.current_state);
}

function buildCurrentSession(builderFrontDoor: BuilderFrontDoorSummary) {
  const current = builderFrontDoor.current_session;
  if (!current) {
    return null;
  }
  return {
    family: "builder",
    ...current,
  };
}

export function buildExecutionSessionProjections(
  builderFrontDoor: BuilderFrontDoorSummary,
  bootstrapSlices: BootstrapSliceRecord[] = [],
  filters: ExecutionProjectionFilters = {},
): ExecutionSessionProjection[] {
  const deduped = new Map<string, BuilderFrontDoorSummary["sessions"][number]>();
  for (const session of [builderFrontDoor.current_session, ...builderFrontDoor.sessions].filter(
    (candidate): candidate is BuilderFrontDoorSummary["sessions"][number] => candidate !== null,
  )) {
    deduped.set(session.id, session);
  }

  const projectedBuilderSessions = [...deduped.values()]
    .filter((session) => !filters.family || filters.family === "builder")
    .filter((session) => !filters.status || session.status === filters.status)
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
    .map((session) =>
      executionSessionProjectionSchema.parse({
        id: session.id,
        family: "builder",
        source: "builder_front_door",
        title: session.title,
        status: session.status,
        primary_adapter: session.primary_adapter,
        current_route: session.current_route,
        verification_status: session.verification_status,
        pending_approval_count: session.pending_approval_count,
        artifact_count: session.artifact_count,
        resumable_handle: session.resumable_handle,
        shadow_mode: session.shadow_mode,
        fallback_state: session.fallback_state,
        updated_at: session.updated_at,
      }),
    );

  const projectedBootstrapSlices = bootstrapSlices
    .filter((slice) => !filters.family || filters.family === "bootstrap_takeover")
    .map((slice) => {
      const projectedStatus = mapBootstrapSliceStatus(slice.status);
      return {
        projectedStatus,
        projection: executionSessionProjectionSchema.parse({
          id: slice.id,
          family: "bootstrap_takeover",
          source: "bootstrap_slice",
          title: slice.objective,
          status: projectedStatus,
          primary_adapter: slice.execution_mode || slice.continuation_mode || slice.host_id || "bootstrap_supervisor",
          current_route: slice.family,
          verification_status: mapBootstrapSliceVerificationStatus(slice.validation_status),
          pending_approval_count:
            projectedStatus === "waiting_approval" || Boolean(slice.blocking_packet_id || slice.metadata.blocking_packet_id)
              ? 1
              : 0,
          artifact_count: slice.completion_evidence_paths.length,
          resumable_handle: slice.worktree_path || null,
          shadow_mode: false,
          fallback_state: slice.stop_reason || null,
          updated_at: slice.updated_at || slice.created_at || nowIso(),
        }),
      };
    })
    .filter((slice) => !filters.status || slice.projectedStatus === filters.status)
    .sort((left, right) => right.projection.updated_at.localeCompare(left.projection.updated_at))
    .map((slice) => slice.projection);

  return [...projectedBuilderSessions, ...projectedBootstrapSlices].sort((left, right) =>
    right.updated_at.localeCompare(left.updated_at),
  );
}

function projectBuilderExecutionSession(session: BuilderExecutionSession): ExecutionSessionProjection {
  return executionSessionProjectionSchema.parse({
    id: session.id,
    family: "builder",
    source: "builder_front_door",
    title: session.title,
    status: session.status,
    primary_adapter: session.route_decision.primary_adapter,
    current_route: session.current_route ?? session.route_decision.route_label,
    verification_status: session.verification_state.status,
    pending_approval_count: session.approvals.filter((approval) => approval.status === "pending").length,
    artifact_count: session.latest_result_packet?.artifacts.length ?? 0,
    resumable_handle: session.latest_result_packet?.resumable_handle ?? null,
    shadow_mode: session.shadow_mode,
    fallback_state: session.fallback_state,
    updated_at: session.updated_at,
  });
}

function mapBootstrapSliceStatus(status: string) {
  switch (status) {
    case "waiting_approval":
      return "waiting_approval" as const;
    case "claimed":
    case "active":
    case "running":
      return "running" as const;
    case "completed":
    case "ready_for_takeover_check":
      return "completed" as const;
    case "blocked":
      return "blocked" as const;
    case "failed":
      return "failed" as const;
    case "cancelled":
      return "cancelled" as const;
    case "draft":
      return "draft" as const;
    case "queued":
    case "pending":
    default:
      return "queued" as const;
  }
}

function mapBootstrapSliceVerificationStatus(status: string) {
  switch (status) {
    case "passed":
      return "passed" as const;
    case "failed":
      return "failed" as const;
    case "blocked":
      return "blocked" as const;
    case "running":
      return "running" as const;
    case "pending":
    default:
      return "planned" as const;
  }
}

function parseExecutionTimestamp(value: string | number | null | undefined) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim().length > 0) {
    const numeric = Number(value);
    if (Number.isFinite(numeric) && numeric > 0) {
      return numeric;
    }
    const parsed = Date.parse(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return 0;
}

export function buildExecutionProgramProjections(
  scheduledJobs: ScheduledJobRecord[],
  bootstrapPrograms: BootstrapProgramRecord[] = [],
  filters: ExecutionProjectionFilters = {},
): ExecutionProgramProjection[] {
  const projectedScheduled = scheduledJobs
    .filter((job) => !filters.family || job.job_family === filters.family)
    .filter((job) => !filters.status || job.current_state === filters.status)
    .map((job) => ({
      projection: executionProgramProjectionSchema.parse({
        id: job.id,
        family: job.job_family,
        source: "scheduled_job",
        title: job.title,
        cadence: job.cadence,
        trigger_mode: job.trigger_mode,
        current_state: job.current_state,
        last_outcome: job.last_outcome,
        owner_agent: job.owner_agent,
        deep_link: job.deep_link,
        last_run: job.last_run,
        next_run: job.next_run,
        paused: Boolean(job.paused),
      }),
      sort_timestamp: job.next_run ?? job.last_run ?? "",
    }));

  const projectedBootstrap = bootstrapPrograms
    .filter((program) => !filters.family || filters.family === "bootstrap_takeover")
    .filter((program) => !filters.status || program.status === filters.status)
    .map((program) => ({
      projection: executionProgramProjectionSchema.parse({
        id: program.id,
        family: "bootstrap_takeover",
        source: "bootstrap_program",
        title: program.label,
        cadence: "event_driven",
        trigger_mode: "bootstrap_supervisor",
        current_state: program.status,
        last_outcome:
          program.status === "waiting_approval"
            ? "approval_required"
            : ["completed", "ready_for_takeover_check"].includes(program.status)
              ? "success"
              : ["blocked", "failed"].includes(program.status)
                ? program.status
                : "pending",
        owner_agent: "bootstrap_supervisor",
        deep_link: `/bootstrap?program=${encodeURIComponent(program.id)}`,
        last_run: null,
        next_run: null,
        paused: program.status === "paused",
      }),
      sort_timestamp: program.updated_at || program.created_at || "",
    }));

  const stateRank = (state: string) => {
    if (state === "waiting_approval") {
      return 0;
    }
    if (state === "running" || state === "active") {
      return 1;
    }
    if (state === "queued" || state === "scheduled" || state === "pending") {
      return 2;
    }
    if (state === "blocked" || state === "failed") {
      return 3;
    }
    if (state === "paused") {
      return 4;
    }
    return 5;
  };

  return [...projectedScheduled, ...projectedBootstrap]
    .sort((left, right) => {
      const rankDelta = stateRank(left.projection.current_state) - stateRank(right.projection.current_state);
      if (rankDelta !== 0) {
        return rankDelta;
      }
      return right.sort_timestamp.localeCompare(left.sort_timestamp);
    })
    .map((item) => item.projection);
}

type BuilderSyntheticRunRecord = Awaited<ReturnType<typeof listBuilderSyntheticRuns>>[number];
type BuilderSyntheticApprovalRecord = Awaited<ReturnType<typeof listBuilderSyntheticApprovals>>[number];

export function buildExecutionJobProjections(
  builderRuns: BuilderSyntheticRunRecord[],
  bootstrapSlices: BootstrapSliceRecord[] = [],
  filters: ExecutionJobFilters = {},
): ExecutionJobProjection[] {
  const projectedBuilderRuns = builderRuns
    .filter((run) => !filters.family || filters.family === "builder")
    .filter((run) => !filters.status || run.latest_attempt.status === filters.status)
    .map((run) =>
      ({
        projection: executionJobProjectionSchema.parse({
          id: run.latest_attempt.id,
          family: "builder",
          source: "builder_front_door",
          owner_kind: "session",
          owner_id: run.task_id,
          run_id: run.id,
          status: run.latest_attempt.status,
          adapter_id: run.agent_id,
          provider_or_endpoint_id: run.provider_lane,
          runtime_host: run.latest_attempt.runtime_host,
          summary: run.summary,
          created_at: run.created_at,
          updated_at: run.updated_at,
          completed_at: run.completed_at,
          heartbeat_at: run.latest_attempt.heartbeat_at,
          approval_pending: run.approval_pending,
          deep_link: `/builder?session=${encodeURIComponent(run.task_id)}`,
        }),
        sort_timestamp: run.updated_at,
      }),
    );

  const projectedBootstrapSlices = bootstrapSlices
    .filter((slice) => !filters.family || filters.family === "bootstrap_takeover")
    .map((slice) => {
      const projectedStatus = mapBootstrapSliceStatus(slice.status);
      return {
        projectedStatus,
        projection: executionJobProjectionSchema.parse({
          id: slice.id,
          family: "bootstrap_takeover",
          source: "bootstrap_slice",
          owner_kind: "program",
          owner_id: slice.program_id,
          run_id: slice.id,
          status: projectedStatus,
          adapter_id: slice.execution_mode || slice.continuation_mode || "bootstrap_supervisor",
          provider_or_endpoint_id: slice.host_id || slice.continuation_mode || "bootstrap_supervisor",
          runtime_host: slice.host_id || "bootstrap-supervisor",
          summary: slice.next_step || slice.objective,
          created_at: parseExecutionTimestamp(slice.created_at),
          updated_at: parseExecutionTimestamp(slice.updated_at),
          completed_at: parseExecutionTimestamp(slice.completed_at),
          heartbeat_at: parseExecutionTimestamp(slice.claimed_at) || parseExecutionTimestamp(slice.updated_at),
          approval_pending:
            projectedStatus === "waiting_approval" || Boolean(slice.blocking_packet_id || slice.metadata.blocking_packet_id),
          deep_link: `/bootstrap?program=${encodeURIComponent(slice.program_id)}&slice=${encodeURIComponent(slice.id)}`,
        }),
        sort_timestamp: parseExecutionTimestamp(slice.updated_at) || parseExecutionTimestamp(slice.created_at),
      };
    })
    .filter((slice) => !filters.status || slice.projectedStatus === filters.status);

  return [...projectedBootstrapSlices, ...projectedBuilderRuns]
    .sort((left, right) => right.sort_timestamp - left.sort_timestamp)
    .slice(0, filters.limit && filters.limit > 0 ? filters.limit : builderRuns.length + bootstrapSlices.length)
    .map((item) => item.projection);
}

export function buildExecutionResultProjections(
  builderSessions: BuilderExecutionSession[],
  filters: ExecutionResultFilters = {},
): ExecutionResultProjection[] {
  return builderSessions
    .filter((session) => !filters.family || filters.family === "builder")
    .filter((session) => !filters.status || session.status === filters.status)
    .filter((session): session is BuilderExecutionSession & { latest_result_packet: NonNullable<BuilderExecutionSession["latest_result_packet"]> } =>
      session.latest_result_packet !== null,
    )
    .filter((session) => !filters.outcome || session.latest_result_packet.outcome === filters.outcome)
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
    .slice(0, filters.limit && filters.limit > 0 ? filters.limit : builderSessions.length)
    .map((session) =>
      executionResultProjectionSchema.parse({
        id: `builder-result:${session.id}`,
        family: "builder",
        source: "builder_front_door",
        owner_kind: "session",
        owner_id: session.id,
        related_run_id: `builder-run-${session.id}`,
        status: session.status,
        outcome: session.latest_result_packet.outcome,
        summary: session.latest_result_packet.summary,
        artifact_count: session.latest_result_packet.artifacts.length,
        artifacts: session.latest_result_packet.artifacts,
        files_changed: session.latest_result_packet.files_changed,
        validation: session.latest_result_packet.validation,
        remaining_risks: session.latest_result_packet.remaining_risks,
        resumable_handle: session.latest_result_packet.resumable_handle,
        recovery_gate: session.latest_result_packet.recovery_gate,
        verification_status: session.verification_state.status,
        updated_at: session.updated_at,
        deep_link: `/builder?session=${encodeURIComponent(session.id)}`,
        metadata: {
          builder_session_id: session.id,
          linked_surfaces: session.linked_surfaces,
          shadow_mode: session.shadow_mode,
        },
      }),
    );
}

export function buildExecutionReviewProjections(
  builderApprovals: BuilderSyntheticApprovalRecord[],
  bootstrapProgramsPayload: BootstrapProgramsPayload | null = null,
  operatorApprovals: RawOperatorApproval[] = [],
  filters: ExecutionReviewFilters = {},
): ExecutionReviewProjection[] {
  const bootstrapApprovals = buildBootstrapSyntheticApprovals(bootstrapProgramsPayload, filters.status ?? null);

  const projectedBuilderApprovals = builderApprovals
    .filter((approval) => !filters.family || filters.family === "builder")
    .map((approval) =>
      executionReviewProjectionSchema.parse({
        id: approval.id,
        family: "builder",
        source: "builder_front_door",
        owner_kind: "session",
        owner_id: String(approval.related_task_id ?? ""),
        related_run_id: String(approval.related_run_id ?? ""),
        related_task_id: String(approval.related_task_id ?? ""),
        requested_action: approval.requested_action,
        privilege_class: approval.privilege_class,
        reason: approval.reason,
        status: approval.status,
        requested_at: Number(approval.requested_at ?? 0),
        task_prompt: approval.task_prompt,
        task_agent_id: approval.task_agent_id,
        task_priority: approval.task_priority,
        task_status: approval.task_status,
        deep_link: `/builder?session=${encodeURIComponent(String(approval.related_task_id ?? ""))}`,
        metadata: approval.metadata ?? {},
      }),
    );

  const projectedBootstrapApprovals = bootstrapApprovals
    .filter((approval) => !filters.family || filters.family === "bootstrap_takeover")
    .map((approval) => {
      const programId =
        typeof approval.metadata?.bootstrap_program_id === "string"
          ? String(approval.metadata.bootstrap_program_id)
          : String(approval.related_run_id ?? "").replace(/^bootstrap-program:/, "");
      const sliceId = String(approval.related_task_id ?? "");
      return executionReviewProjectionSchema.parse({
        id: approval.id,
        family: "bootstrap_takeover",
        source: "bootstrap_program",
        owner_kind: "program",
        owner_id: programId,
        related_run_id: String(approval.related_run_id ?? ""),
        related_task_id: sliceId,
        requested_action: approval.requested_action,
        privilege_class: approval.privilege_class,
        reason: approval.reason,
        status: approval.status,
        requested_at: Number(approval.requested_at ?? 0),
        task_prompt: approval.task_prompt,
        task_agent_id: approval.task_agent_id,
        task_priority: approval.task_priority,
        task_status: approval.task_status,
        deep_link: `/bootstrap?program=${encodeURIComponent(programId)}&slice=${encodeURIComponent(sliceId)}`,
        metadata: approval.metadata ?? {},
      });
    });

  const projectedOperatorApprovals = operatorApprovals
    .map((approval) => {
      const metadata = approval.metadata ?? {};
      const inferredTaskId =
        normalizedString(approval.related_task_id) ||
        (approval.id.startsWith("approval:") ? approval.id.slice("approval:".length) : "");
      const family =
        normalizedString(metadata.family) ||
        normalizedString(metadata.execution_family) ||
        normalizedString(metadata.route_family) ||
        (() => {
          switch (normalizedString(approval.task_agent_id).toLowerCase()) {
            case "coding-agent":
              return "builder";
            case "research-agent":
              return "research_audit";
            case "knowledge-agent":
              return "knowledge_memory";
            case "home-agent":
              return "home_ops";
            case "media-agent":
              return "media_ops";
            case "stash-agent":
              return "stash_ops";
            case "creative-agent":
              return "creative_sovereign";
            case "data-curator":
              return "personal_data";
            case "general-assistant":
              return "maintenance";
            default:
              return "operator_task";
          }
        })();

      return executionReviewProjectionSchema.parse({
        id: approval.id,
        family,
        source: normalizedString(metadata.source) || "operator_approval",
        owner_kind:
          normalizedString(metadata.owner_kind) ||
          (inferredTaskId ? "task" : normalizedString(approval.related_run_id) ? "run" : "approval"),
        owner_id: inferredTaskId || normalizedString(approval.related_run_id) || approval.id,
        related_run_id: normalizedString(approval.related_run_id) || approval.id,
        related_task_id: inferredTaskId,
        requested_action: normalizedString(approval.requested_action) || "approve",
        privilege_class: normalizedString(approval.privilege_class) || "admin",
        reason:
          normalizedString(approval.reason) ||
          normalizedString(approval.task_prompt) ||
          `Approval required for ${approval.id}`,
        status: normalizedString(approval.status) || "pending",
        requested_at: Math.max(0, Math.floor(Number(approval.requested_at ?? 0))),
        task_prompt:
          normalizedString(approval.task_prompt) ||
          normalizedString(approval.reason) ||
          approval.id,
        task_agent_id: normalizedString(approval.task_agent_id) || "operator",
        task_priority: normalizedString(approval.task_priority) || "normal",
        task_status: normalizedString(approval.task_status) || "pending",
        deep_link:
          normalizedString(metadata.deep_link) ||
          (normalizedString(approval.id)
            ? `/review?selection=${encodeURIComponent(approval.id)}`
            : normalizedString(approval.related_run_id)
              ? `/runs?selection=${encodeURIComponent(normalizedString(approval.related_run_id))}`
              : "/review"),
        metadata,
      });
    })
    .filter((review) => !filters.family || review.family === filters.family)
    .filter((review) => !filters.status || review.status === filters.status);

  return [...projectedOperatorApprovals, ...projectedBuilderApprovals, ...projectedBootstrapApprovals]
    .sort((left, right) => right.requested_at - left.requested_at)
    .slice(
      0,
      filters.limit && filters.limit > 0
        ? filters.limit
        : projectedOperatorApprovals.length + projectedBuilderApprovals.length + projectedBootstrapApprovals.length,
    );
}

function capabilitySort(
  left: { capability_score: number; demotion_state: string },
  right: { capability_score: number; demotion_state: string },
) {
  const leftPenalty = left.demotion_state === "healthy" ? 0 : left.demotion_state === "degraded" ? 1 : 2;
  const rightPenalty = right.demotion_state === "healthy" ? 0 : right.demotion_state === "degraded" ? 1 : 2;
  if (leftPenalty !== rightPenalty) {
    return leftPenalty - rightPenalty;
  }
  return right.capability_score - left.capability_score;
}

function selectCapabilityLeader(
  records: CapabilitySnapshot["providers"] | CapabilitySnapshot["local_endpoints"],
  taskClass: string,
) {
  const matches = records.filter((record) => record.task_class === taskClass);
  const candidates = matches.length > 0 ? matches : records;
  if (candidates.length === 0) {
    return null;
  }
  const sorted = [...candidates].sort(capabilitySort);
  const leader = sorted[0];
  return {
    subject_id: leader.subject_id,
    task_class: leader.task_class,
    capability_score: leader.capability_score,
    demotion_state: leader.demotion_state,
    reserve_class: leader.reserve_class ?? null,
  };
}

export function buildExecutiveKernelSummary(input: ExecutiveKernelBuildInput): ExecutiveKernelSummary {
  const currentSession = buildCurrentSession(input.builderFrontDoor);
  const executionPrograms = buildExecutionProgramProjections(input.scheduledJobs, input.bootstrapPrograms);
  const activePrograms = executionPrograms.filter(isActiveExecutionProgram);
  const runningPrograms = activePrograms.filter(isRunningExecutionProgram);
  const protectedReserveCount = input.capacityTelemetry.gpu_samples.filter((sample) => sample.protected_reserve).length;
  const harvestableSlotCount =
    input.governor?.capacity.local_compute?.harvestable_scheduler_slot_count ??
    input.capacityTelemetry.capacity_summary.harvestable_scheduler_slot_count ??
    0;
  const openHarvestSlotCount = input.governor?.capacity.local_compute?.open_harvest_slots.length ?? 0;
  const activeFamily =
    currentSession?.family ??
    activePrograms[0]?.family ??
    input.steadyState?.currentWork?.laneFamily ??
    input.registry.first_live_family;
  const currentPrograms = activePrograms.slice(0, 3).map((program) => ({
    id: program.id,
    family: program.family,
    title: program.title,
    current_state: program.current_state,
    last_outcome: program.last_outcome,
    deep_link: program.deep_link,
  }));
  const errors = [
    ...(input.errors ?? []),
    ...(input.builderFrontDoor.degraded ? [input.builderFrontDoor.detail ?? "Builder front door degraded."] : []),
    ...(!input.governor ? ["Governor snapshot unavailable."] : []),
  ];
  const capabilityPosture = {
    implementation: input.capabilitySnapshot
      ? selectCapabilityLeader(input.capabilitySnapshot.providers, "multi_file_implementation")
      : null,
    audit: input.capabilitySnapshot ? selectCapabilityLeader(input.capabilitySnapshot.providers, "repo_wide_audit") : null,
    local_endpoint: input.capabilitySnapshot
      ? selectCapabilityLeader(input.capabilitySnapshot.local_endpoints, "multi_file_implementation")
      : null,
    degraded_subject_count: input.capabilitySnapshot?.degraded_subjects.length ?? 0,
    source_of_truth: input.capabilitySnapshot?.source_of_truth ?? "reports/truth-inventory/capability-intelligence.json",
  };

  return executiveKernelSummarySchema.parse({
    available: true,
    degraded: errors.length > 0,
    detail: errors[0] ?? null,
    updated_at: input.updatedAt,
    kernel_mode: input.registry.kernel_mode,
    first_live_family: input.registry.first_live_family,
    active_family: activeFamily,
    active_session_count: input.builderFrontDoor.active_count,
    active_program_count: activePrograms.length,
    running_program_count: runningPrograms.length,
    local_protected_reserve_count: protectedReserveCount,
    local_harvestable_slot_count: harvestableSlotCount,
    open_harvest_slot_count: openHarvestSlotCount,
    provider_reserve_posture: input.governor?.capacity.provider_reserve.posture ?? "unknown",
    constrained_provider_count: input.governor?.capacity.provider_reserve.constrained_count ?? 0,
    current_session: currentSession,
    current_programs: currentPrograms,
    dispatch: {
      decision_order: input.registry.dispatch_order,
      implementation_lane: input.registry.dispatch_defaults.implementation_lane,
      audit_lane: input.registry.dispatch_defaults.audit_lane,
      mechanic_lane: input.registry.dispatch_defaults.mechanic_lane,
      github_lane: input.registry.dispatch_defaults.github_lane,
      bulk_lane: input.registry.dispatch_defaults.bulk_lane,
      recommendation:
        input.registry.dispatch_defaults.recommendation ||
        DEFAULT_EXECUTIVE_KERNEL_REGISTRY.dispatch_defaults.recommendation,
    },
    capability_posture: capabilityPosture,
    front_door_url: input.frontDoorUrl,
  });
}

export async function loadExecutiveKernelSummary(
  options: ExecutiveKernelLoadOptions = {},
): Promise<ExecutiveKernelSummary> {
  const [builderFrontDoor, steadyStateResult, governor, scheduledJobsResponse, bootstrapProgramsResponse, registry, capacityTelemetry, capabilityRouteSnapshot, capabilityFileSnapshot] =
    await Promise.all([
      options.builderFrontDoor ? Promise.resolve(options.builderFrontDoor) : readBuilderSummary(),
      options.steadyState !== undefined
        ? Promise.resolve({ snapshot: options.steadyState })
        : loadSteadyStateFrontDoor(),
      fetchOptionalAgentJson("/v1/governor", governorSnapshotSchema),
      fetchOptionalAgentJson("/v1/tasks/scheduled?limit=12", scheduledJobsResponseSchema),
      fetchOptionalAgentJson("/v1/bootstrap/programs", bootstrapProgramsResponseSchema),
      readJsonFromCandidates(executiveKernelRegistryPaths(), executiveKernelRegistrySchema),
      readJsonFromCandidates(capacityTelemetryPaths(), capacityTelemetrySchema),
      fetchOptionalAgentJson("/v1/models/capabilities", capabilitySnapshotSchema),
      readJsonFromCandidates(capabilitySnapshotPaths(), capabilitySnapshotSchema),
    ]);
  const capabilitySnapshot = capabilityRouteSnapshot ?? capabilityFileSnapshot;

  const errors: string[] = [];
  if (!registry) {
    errors.push("Executive kernel registry unavailable.");
  }
  if (!capacityTelemetry) {
    errors.push("Capacity telemetry unavailable.");
  }
  if (!scheduledJobsResponse) {
    errors.push("Scheduled jobs unavailable.");
  }
  if (!capabilitySnapshot) {
    errors.push("Capability posture unavailable.");
  }

  return buildExecutiveKernelSummary({
    builderFrontDoor,
    steadyState: steadyStateResult.snapshot ?? null,
    governor,
    scheduledJobs: scheduledJobsResponse?.jobs ?? [],
    bootstrapPrograms: bootstrapProgramsResponse?.programs ?? [],
    registry: registry ?? DEFAULT_EXECUTIVE_KERNEL_REGISTRY,
    capacityTelemetry:
      capacityTelemetry ??
      capacityTelemetrySchema.parse({
        capacity_summary: { harvestable_scheduler_slot_count: 0 },
        gpu_samples: [],
      }),
    capabilitySnapshot,
    frontDoorUrl: config.frontDoor.canonicalUrl,
    updatedAt: builderFrontDoor.updated_at || nowIso(),
    errors,
  });
}

export async function loadExecutionSessions(
  filters: ExecutionProjectionFilters = {},
): Promise<ExecutionSessionProjection[]> {
  const [builderFrontDoor, bootstrapSlicesResponse] = await Promise.all([
    readBuilderSummary(),
    fetchOptionalAgentJson("/v1/bootstrap/slices?limit=500", bootstrapSlicesResponseSchema),
  ]);
  return buildExecutionSessionProjections(builderFrontDoor, bootstrapSlicesResponse?.slices ?? [], filters);
}

export async function loadExecutionSession(sessionId: string): Promise<ExecutionSessionProjection | null> {
  const builderSession = await readBuilderSession(sessionId);
  if (builderSession) {
    return projectBuilderExecutionSession(builderSession);
  }

  const bootstrapSlicesResponse = await fetchOptionalAgentJson("/v1/bootstrap/slices?limit=500", bootstrapSlicesResponseSchema);
  const bootstrapSlice = bootstrapSlicesResponse?.slices.find((slice) => slice.id === sessionId);
  if (bootstrapSlice) {
    return buildExecutionSessionProjections(
      {
        available: true,
        degraded: false,
        detail: null,
        updated_at: bootstrapSlice.updated_at || bootstrapSlice.created_at || nowIso(),
        session_count: 0,
        active_count: 0,
        pending_approval_count: 0,
        recent_artifact_count: 0,
        shared_pressure: {
          pending_review_count: 0,
          actionable_result_count: 0,
          current_session_pending_review_count: 0,
          current_session_actionable_result_count: 0,
          current_session_status: "ready",
          current_session_needs_sync: false,
        },
        current_session: null,
        sessions: [],
      },
      [bootstrapSlice],
    )[0] ?? null;
  }

  return null;
}

export async function loadExecutionPrograms(
  filters: ExecutionProjectionFilters = {},
): Promise<ExecutionProgramProjection[]> {
  const [scheduledJobsResponse, bootstrapProgramsResponse] = await Promise.all([
    fetchOptionalAgentJson("/v1/tasks/scheduled?limit=48", scheduledJobsResponseSchema),
    fetchOptionalAgentJson("/v1/bootstrap/programs", bootstrapProgramsResponseSchema),
  ]);

  return buildExecutionProgramProjections(
    scheduledJobsResponse?.jobs ?? [],
    bootstrapProgramsResponse?.programs ?? [],
    filters,
  );
}

export async function loadExecutionJobs(
  filters: ExecutionJobFilters = {},
): Promise<ExecutionJobProjection[]> {
  const limit = filters.limit && filters.limit > 0 ? filters.limit : 50;
  const [builderRuns, bootstrapSlicesResponse] = await Promise.all([
    !filters.family || filters.family === "builder" ? listBuilderSyntheticRuns(filters.status ?? null, limit) : Promise.resolve([]),
    fetchOptionalAgentJson("/v1/bootstrap/slices?limit=500", bootstrapSlicesResponseSchema),
  ]);

  return buildExecutionJobProjections(builderRuns, bootstrapSlicesResponse?.slices ?? [], filters);
}

export async function loadExecutionResults(
  filters: ExecutionResultFilters = {},
): Promise<ExecutionResultProjection[]> {
  const limit = filters.limit && filters.limit > 0 ? filters.limit : 50;
  const builderRuns =
    !filters.family || filters.family === "builder"
      ? await listBuilderSyntheticRuns(filters.status ?? null, limit)
      : [];
  const builderSessions = (
    await Promise.all(builderRuns.map((run) => readBuilderSession(run.task_id)))
  ).filter((session): session is BuilderExecutionSession => session !== null);

  return buildExecutionResultProjections(builderSessions, filters);
}

export async function loadExecutionReviews(
  filters: ExecutionReviewFilters = {},
): Promise<ExecutionReviewProjection[]> {
  const feed = await loadExecutionReviewFeed(filters);
  return feed.reviews;
}

export async function loadExecutionReviewFeed(
  filters: ExecutionReviewFilters = {},
): Promise<ExecutionReviewFeed> {
  const searchParams = new URLSearchParams();
  if (filters.status) {
    searchParams.set("status", filters.status);
  }
  const limit = filters.limit && filters.limit > 0 ? filters.limit : 500;
  searchParams.set("limit", String(limit));
  const approvalsPath = `/v1/operator/approvals?${searchParams.toString()}`;
  const [builderApprovals, bootstrapProgramsPayload] = await Promise.all([
    listBuilderSyntheticApprovals(filters.status ?? null),
    fetchOptionalAgentJson("/v1/bootstrap/programs", bootstrapProgramsResponseSchema),
  ]);
  const operatorApprovalsPayload = await fetchOptionalAgentJsonEnvelope(
    approvalsPath,
    operatorApprovalsResponseSchema,
  );

  const reviews = buildExecutionReviewProjections(
    builderApprovals,
    (bootstrapProgramsPayload as BootstrapProgramsPayload | null) ?? null,
    operatorApprovalsPayload.data?.approvals ?? [],
    filters,
  );

  return {
    available: operatorApprovalsPayload.available,
    degraded: !operatorApprovalsPayload.available,
    source: "shared_execution_kernel",
    detail: operatorApprovalsPayload.available ? null : "Operator approval feed unavailable from agent server.",
    reviews,
    count: reviews.length,
  };
}

export async function loadExecutionReview(reviewId: string): Promise<ExecutionReviewProjection | null> {
  const reviews = await loadExecutionReviews({ limit: 500 });
  return reviews.find((review) => review.id === reviewId) ?? null;
}
