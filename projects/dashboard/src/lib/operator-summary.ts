import {
  listBuilderSyntheticInboxItems,
  listBuilderSyntheticRuns,
  listBuilderSyntheticTodos,
  readBuilderSummary,
} from "@/lib/builder-store";
import { summarizeBuilderKernelPressure } from "@/lib/builder-kernel-pressure";
import {
  buildExecutionJobProjections,
  buildExecutionSessionProjections,
  loadExecutiveKernelSummary,
  loadExecutionResults,
  loadExecutionReviewFeed,
} from "@/lib/executive-kernel";
import { loadBlockerMap } from "@/lib/blocker-map";
import { loadBlockerExecutionPlan } from "@/lib/blocker-execution-plan";
import { loadContinuityController } from "@/lib/continuity-controller";
import { loadSteadyStateFrontDoor } from "@/lib/operator-frontdoor";
import { summarizeScheduledJobPressure } from "@/lib/scheduled-job-posture";
import { loadAutonomousValueProof } from "@/lib/autonomous-value-proof";
import { loadOperatorMobileSummary } from "@/lib/operator-mobile-summary";
import { loadValueThroughputScorecard } from "@/lib/value-throughput";
import { proxyAgentJson } from "@/lib/server-agent";

const TASKS_FALLBACK = {
  pending_approval: 0,
  failed_actionable: 0,
  stale_lease: 0,
  failed_historical_repaired: 0,
};

const EMPTY_BUILDER_FRONT_DOOR = {
  available: true,
  degraded: false,
  detail: null,
  updated_at: "",
  session_count: 0,
  active_count: 0,
  pending_approval_count: 0,
  recent_artifact_count: 0,
  shared_pressure: {
    pending_review_count: 0,
    actionable_result_count: 0,
    current_session_pending_review_count: 0,
    current_session_actionable_result_count: 0,
    current_session_status: "ready" as const,
    current_session_needs_sync: false,
  },
  current_session: null,
  sessions: [],
};

type SummarySection = {
  total?: number;
  by_status?: Record<string, number>;
};

type TaskSummarySection = SummarySection & {
  pending_approval?: number;
  stale_lease?: number;
  failed_actionable?: number;
  failed_historical_repaired?: number;
  failed_missing_detail?: number;
};

function normalizeSection(section: unknown): Required<SummarySection> {
  const candidate = section && typeof section === "object" ? (section as SummarySection) : {};
  return {
    total: typeof candidate.total === "number" ? candidate.total : 0,
    by_status:
      candidate.by_status && typeof candidate.by_status === "object"
        ? { ...(candidate.by_status as Record<string, number>) }
        : {},
  };
}

function mergeStatusCounts(
  base: Record<string, number>,
  additions: Record<string, number>,
): Record<string, number> {
  const merged = { ...base };
  for (const [status, count] of Object.entries(additions)) {
    merged[status] = (merged[status] ?? 0) + count;
  }
  return merged;
}

function countByStatus<T extends { status?: string }>(items: T[]): Record<string, number> {
  return items.reduce<Record<string, number>>((counts, item) => {
    const status = typeof item.status === "string" && item.status ? item.status : "unknown";
    counts[status] = (counts[status] ?? 0) + 1;
    return counts;
  }, {});
}

function mapExecutionTaskStatus(status: string) {
  return status === "waiting_approval" ? "pending_approval" : status;
}

function countExecutionTaskStatuses(items: Array<{ status: string }>) {
  return items.reduce<Record<string, number>>((counts, item) => {
    const status = mapExecutionTaskStatus(item.status);
    counts[status] = (counts[status] ?? 0) + 1;
    return counts;
  }, {});
}

function mergeSummarySection(section: unknown, additions: Record<string, number>) {
  const normalized = normalizeSection(section);
  return {
    total: normalized.total + Object.values(additions).reduce((sum, value) => sum + value, 0),
    by_status: mergeStatusCounts(normalized.by_status, additions),
  };
}

