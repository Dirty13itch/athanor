import type {
  AgentInfo,
  BuilderFrontDoorSummary,
  JudgePlaneSnapshot,
  NavAttentionPersistenceRecord,
  NavAttentionPersistenceState,
  NavAttentionSignal,
  NavAttentionSource,
  NavAttentionTier,
  ServiceSnapshot,
  WorkforceNotification,
  WorkforceSnapshot,
} from "@/lib/contracts";
import { getBuilderKernelSharedPressure } from "@/lib/builder-kernel-pressure";

export type { NavAttentionPersistenceRecord, NavAttentionPersistenceState } from "@/lib/contracts";

const CORE_OPERATOR_SERVICE_IDS = new Set([
  "dashboard",
  "agent-server",
  "litellm-proxy",
  "qdrant",
  "neo4j",
  "prometheus",
]);

const V1_ATTENTION_ROUTES = [
  "/",
  "/operator",
  "/builder",
  "/runs",
  "/inbox",
  "/review",
  "/services",
  "/backlog",
  "/agents",
] as const;

export const NAV_ATTENTION_HOT_MS = 90_000;
export const NAV_ATTENTION_SETTLED_MS = 6 * 60_000;

export interface NavAttentionPresentation {
  signal: NavAttentionSignal | null;
  tier: NavAttentionTier;
  displayTier: NavAttentionTier;
  reason: string | null;
  source: NavAttentionSource | null;
  count: number | null;
  showCount: boolean;
  animateSweep: boolean;
  pulseIndicator: boolean;
  settled: boolean;
  acknowledged: boolean;
  activeSurface: boolean;
}

function buildSignature(
  routeHref: string,
  source: NavAttentionSource,
  tier: NavAttentionTier,
  count: number | null,
  identifiers: string[]
) {
  return [routeHref, source, tier, count ?? "none", ...identifiers.filter(Boolean)].join("|");
}

function createSignal(
  routeHref: string,
  tier: NavAttentionTier,
  source: NavAttentionSource,
  reason: string,
  updatedAt: string,
  count: number | null = null,
  identifiers: string[] = []
): NavAttentionSignal {
  return {
    routeHref,
    tier,
    count,
    reason,
    source,
    updatedAt,
    signature: buildSignature(routeHref, source, tier, count, identifiers),
  };
}

function createNoneSignal(routeHref: string, updatedAt: string): NavAttentionSignal {
  return createSignal(routeHref, "none", "clear", "No immediate operator action.", updatedAt, null, []);
}

function byNewestId<T extends { id: string; createdAt?: string }>(items: T[]) {
  return [...items].sort((left, right) => {
    const leftValue = left.createdAt ?? "";
    const rightValue = right.createdAt ?? "";
    return rightValue.localeCompare(leftValue) || left.id.localeCompare(right.id);
  });
}

function getPendingApprovalTasks(workforce: WorkforceSnapshot) {
  return byNewestId(
    workforce.tasks.filter((task) => task.status === "pending_approval" && Boolean(task.reviewId))
  );
}

function getFailedResultTasks(workforce: WorkforceSnapshot) {
  return byNewestId(workforce.tasks.filter((task) => task.status === "failed" && Boolean(task.resultId)));
}

function getRunsSignal(workforce: WorkforceSnapshot): NavAttentionSignal {
  const updatedAt = workforce.generatedAt;
  const approvals = getPendingApprovalTasks(workforce);
  if (approvals.length > 0) {
    return createSignal(
      "/runs",
      "urgent",
      "pending_approvals",
      approvals.length === 1 ? "1 run needs approval." : `${approvals.length} runs need approval.`,
      updatedAt,
      approvals.length,
      approvals.map((task) => task.reviewId ?? task.id)
    );
  }

  const failed = getFailedResultTasks(workforce);
  if (failed.length > 0) {
    return createSignal(
      "/runs",
      "action",
      "failed_tasks",
      failed.length === 1 ? "1 run failed and needs review." : `${failed.length} runs failed and need review.`,
      updatedAt,
      failed.length,
      failed.map((task) => task.resultId ?? task.id)
    );
  }

  const queued = byNewestId(
    workforce.tasks.filter((task) => task.status === "pending" || task.status === "running")
  );
  if (queued.length > 0) {
    return createSignal(
      "/runs",
      "watch",
      "queued_work",
      queued.length === 1 ? "1 run is active in the queue." : `${queued.length} runs are active in the queue.`,
      updatedAt,
      queued.length,
      queued.map((task) => task.id)
    );
  }

  return createNoneSignal("/runs", updatedAt);
}

function getOperatorDecisionSignal(
  routeHref: "/" | "/operator",
  workforce: WorkforceSnapshot,
): NavAttentionSignal {
  const updatedAt = workforce.generatedAt;
  const approvals = getPendingApprovalTasks(workforce);
  if (approvals.length > 0) {
    return createSignal(
      routeHref,
      "urgent",
      "pending_approvals",
      approvals.length === 1
        ? "1 operator decision is waiting for approval."
        : `${approvals.length} operator decisions are waiting for approval.`,
      updatedAt,
      approvals.length,
      approvals.map((task) => task.reviewId ?? task.id),
    );
  }

  const failed = getFailedResultTasks(workforce);
  if (failed.length > 0) {
    return createSignal(
      routeHref,
      "action",
      "failed_tasks",
      failed.length === 1
        ? "1 failed run still needs operator review."
        : `${failed.length} failed runs still need operator review.`,
      updatedAt,
      failed.length,
      failed.map((task) => task.resultId ?? task.id),
    );
  }

  const active = byNewestId(
    workforce.tasks.filter((task) => task.status === "pending" || task.status === "running"),
  );
  if (active.length > 0) {
    return createSignal(
      routeHref,
      "watch",
      "queued_work",
      active.length === 1
        ? "1 governed lane is actively moving."
        : `${active.length} governed lanes are actively moving.`,
      updatedAt,
      active.length,
      active.map((task) => task.id),
    );
  }

  return createNoneSignal(routeHref, updatedAt);
}

function getBuilderSignal(builder: BuilderFrontDoorSummary, updatedAt: string): NavAttentionSignal {
  const sharedPressure = getBuilderKernelSharedPressure(builder);
  if (builder.degraded) {
    return createSignal(
      "/builder",
      "action",
      "builder_feed_degraded",
      builder.detail ?? "Builder front door is degraded.",
      updatedAt,
      builder.session_count,
      [String(builder.session_count)],
    );
  }

  const current = builder.current_session;
  if (!current) {
    return createNoneSignal("/builder", updatedAt);
  }

  if (sharedPressure.current_session_status === "result_attention") {
    return createSignal(
      "/builder",
      "urgent",
      "builder_failed",
      `${current.title} needs builder review.`,
      updatedAt,
      1,
      [current.id, current.verification_status, current.fallback_state ?? "none"],
    );
  }

  if (sharedPressure.current_session_status === "needs_sync") {
    return createSignal(
      "/builder",
      "action",
      "builder_needs_sync",
      "Builder status and shared review or result evidence are out of sync.",
      updatedAt,
      1,
      [current.id, current.status, sharedPressure.current_session_status],
    );
  }

  if (sharedPressure.current_session_status === "review_required") {
    return createSignal(
      "/builder",
      "action",
      "builder_pending_approval",
      sharedPressure.current_session_pending_review_count === 1
        ? "1 builder session is waiting for review."
        : `${sharedPressure.current_session_pending_review_count} builder reviews are waiting.`,
      updatedAt,
      sharedPressure.current_session_pending_review_count,
      [current.id, sharedPressure.current_session_status],
    );
  }

  if (sharedPressure.current_session_status === "active") {
    return createSignal(
      "/builder",
      "watch",
      "builder_active",
      `${current.title} is active on ${current.primary_adapter}.`,
      updatedAt,
      1,
      [current.id, current.status, current.resumable_handle ?? "none"],
    );
  }

  return createNoneSignal("/builder", updatedAt);
}

function getInboxSignal(workforce: WorkforceSnapshot): NavAttentionSignal {
  const updatedAt = workforce.generatedAt;
  const unresolved = byNewestId(workforce.notifications.filter((notification) => !notification.resolved));
  const pendingApprovals = unresolved.filter((notification) => notification.tier === "ask");
  if (pendingApprovals.length > 0) {
    return createSignal(
      "/inbox",
      "urgent",
      "critical_notifications",
      pendingApprovals.length === 1 ? "1 inbox item is waiting for approval." : `${pendingApprovals.length} inbox items are waiting for approval.`,
      updatedAt,
      pendingApprovals.length,
      pendingApprovals.map((notification) => notification.id)
    );
  }

  const actionable = unresolved.filter((notification) => notification.tier === "notify");
  if (actionable.length > 0) {
    return createSignal(
      "/inbox",
      "action",
      "actionable_notifications",
      actionable.length === 1 ? "1 inbox item needs a check." : `${actionable.length} inbox items need a check.`,
      updatedAt,
      actionable.length,
      actionable.map((notification) => notification.id)
    );
  }

  const informational = unresolved.filter((notification) => notification.tier === "act");
  if (informational.length > 0 || workforce.summary.unreadNotifications > 0) {
    const count = informational.length > 0 ? informational.length : workforce.summary.unreadNotifications;
    return createSignal(
      "/inbox",
      "watch",
      "informational_notifications",
      count === 1 ? "1 inbox item is unread." : `${count} inbox items are unread.`,
      updatedAt,
      count,
      (informational.length > 0 ? informational : unresolved).map((notification) => notification.id)
    );
  }

  return createNoneSignal("/inbox", updatedAt);
}