function mergeTaskSummarySection(
  section: unknown,
  additions: {
    byStatus: Record<string, number>;
    pendingApproval: number;
    failedActionable: number;
  },
) {
  const normalized = section && typeof section === "object" ? (section as TaskSummarySection) : {};
  const baseSection = normalizeSection(section);
  return {
    total: baseSection.total + Object.values(additions.byStatus).reduce((sum, value) => sum + value, 0),
    by_status: mergeStatusCounts(baseSection.by_status, additions.byStatus),
    pending_approval:
      (typeof normalized.pending_approval === "number" ? normalized.pending_approval : 0) + additions.pendingApproval,
    stale_lease: typeof normalized.stale_lease === "number" ? normalized.stale_lease : 0,
    failed_actionable:
      (typeof normalized.failed_actionable === "number" ? normalized.failed_actionable : 0) + additions.failedActionable,
    failed_historical_repaired:
      typeof normalized.failed_historical_repaired === "number" ? normalized.failed_historical_repaired : 0,
    failed_missing_detail:
      typeof normalized.failed_missing_detail === "number" ? normalized.failed_missing_detail : 0,
  };
}

function sumStatusCounts(counts: Record<string, number>) {
  return Object.values(counts).reduce((sum, value) => sum + value, 0);
}

function extractScheduledJobsForPressure(payload: unknown) {
  if (!payload || typeof payload !== "object" || !Array.isArray((payload as { jobs?: unknown[] }).jobs)) {
    return [];
  }

  return (payload as { jobs: unknown[] }).jobs
    .map((job) => {
      if (!job || typeof job !== "object") {
        return null;
      }

      const candidate = job as Record<string, unknown>;
      return {
        id: typeof candidate.id === "string" ? candidate.id : "",
        last_execution_mode:
          typeof candidate.last_execution_mode === "string" ? candidate.last_execution_mode : null,
        last_execution_plane:
          typeof candidate.last_execution_plane === "string" ? candidate.last_execution_plane : null,
        last_admission_classification:
          typeof candidate.last_admission_classification === "string"
            ? candidate.last_admission_classification
            : null,
        last_backlog_id: typeof candidate.last_backlog_id === "string" ? candidate.last_backlog_id : null,
      };
    })
    .filter(
      (
        job,
      ): job is {
        id: string;
        last_execution_mode: string | null;
        last_execution_plane: string | null;
        last_admission_classification: string | null;
        last_backlog_id: string | null;
      } => Boolean(job?.id),
    );
}