function getReviewSignal(
  judge: Pick<JudgePlaneSnapshot, "generated_at" | "summary"> | null
): NavAttentionSignal {
  const updatedAt = judge?.generated_at ?? new Date().toISOString();
  const pendingQueue = judge?.summary.pending_review_queue ?? 0;
  const reviewRequired = judge?.summary.review_required ?? 0;
  if (pendingQueue > 0 || reviewRequired > 0) {
    const count = pendingQueue > 0 ? pendingQueue : reviewRequired;
    return createSignal(
      "/review",
      "urgent",
      "pending_review_queue",
      count === 1 ? "1 review item is waiting." : `${count} review items are waiting.`,
      updatedAt,
      count,
      [String(pendingQueue), String(reviewRequired)]
    );
  }

  const recentVerdicts = judge?.summary.recent_verdicts ?? 0;
  if (recentVerdicts > 0) {
    return createSignal(
      "/review",
      "watch",
      "review_activity",
      recentVerdicts === 1 ? "1 fresh review result landed." : `${recentVerdicts} fresh review results landed.`,
      updatedAt,
      recentVerdicts,
      [String(recentVerdicts)]
    );
  }

  return createNoneSignal("/review", updatedAt);
}

function getServiceSignal(services: ServiceSnapshot[], updatedAt: string): NavAttentionSignal {
  const degraded = services.filter((service) => {
    const status = service.healthSnapshot?.status;
    return status ? status !== "healthy" : !service.healthy;
  });
  const degradedCore = degraded.filter((service) => CORE_OPERATOR_SERVICE_IDS.has(service.id));
  if (degradedCore.length > 0) {
    return createSignal(
      "/services",
      "urgent",
      "degraded_core_services",
      degradedCore.length === 1
        ? `${degradedCore[0]?.name ?? "Core service"} is degraded.`
        : `${degradedCore.length} core services are degraded.`,
      updatedAt,
      degradedCore.length,
      degradedCore.map((service) => service.id)
    );
  }

  if (degraded.length > 0) {
    return createSignal(
      "/services",
      "action",
      "degraded_services",
      degraded.length === 1
        ? `${degraded[0]?.name ?? "Service"} is degraded.`
        : `${degraded.length} services are degraded.`,
      updatedAt,
      degraded.length,
      degraded.map((service) => service.id)
    );
  }

  return createNoneSignal("/services", updatedAt);
}

function getBacklogSignal(workforce: WorkforceSnapshot): NavAttentionSignal {
  const updatedAt = workforce.generatedAt;
  if (workforce.workplan.needsRefill) {
    return createSignal(
      "/backlog",
      "action",
      "workplan_refill",
      "The backlog needs refill or operator steering.",
      updatedAt,
      null,
      [String(workforce.summary.pendingTasks), String(workforce.summary.queuedProjects)]
    );
  }

  if (workforce.summary.queuedProjects > 0 || workforce.summary.activeGoals > 0) {
    const count = workforce.summary.queuedProjects > 0 ? workforce.summary.queuedProjects : null;
    return createSignal(
      "/backlog",
      "watch",
      "planning_backlog",
      workforce.summary.queuedProjects > 0
        ? `${workforce.summary.queuedProjects} projects have backlog pressure.`
        : "Backlog pressure exists, but nothing is blocked.",
      updatedAt,
      count,
      [String(workforce.summary.queuedProjects), String(workforce.summary.activeGoals)]
    );
  }

  return createNoneSignal("/backlog", updatedAt);
}

function getAgentsSignal(
  agents: AgentInfo[],
  workforce: WorkforceSnapshot,
  updatedAt: string
): NavAttentionSignal {
  if (agents.length === 0) {
    return createSignal(
      "/agents",
      "action",
      "agent_roster_missing",
      "Agent roster data is missing from the shell snapshot.",
      updatedAt,
      null,
      ["missing"]
    );
  }

  const unavailable = agents.filter((agent) => agent.status !== "ready");
  if (unavailable.length > 0) {
    return createSignal(
      "/agents",
      "action",
      "agent_unavailable",
      unavailable.length === 1
        ? `${unavailable[0]?.name ?? "1 agent"} is unavailable.`
        : `${unavailable.length} agents are unavailable.`,
      updatedAt,
      unavailable.length,
      unavailable.map((agent) => agent.id)
    );
  }

  const lowTrustAgent = workforce.agents.find(
    (agent) => agent.trustGrade === "C" || (agent.trustScore ?? 1) < 0.55
  );
  if (lowTrustAgent) {
    return createSignal(
      "/agents",
      "watch",
      "agent_degraded",
      `${lowTrustAgent.name} is degraded but not blocking the operator.`,
      updatedAt,
      1,
      [lowTrustAgent.id]
    );
  }

  return createNoneSignal("/agents", updatedAt);
}

export function buildNavAttentionSignals({
  workforce,
  services,
  agents,
  judge,
  builder,
  updatedAt,
}: {
  workforce: WorkforceSnapshot;
  services: ServiceSnapshot[];
  agents: AgentInfo[];
  judge: Pick<JudgePlaneSnapshot, "generated_at" | "summary"> | null;
  builder: BuilderFrontDoorSummary;
  updatedAt: string;
}): NavAttentionSignal[] {
  const signals = [
    getOperatorDecisionSignal("/", workforce),
    getOperatorDecisionSignal("/operator", workforce),
    getBuilderSignal(builder, updatedAt),
    getRunsSignal(workforce),
    getInboxSignal(workforce),
    getReviewSignal(judge),
    getServiceSignal(services, updatedAt),
    getBacklogSignal(workforce),
    getAgentsSignal(agents, workforce, updatedAt),
  ];

  return V1_ATTENTION_ROUTES.map(
    (routeHref) => signals.find((signal) => signal.routeHref === routeHref) ?? createNoneSignal(routeHref, updatedAt)
  );
}

export function createNavAttentionMap(signals: NavAttentionSignal[]) {
  return new Map(signals.map((signal) => [signal.routeHref, signal]));
}

export function navAttentionStateEquals(
  left: NavAttentionPersistenceState,
  right: NavAttentionPersistenceState
): boolean {
  const leftKeys = Object.keys(left).sort();
  const rightKeys = Object.keys(right).sort();
  if (leftKeys.length !== rightKeys.length) {
    return false;
  }

  for (let index = 0; index < leftKeys.length; index += 1) {
    if (leftKeys[index] !== rightKeys[index]) {
      return false;
    }
  }

  for (const routeHref of leftKeys) {
    const leftRecord = left[routeHref];
    const rightRecord = right[routeHref];
    if (!leftRecord || !rightRecord) {
      return false;
    }
    if (
      leftRecord.signature !== rightRecord.signature ||
      leftRecord.firstSeenAt !== rightRecord.firstSeenAt ||
      leftRecord.acknowledgedAt !== rightRecord.acknowledgedAt
    ) {
      return false;
    }
  }

  return true;
}

export function resolveNavAttentionPresentation(
  signal: NavAttentionSignal | null | undefined,
  persisted: NavAttentionPersistenceRecord | undefined,
  options: {
    activeSurface: boolean;
    tabVisible: boolean;
    reducedMotion: boolean;
    nowMs?: number;
  }
): NavAttentionPresentation {
  if (!signal || signal.tier === "none") {
    return {
      signal: signal ?? null,
      tier: "none",
      displayTier: "none",
      reason: signal?.reason ?? null,
      source: signal?.source ?? null,
      count: null,
      showCount: false,
      animateSweep: false,
      pulseIndicator: false,
      settled: false,
      acknowledged: false,
      activeSurface: options.activeSurface,
    };
  }

  const nowMs = options.nowMs ?? Date.now();
  const firstSeenAtMs = persisted?.firstSeenAt ? Date.parse(persisted.firstSeenAt) : Number.NaN;
  const acknowledged = persisted?.signature === signal.signature && Boolean(persisted.acknowledgedAt);
  const elapsedMs = Number.isFinite(firstSeenAtMs) ? Math.max(0, nowMs - firstSeenAtMs) : 0;
  const settled = !acknowledged && elapsedMs >= NAV_ATTENTION_HOT_MS;

  let displayTier: NavAttentionTier = signal.tier;
  if (acknowledged) {
    if (signal.tier === "urgent") {
      displayTier = "action";
    } else if (signal.tier === "action") {
      displayTier = "watch";
    }
  }

  const motionSuppressed = options.activeSurface || !options.tabVisible || options.reducedMotion;
  const animateSweep = displayTier === "urgent" && !motionSuppressed;
  const pulseIndicator =
    (displayTier === "urgent" || displayTier === "action") && !motionSuppressed;

  return {
    signal,
    tier: signal.tier,
    displayTier,
    reason: signal.reason,
    source: signal.source,
    count: signal.count,
    showCount: typeof signal.count === "number" && signal.count > 0,
    animateSweep,
    pulseIndicator,
    settled,
    acknowledged,
    activeSurface: options.activeSurface,
  };
}