export async function loadOperatorSummaryPayload(): Promise<Record<string, unknown>> {
  const [
    response,
    bootstrapSlicesResponse,
    steadyStateFrontDoor,
    builderFrontDoor,
    builderRuns,
    builderInboxItems,
    builderTodos,
    sharedPendingReviewFeed,
    builderExecutionResults,
    scheduledJobsResponse,
    autonomousValueProofRead,
    valueThroughputRead,
    blockerMapRead,
    blockerExecutionPlanRead,
    continuityControllerRead,
    operatorMobileSummaryRead,
  ] = await Promise.all([
    proxyAgentJson("/v1/operator/summary", undefined, "Failed to fetch operator work summary", 25_000),
    proxyAgentJson("/v1/bootstrap/slices?limit=500", undefined, "Failed to fetch bootstrap slices"),
    loadSteadyStateFrontDoor(),
    readBuilderSummary(),
    listBuilderSyntheticRuns(null, 1_000),
    listBuilderSyntheticInboxItems(),
    listBuilderSyntheticTodos(),
    loadExecutionReviewFeed({ status: "pending", limit: 500 }),
    loadExecutionResults({ family: "builder", limit: 500 }),
    proxyAgentJson("/v1/tasks/scheduled?limit=120", undefined, "Failed to fetch scheduled jobs"),
    loadAutonomousValueProof(),
    loadValueThroughputScorecard(),
    loadBlockerMap(),
    loadBlockerExecutionPlan(),
    loadContinuityController(),
    loadOperatorMobileSummary(),
  ]);
  const bootstrapSlicesPayload =
    bootstrapSlicesResponse.ok
      ? ((await bootstrapSlicesResponse.json().catch(() => ({}))) as { slices?: Array<Record<string, unknown>> })
      : null;
  const bootstrapSlices: Parameters<typeof buildExecutionSessionProjections>[1] = Array.isArray(
    bootstrapSlicesPayload?.slices,
  )
    ? (bootstrapSlicesPayload.slices as Parameters<typeof buildExecutionSessionProjections>[1])
    : [];
  const steadyState = steadyStateFrontDoor.snapshot;
  const steadyStateStatus = steadyStateFrontDoor.status;
  const executiveKernel = await loadExecutiveKernelSummary({
    builderFrontDoor,
    steadyState,
  });
  const builderRunStatusCounts = countByStatus(builderRuns);
  const builderInboxStatusCounts = countByStatus(builderInboxItems);
  const builderTodoStatusCounts = countByStatus(builderTodos);
  const normalizedBootstrapSlices = bootstrapSlices ?? [];
  const bootstrapExecutionSessions = buildExecutionSessionProjections(
    {
      ...EMPTY_BUILDER_FRONT_DOOR,
      updated_at: builderFrontDoor.updated_at,
    },
    normalizedBootstrapSlices,
    { family: "bootstrap_takeover" },
  );
  const bootstrapExecutionJobs = buildExecutionJobProjections([], normalizedBootstrapSlices, {
    family: "bootstrap_takeover",
    limit: normalizedBootstrapSlices.length || 500,
  });
  const bootstrapRunStatusCounts = countByStatus(bootstrapExecutionJobs);
  const bootstrapTaskStatusCounts = countExecutionTaskStatuses(bootstrapExecutionSessions);
  const sharedPendingReviewStatusCounts = countByStatus(sharedPendingReviewFeed.reviews);
  const localPendingReviewStatusCounts = countByStatus(
    sharedPendingReviewFeed.reviews.filter((review) => ["builder", "bootstrap_takeover"].includes(review.family)),
  );
  const localPendingApprovalCount = sumStatusCounts(localPendingReviewStatusCounts);
  const builderFailureResultStatusCounts = countByStatus(
    builderExecutionResults.filter((result) => ["failed", "blocked", "cancelled"].includes(result.status)),
  );
  const builderFailureResultTaskIds = new Set(
    builderExecutionResults
      .filter((result) => ["failed", "blocked", "cancelled"].includes(result.status))
      .map((result) => result.owner_id),
  );
  const builderFallbackFailureStatusCounts = countByStatus(
    builderRuns.filter(
      (run) =>
        ["failed", "blocked", "cancelled"].includes(run.status) && !builderFailureResultTaskIds.has(run.task_id),
    ),
  );
  const builderFailureStatusCounts = mergeStatusCounts(
    builderFailureResultStatusCounts,
    builderFallbackFailureStatusCounts,
  );
  const bootstrapFailureStatusCounts = Object.fromEntries(
    Object.entries(bootstrapTaskStatusCounts).filter(([status]) =>
      ["failed", "blocked", "cancelled"].includes(status),
    ),
  );
  const bootstrapFailedActionableCount = sumStatusCounts(bootstrapFailureStatusCounts);
  const builderFailedActionableCount = sumStatusCounts(builderFailureStatusCounts);
  const builderFrontDoorWithSharedPressure = {
    ...builderFrontDoor,
    shared_pressure: summarizeBuilderKernelPressure(
      builderFrontDoor,
      sharedPendingReviewFeed.reviews,
      builderExecutionResults,
    ),
  };
  const scheduledJobsPayload =
    scheduledJobsResponse.ok ? await scheduledJobsResponse.json().catch(() => ({})) : null;
  const scheduled = summarizeScheduledJobPressure(extractScheduledJobsForPressure(scheduledJobsPayload));
  const autonomousValueProof = autonomousValueProofRead.proof;
  const valueThroughput = valueThroughputRead.scorecard;
  const blockerMap = blockerMapRead.blockerMap;
  const blockerExecutionPlan = blockerExecutionPlanRead.blockerExecutionPlan;
  const continuityController = continuityControllerRead.continuityController;
  const projectFactory = operatorMobileSummaryRead.summary?.projectFactory ?? null;
  const localTaskStatusCounts = Object.fromEntries(
    Object.entries({
      ...(localPendingApprovalCount > 0 ? { pending_approval: localPendingApprovalCount } : {}),
      ...builderFailureStatusCounts,
      ...bootstrapFailureStatusCounts,
    }).filter(([, count]) => count > 0),
  );

  const payload = (await response.json()) as Record<string, unknown>;
  if (response.status >= 500) {
    return {
      available: false,
      degraded: true,
      source: "agent-server",
      detail: "Failed to fetch operator work summary",
      inbox: mergeSummarySection(undefined, builderInboxStatusCounts),
      todos: mergeSummarySection(undefined, builderTodoStatusCounts),
      runs: mergeSummarySection(undefined, mergeStatusCounts(builderRunStatusCounts, bootstrapRunStatusCounts)),
      approvals: mergeSummarySection(undefined, sharedPendingReviewStatusCounts),
      scheduled,
      autonomousValueProof,
      autonomousValueProofStatus: autonomousValueProofRead.status,
      valueThroughput,
      valueThroughputStatus: valueThroughputRead.status,
      blockerMap,
      blockerMapStatus: blockerMapRead.status,
      blockerExecutionPlan,
      blockerExecutionPlanStatus: blockerExecutionPlanRead.status,
      continuityController,
      continuityControllerStatus: continuityControllerRead.status,
      projectFactory,
      projectFactoryStatus: operatorMobileSummaryRead.status,
      tasks: mergeTaskSummarySection(TASKS_FALLBACK, {
        byStatus: localTaskStatusCounts,
        pendingApproval: localPendingApprovalCount,
        failedActionable: builderFailedActionableCount + bootstrapFailedActionableCount,
      }),
      steadyState,
      steadyStateStatus,
      builderFrontDoor: builderFrontDoorWithSharedPressure,
      executiveKernel,
    };
  }

  return {
    ...payload,
    inbox: mergeSummarySection(payload.inbox, builderInboxStatusCounts),
    todos: mergeSummarySection(payload.todos, builderTodoStatusCounts),
    runs: mergeSummarySection(payload.runs, mergeStatusCounts(builderRunStatusCounts, bootstrapRunStatusCounts)),
    approvals: sharedPendingReviewFeed.available
      ? mergeSummarySection(undefined, sharedPendingReviewStatusCounts)
      : mergeSummarySection(payload.approvals, sharedPendingReviewStatusCounts),
    scheduled,
    autonomousValueProof,
    autonomousValueProofStatus: autonomousValueProofRead.status,
    valueThroughput,
    valueThroughputStatus: valueThroughputRead.status,
    blockerMap,
    blockerMapStatus: blockerMapRead.status,
    blockerExecutionPlan,
    blockerExecutionPlanStatus: blockerExecutionPlanRead.status,
    continuityController,
    continuityControllerStatus: continuityControllerRead.status,
    projectFactory,
    projectFactoryStatus: operatorMobileSummaryRead.status,
    tasks: mergeTaskSummarySection(payload.tasks, {
      byStatus: localTaskStatusCounts,
      pendingApproval: localPendingApprovalCount,
      failedActionable: builderFailedActionableCount + bootstrapFailedActionableCount,
    }),
    source: typeof payload.source === "string" ? payload.source : "agent-server",
    steadyState,
    steadyStateStatus,
    builderFrontDoor: builderFrontDoorWithSharedPressure,
    executiveKernel,
  };
}
