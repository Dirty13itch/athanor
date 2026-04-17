import { randomUUID } from "node:crypto";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import {
  builderExecutionSessionSchema,
  builderProgressEventSchema,
  builderSessionEventsResponseSchema,
  builderTaskEnvelopeSchema,
  type BuilderControlAction,
  type BuilderExecutionSession,
  type BuilderFrontDoorSummary,
  type BuilderProgressEvent,
  type BuilderRouteDecision,
  type BuilderSessionEventsResponse,
  type BuilderSessionPreview,
  type BuilderTaskEnvelope,
} from "@/lib/contracts";

interface BuilderStoreFile {
  version: 1;
  updated_at: string;
  sessions: Record<string, BuilderExecutionSession>;
  events: Record<string, BuilderProgressEvent[]>;
}

type BuilderControlResult = {
  session: BuilderExecutionSession;
  terminal_href: string | null;
};

export type BuilderSessionMutation = (
  session: BuilderExecutionSession,
  events: BuilderProgressEvent[],
  timestamp: string,
) => void;

type BuilderSyntheticRun = {
  id: string;
  task_id: string;
  backlog_id: string;
  agent_id: string;
  workload_class: string;
  provider_lane: string;
  runtime_lane: string;
  policy_class: string;
  status: string;
  summary: string;
  created_at: number;
  updated_at: number;
  completed_at: number;
  step_count: number;
  approval_pending: boolean;
  latest_attempt: {
    id: string;
    runtime_host: string;
    status: string;
    heartbeat_at: number;
  };
  approvals: Array<{ id: string; status: string; privilege_class: string }>;
  metadata: Record<string, unknown>;
};

type BuilderSyntheticApproval = {
  id: string;
  related_run_id: string;
  related_task_id: string;
  requested_action: string;
  privilege_class: string;
  reason: string;
  status: string;
  requested_at: number;
  task_prompt: string;
  task_agent_id: string;
  task_priority: string;
  task_status: string;
  metadata: Record<string, unknown>;
};

const STORE_FILENAME = "builder-sessions.json";
const DEFAULT_STORE_PATH = path.join(process.cwd(), ".data", STORE_FILENAME);

let writeQueue: Promise<void> = Promise.resolve();

function nowIso(): string {
  return new Date().toISOString();
}

function toUnixSeconds(value: string | null | undefined): number {
  if (!value) {
    return 0;
  }
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? Math.floor(parsed / 1000) : 0;
}

function resolveStorePath(): string {
  return process.env.DASHBOARD_BUILDER_STORE_PATH?.trim() || DEFAULT_STORE_PATH;
}

function defaultStore(): BuilderStoreFile {
  return {
    version: 1,
    updated_at: nowIso(),
    sessions: {},
    events: {},
  };
}

function sortByUpdatedAtDesc<T extends { updated_at: string }>(items: T[]): T[] {
  return [...items].sort((left, right) => right.updated_at.localeCompare(left.updated_at));
}

function parseSessions(value: unknown): Record<string, BuilderExecutionSession> {
  if (!value || typeof value !== "object") {
    return {};
  }

  const sessions: Record<string, BuilderExecutionSession> = {};
  for (const [id, session] of Object.entries(value as Record<string, unknown>)) {
    const parsed = builderExecutionSessionSchema.safeParse(session);
    if (parsed.success) {
      sessions[id] = parsed.data;
    }
  }
  return sessions;
}

function parseEvents(value: unknown): Record<string, BuilderProgressEvent[]> {
  if (!value || typeof value !== "object") {
    return {};
  }

  const events: Record<string, BuilderProgressEvent[]> = {};
  for (const [id, sessionEvents] of Object.entries(value as Record<string, unknown>)) {
    if (!Array.isArray(sessionEvents)) {
      continue;
    }
    events[id] = sessionEvents
      .map((event) => builderProgressEventSchema.safeParse(event))
      .flatMap((parsed) => (parsed.success ? [parsed.data] : []));
  }
  return events;
}

async function readStoreFile(): Promise<BuilderStoreFile> {
  const storePath = resolveStorePath();
  try {
    const raw = await readFile(storePath, "utf8");
    const parsed = JSON.parse(raw) as Partial<BuilderStoreFile>;
    return {
      version: 1,
      updated_at: typeof parsed.updated_at === "string" ? parsed.updated_at : nowIso(),
      sessions: parseSessions(parsed.sessions),
      events: parseEvents(parsed.events),
    };
  } catch {
    return defaultStore();
  }
}

async function writeStoreFile(store: BuilderStoreFile): Promise<void> {
  const storePath = resolveStorePath();
  await mkdir(path.dirname(storePath), { recursive: true });
  const tempPath = `${storePath}.${randomUUID()}.tmp`;
  await writeFile(tempPath, `${JSON.stringify(store, null, 2)}\n`, "utf8");
  await rename(tempPath, storePath);
}

function summarizeGoal(goal: string): string {
  const normalized = goal.trim().replace(/\s+/g, " ");
  if (normalized.length <= 84) {
    return normalized;
  }
  return `${normalized.slice(0, 81).trimEnd()}...`;
}

function buildVerificationContract(taskEnvelope: BuilderTaskEnvelope) {
  switch (taskEnvelope.task_class) {
    case "multi_file_implementation":
      return {
        required_checks: ["targeted_tests_or_build", "diff_review", "acceptance_criteria_match"],
        blocking_failures: ["tests_failed", "acceptance_criteria_unmet"],
        non_blocking_failures: ["warnings_present", "manual_review_recommended"],
        fallback_behavior: "Escalate to claude_code if semantic ambiguity or verification failure appears.",
      };
    case "deterministic_refactor":
      return {
        required_checks: ["scope_coverage_check", "targeted_typecheck_or_tests", "diff_entropy_review"],
        blocking_failures: ["coverage_gap", "typecheck_failed"],
        non_blocking_failures: ["follow_up_cleanup_needed"],
        fallback_behavior: "Escalate to codex and then claude_code when the mechanical edit needs semantic repair.",
      };
    case "architecture_review":
    case "repo_wide_audit":
      return {
        required_checks: ["cross_file_citations", "ranked_findings", "evidence_links"],
        blocking_failures: ["missing_evidence"],
        non_blocking_failures: ["operator_review_recommended"],
        fallback_behavior: "Fallback to codex and then claude_code if Gemini is unavailable.",
      };
    case "sovereign_private_coding":
    case "creative_batch":
      return {
        required_checks: ["local_route_confirmation", "artifact_or_output_trace", "policy_compliance_check"],
        blocking_failures: ["cloud_egress_detected", "local_route_unavailable"],
        non_blocking_failures: ["capacity_wait_required"],
        fallback_behavior: "Remain local-only and fail closed while capacity or local lane health is degraded.",
      };
  }
}

function buildRouteDecision(taskEnvelope: BuilderTaskEnvelope): BuilderRouteDecision {
  if (
    taskEnvelope.task_class === "multi_file_implementation" &&
    taskEnvelope.sensitivity_class === "private_but_cloud_allowed" &&
    taskEnvelope.workspace_mode === "repo_worktree" &&
    !taskEnvelope.needs_github
  ) {
    return {
      route_id: "builder:codex:direct_cli",
      route_label: "Codex direct implementation",
      primary_adapter: "codex",
      execution_mode: "direct_cli",
      fallback_chain: ["claude_code"],
      workspace_plan:
        taskEnvelope.workspace_mode === "repo_worktree"
          ? "Use an isolated repo worktree for the first builder mutation slice."
          : "Use the current repo workspace until mutation isolation is required.",
      verification_profile: "targeted_tests_and_diff_review",
      policy_basis: [
        "lane-selection-matrix:multi_file_implementation:private_but_cloud_allowed",
        "builder-front-door:first-slice",
      ],
      activation_state: "live_ready",
    };
  }

  if (taskEnvelope.task_class === "deterministic_refactor") {
    return {
      route_id: "builder:aider:litellm_routed",
      route_label: "Aider deterministic refactor",
      primary_adapter: "aider",
      execution_mode: "litellm_routed",
      fallback_chain: ["codex", "claude_code"],
      workspace_plan: "Use a dedicated repo worktree because the edit spans many files.",
      verification_profile: "scope_coverage_and_typecheck",
      policy_basis: [
        "lane-selection-matrix:deterministic_refactor:private_but_cloud_allowed",
        "builder-front-door:deferred-core-route",
      ],
      activation_state: "planned_future",
    };
  }

  if (taskEnvelope.task_class === "architecture_review" || taskEnvelope.task_class === "repo_wide_audit") {
    return {
      route_id: "builder:gemini_cli:audit",
      route_label: "Gemini wide-context audit",
      primary_adapter: "gemini_cli",
      execution_mode: taskEnvelope.task_class === "repo_wide_audit" ? "goose_wrapped" : "direct_cli",
      fallback_chain: ["codex", "claude_code"],
      workspace_plan: "Use a read-only docs or repo context unless the operator explicitly escalates to mutation.",
      verification_profile: "evidence_and_findings",
      policy_basis: [
        `lane-selection-matrix:${taskEnvelope.task_class}:cloud_safe`,
        "builder-front-door:deferred-core-route",
      ],
      activation_state: "planned_future",
    };
  }

  if (taskEnvelope.needs_github && taskEnvelope.needs_background) {
    return {
      route_id: "builder:copilot:github_async",
      route_label: "Copilot GitHub async delegate",
      primary_adapter: "copilot",
      execution_mode: "direct_cli",
      fallback_chain: ["codex", "claude_code"],
      workspace_plan: "Own work on a branch or delegated workspace with GitHub-native async handoff.",
      verification_profile: "pull_request_ready_validation",
      policy_basis: [
        "builder-front-door:github_async_delegate",
        "builder-front-door:deferred-core-route",
      ],
      activation_state: "planned_future",
    };
  }

  if (taskEnvelope.task_class === "sovereign_private_coding" || taskEnvelope.task_class === "creative_batch") {
    return {
      route_id: "builder:sovereign:local_only",
      route_label: "Sovereign local-only lane",
      primary_adapter:
        taskEnvelope.task_class === "creative_batch" ? "sovereign_bulk" : "sovereign_coder",
      execution_mode: "sovereign_local",
      fallback_chain: ["sovereign_supervisor"],
      workspace_plan: "Fail closed to local-only execution and keep artifacts on the sovereign lane.",
      verification_profile: "local_route_and_artifact_trace",
      policy_basis: [
        `lane-selection-matrix:${taskEnvelope.task_class}:sovereign_only`,
        "builder-front-door:local-only-policy",
      ],
      activation_state: "local_only",
    };
  }

  return {
    route_id: "builder:claude_code:rescue",
    route_label: "Claude Code escalator",
    primary_adapter: "claude_code",
    execution_mode: "direct_cli",
    fallback_chain: ["codex"],
    workspace_plan: "Escalate through the rescue lane once a primary builder route is linked.",
    verification_profile: "semantic_review",
    policy_basis: ["builder-front-door:rescue-lane", "builder-front-door:deferred-core-route"],
    activation_state: "planned_future",
  };
}

function buildPendingApproval(reason: string) {
  return {
    id: `builder-approval-${randomUUID()}`,
    requested_action: "start_builder_execution",
    privilege_class: "operator" as const,
    reason,
    status: "pending" as const,
    created_at: nowIso(),
    resolved_at: null,
  };
}

export function createBuilderEvent(
  event_type: string,
  label: string,
  detail: string,
  tone: BuilderProgressEvent["tone"],
): BuilderProgressEvent {
  return {
    id: `builder-event-${randomUUID()}`,
    event_type,
    label,
    detail,
    tone,
    timestamp: nowIso(),
  };
}

function toPreview(session: BuilderExecutionSession): BuilderSessionPreview {
  const pending_approval_count = session.approvals.filter((approval) => approval.status === "pending").length;
  return {
    id: session.id,
    title: session.title,
    status: session.status,
    primary_adapter: session.route_decision.primary_adapter,
    current_route: session.current_route ?? session.route_decision.route_label,
    verification_status: session.verification_state.status,
    pending_approval_count,
    artifact_count: session.latest_result_packet?.artifacts.length ?? 0,
    resumable_handle: session.latest_result_packet?.resumable_handle ?? null,
    shadow_mode: session.shadow_mode,
    fallback_state: session.fallback_state,
    updated_at: session.updated_at,
  };
}

function pickCurrentSession(previews: BuilderSessionPreview[]): BuilderSessionPreview | null {
  const current =
    previews.find((session) => !["completed", "cancelled", "failed"].includes(session.status)) ??
    previews[0] ??
    null;
  return current;
}

function toSummary(store: BuilderStoreFile): BuilderFrontDoorSummary {
  const sessions = sortByUpdatedAtDesc(Object.values(store.sessions)).map(toPreview);
  const current_session = pickCurrentSession(sessions);
  return {
    available: true,
    degraded: false,
    detail: null,
    updated_at: store.updated_at,
    session_count: sessions.length,
    active_count: sessions.filter((session) =>
      ["waiting_approval", "queued", "running"].includes(session.status),
    ).length,
    pending_approval_count: sessions.reduce((sum, session) => sum + session.pending_approval_count, 0),
    recent_artifact_count: current_session?.artifact_count ?? 0,
    current_session,
    sessions: sessions.slice(0, 8),
  };
}

async function mutateStore<T>(
  updater: (store: BuilderStoreFile) => T | Promise<T>,
): Promise<T> {
  const next = writeQueue.then(async () => {
    const current = await readStoreFile();
    const result = await updater(current);
    current.updated_at = nowIso();
    await writeStoreFile(current);
    return result;
  });

  writeQueue = next.then(() => undefined, () => undefined);
  return next;
}

export async function readBuilderSummary(): Promise<BuilderFrontDoorSummary> {
  return toSummary(await readStoreFile());
}

export async function readBuilderSession(sessionId: string): Promise<BuilderExecutionSession | null> {
  const store = await readStoreFile();
  return store.sessions[sessionId] ?? null;
}

export async function readBuilderSessionEvents(sessionId: string): Promise<BuilderSessionEventsResponse | null> {
  const store = await readStoreFile();
  if (!store.sessions[sessionId]) {
    return null;
  }
  const events = store.events[sessionId] ?? [];
  return builderSessionEventsResponseSchema.parse({
    session_id: sessionId,
    count: events.length,
    events,
  });
}

export async function mutateBuilderSession(
  sessionId: string,
  mutate: BuilderSessionMutation,
): Promise<BuilderExecutionSession> {
  return mutateStore((store) => {
    const session = store.sessions[sessionId];
    if (!session) {
      throw new Error(`Unknown builder session: ${sessionId}`);
    }

    const events = [...(store.events[sessionId] ?? [])];
    const timestamp = nowIso();
    mutate(session, events, timestamp);
    session.updated_at = timestamp;
    store.sessions[sessionId] = builderExecutionSessionSchema.parse(session);
    store.events[sessionId] = events.map((event) => builderProgressEventSchema.parse(event));
    return store.sessions[sessionId];
  });
}

export async function createBuilderSession(taskEnvelope: BuilderTaskEnvelope): Promise<BuilderExecutionSession> {
  const parsed = builderTaskEnvelopeSchema.parse(taskEnvelope);
  return mutateStore((store) => {
    const id = `builder-${randomUUID()}`;
    const created_at = nowIso();
    const route_decision = buildRouteDecision(parsed);
    const verification_contract = buildVerificationContract(parsed);
    const requires_approval =
      route_decision.activation_state === "live_ready" || route_decision.activation_state === "shadow_ready";
    const approvals = requires_approval
      ? [
          buildPendingApproval(
            route_decision.activation_state === "live_ready"
              ? "Live builder execution needs explicit operator approval before worktree mutation begins."
              : "Shadow-mode builder execution still needs explicit operator start until the worker bridge is linked.",
          ),
        ]
      : [];

    const status =
      route_decision.activation_state === "live_ready" || route_decision.activation_state === "shadow_ready"
        ? "waiting_approval"
        : "blocked";

    const latest_result_packet = {
      outcome:
        route_decision.activation_state === "live_ready" || route_decision.activation_state === "shadow_ready"
          ? "planned"
          : "blocked",
      summary:
        route_decision.activation_state === "live_ready"
          ? "Route selected and ready for live Codex execution. Approve the session to queue the builder run."
          : route_decision.activation_state === "shadow_ready"
            ? "Route selected and staged for the shadow Codex path. Approve the session to queue the builder run."
          : "Route selected, but this adapter is not wired into the builder front door yet.",
      artifacts: [],
      files_changed: [],
      validation: verification_contract.required_checks.map((check) => ({
        id: check,
        label: check.replaceAll("_", " "),
        status: "pending" as const,
        detail: "Verification is staged and waiting on execution evidence.",
      })),
      remaining_risks:
        route_decision.activation_state === "live_ready"
          ? ["Operator approval still pending", "Verification has not run yet"]
          : route_decision.activation_state === "shadow_ready"
            ? ["Worker bridge still pending", "Terminal fallback remains the current escape hatch"]
          : ["Selected adapter is not linked into the builder front door yet"],
      resumable_handle: null,
      recovery_gate:
        route_decision.activation_state === "live_ready" || route_decision.activation_state === "shadow_ready"
          ? "operator_approval_required"
          : "adapter_not_yet_linked",
    };

    const session = builderExecutionSessionSchema.parse({
      id,
      title: summarizeGoal(parsed.goal),
      status,
      created_at,
      updated_at: created_at,
      task_envelope: parsed,
      route_decision,
      verification_contract,
      verification_state: {
        status: "planned",
        summary:
          route_decision.activation_state === "live_ready"
            ? "Verification contract is staged for the live Codex builder route."
            : route_decision.activation_state === "shadow_ready"
              ? "Verification contract is staged for the first Codex route."
            : "Verification contract is staged, but the adapter is not active in the builder front door yet.",
        completed_checks: [],
        failed_checks: [],
        last_updated_at: created_at,
      },
      latest_result_packet,
      approvals,
      current_worker: route_decision.primary_adapter,
      current_route: route_decision.route_label,
      shadow_mode: route_decision.activation_state === "shadow_ready",
      fallback_state:
        route_decision.activation_state === "live_ready"
          ? "approval_pending"
          : route_decision.activation_state === "shadow_ready"
            ? "worker_bridge_pending"
            : "adapter_not_yet_linked",
      linked_surfaces: {
        runs_href: `/runs?builderSession=${id}`,
        review_href: `/review?builderSession=${id}`,
        terminal_href: `/terminal?builderSession=${id}`,
      },
    });

    store.sessions[id] = session;
    store.events[id] = [
      createBuilderEvent("session_created", "Session created", "Builder intake recorded a new task envelope.", "info"),
      createBuilderEvent(
        "route_selected",
        "Route selected",
        `${route_decision.route_label} selected with ${route_decision.primary_adapter} on ${route_decision.execution_mode}.`,
        "success",
      ),
      createBuilderEvent(
        "verification_planned",
        "Verification staged",
        `Required checks: ${verification_contract.required_checks.join(", ")}.`,
        "info",
      ),
      ...(requires_approval
        ? [
            createBuilderEvent(
              "approval_requested",
              "Approval requested",
              route_decision.activation_state === "live_ready"
                ? "Operator approval is required before the live builder route can begin worktree mutation."
                : "Operator approval is required before the shadow builder route can queue execution.",
              "warning",
            ),
          ]
        : [
            createBuilderEvent(
              "route_deferred",
              "Route not yet linked",
              "This adapter remains defined but not yet wired into the builder front door.",
              "warning",
            ),
          ]),
    ];

    return session;
  });
}

export async function applyBuilderSessionControl(
  sessionId: string,
  action: BuilderControlAction,
  approvalId?: string | null,
): Promise<BuilderControlResult> {
  return mutateStore((store) => {
    const session = store.sessions[sessionId];
    if (!session) {
      throw new Error(`Unknown builder session: ${sessionId}`);
    }

    const timestamp = nowIso();
    const events = store.events[sessionId] ?? [];
    let terminal_href: string | null = null;

    if (action === "approve" || action === "reject") {
      const targetApproval =
        session.approvals.find((approval) => approval.id === approvalId) ??
        session.approvals.find((approval) => approval.status === "pending");
      if (!targetApproval) {
        throw new Error("No pending builder approval was found for this session.");
      }
      targetApproval.status = action === "approve" ? "approved" : "rejected";
      targetApproval.resolved_at = timestamp;
    }

    switch (action) {
      case "approve":
        session.status = "queued";
        session.fallback_state =
          session.route_decision.activation_state === "live_ready" ? "execution_queued" : "worker_bridge_pending";
        session.verification_state.status = "planned";
        session.verification_state.summary =
          session.route_decision.activation_state === "live_ready"
            ? "Approval recorded. The session is queued for live Codex execution."
            : "Approval recorded. The session is queued for the shadow Codex route while the worker bridge remains pending.";
        session.verification_state.last_updated_at = timestamp;
        if (session.latest_result_packet) {
          session.latest_result_packet.summary =
            session.route_decision.activation_state === "live_ready"
              ? "Approval recorded. The session is queued for live Codex execution."
              : "Approval recorded. The session is queued for the shadow Codex route while the worker bridge remains pending.";
          session.latest_result_packet.recovery_gate =
            session.route_decision.activation_state === "live_ready" ? "execution_starting" : "worker_bridge_pending";
        }
        events.push(
          createBuilderEvent(
            "approval_resolved",
            "Approval granted",
            session.route_decision.activation_state === "live_ready"
              ? "Operator approved the builder session. It is now queued for the live Codex worker path."
              : "Operator approved the builder session. It is now queued for the shadow worker path.",
            "success",
          ),
        );
        break;
      case "reject":
        session.status = "cancelled";
        session.fallback_state = "operator_rejected";
        session.verification_state.status = "blocked";
        session.verification_state.summary =
          "Operator rejected the session before execution could begin.";
        session.verification_state.last_updated_at = timestamp;
        if (session.latest_result_packet) {
          session.latest_result_packet.outcome = "cancelled";
          session.latest_result_packet.summary =
            "Operator rejected the session before execution could begin.";
          session.latest_result_packet.recovery_gate = "resume_requires_new_approval";
        }
        events.push(
          createBuilderEvent(
            "approval_resolved",
            "Approval rejected",
            "Operator rejected the builder session before execution could begin.",
            "danger",
          ),
        );
        break;
      case "resume": {
        const hasPendingApproval = session.approvals.some((approval) => approval.status === "pending");
        if (
          !hasPendingApproval &&
          (session.route_decision.activation_state === "live_ready" ||
            session.route_decision.activation_state === "shadow_ready")
        ) {
          session.approvals.push(
            buildPendingApproval(
              session.route_decision.activation_state === "live_ready"
                ? "Resuming this builder session requires a fresh operator approval before Codex execution can continue."
                : "Resuming this shadow builder session requires a fresh operator approval before execution can begin.",
            ),
          );
        }
        session.status =
          session.route_decision.activation_state === "live_ready" ||
          session.route_decision.activation_state === "shadow_ready"
            ? "waiting_approval"
            : "blocked";
        session.fallback_state =
          session.route_decision.activation_state === "live_ready"
            ? "approval_pending"
            : session.route_decision.activation_state === "shadow_ready"
              ? "worker_bridge_pending"
              : "adapter_not_yet_linked";
        session.verification_state.status = "planned";
        session.verification_state.summary =
          session.route_decision.activation_state === "live_ready"
            ? "Session resumed and is waiting for a fresh operator approval before Codex execution continues."
            : session.route_decision.activation_state === "shadow_ready"
              ? "Session resumed and is waiting for a fresh operator approval."
            : "Session resumed, but the selected adapter is still not linked into the builder front door.";
        session.verification_state.last_updated_at = timestamp;
        if (session.latest_result_packet) {
          session.latest_result_packet.outcome =
            session.route_decision.activation_state === "live_ready" ||
            session.route_decision.activation_state === "shadow_ready"
              ? "planned"
              : "blocked";
          session.latest_result_packet.summary = session.verification_state.summary;
          session.latest_result_packet.recovery_gate =
            session.route_decision.activation_state === "live_ready" ||
            session.route_decision.activation_state === "shadow_ready"
              ? "operator_approval_required"
              : "adapter_not_yet_linked";
        }
        events.push(
          createBuilderEvent(
            "session_resumed",
            "Session resumed",
            session.verification_state.summary,
            session.route_decision.activation_state === "live_ready" ||
            session.route_decision.activation_state === "shadow_ready"
              ? "warning"
              : "info",
          ),
        );
        break;
      }
      case "cancel":
        session.status = "cancelled";
        session.fallback_state = "operator_cancelled";
        session.approvals = session.approvals.map((approval) =>
          approval.status === "pending"
            ? {
                ...approval,
                status: "rejected",
                resolved_at: timestamp,
              }
            : approval,
        );
        session.verification_state.status = "blocked";
        session.verification_state.summary = "Session cancelled by the operator.";
        session.verification_state.last_updated_at = timestamp;
        if (session.latest_result_packet) {
          session.latest_result_packet.outcome = "cancelled";
          session.latest_result_packet.summary = "Session cancelled by the operator.";
          session.latest_result_packet.recovery_gate = "resume_required";
        }
        events.push(
          createBuilderEvent("session_cancelled", "Session cancelled", "Operator cancelled the builder session.", "danger"),
        );
        break;
      case "open_terminal":
        terminal_href = session.linked_surfaces.terminal_href;
        events.push(
          createBuilderEvent(
            "terminal_opened",
            "Terminal escape hatch opened",
            "Builder session handed off to the terminal fallback path.",
            "info",
          ),
        );
        break;
    }

    session.updated_at = timestamp;
    store.sessions[sessionId] = builderExecutionSessionSchema.parse(session);
    store.events[sessionId] = events.map((event) => builderProgressEventSchema.parse(event));

    return {
      session: store.sessions[sessionId],
      terminal_href,
    };
  });
}

export async function listBuilderSyntheticRuns(status?: string | null, limit = 50): Promise<BuilderSyntheticRun[]> {
  const store = await readStoreFile();
  return sortByUpdatedAtDesc(Object.values(store.sessions))
    .filter((session) => !status || session.status === status)
    .map((session) => ({
      id: `builder-run-${session.id}`,
      task_id: session.id,
      backlog_id: "",
      agent_id: session.route_decision.primary_adapter,
      workload_class: session.task_envelope.task_class,
      provider_lane: session.route_decision.primary_adapter,
      runtime_lane: session.route_decision.execution_mode,
      policy_class: session.task_envelope.sensitivity_class,
      status: session.status,
      summary: session.latest_result_packet?.summary ?? session.title,
      created_at: toUnixSeconds(session.created_at),
      updated_at: toUnixSeconds(session.updated_at),
      completed_at: toUnixSeconds(session.status === "completed" ? session.updated_at : null),
      step_count: (store.events[session.id] ?? []).length,
      approval_pending: session.approvals.some((approval) => approval.status === "pending"),
      latest_attempt: {
        id: `builder-attempt-${session.id}`,
        runtime_host: "builder-front-door",
        status: session.status,
        heartbeat_at: toUnixSeconds(session.updated_at),
      },
      approvals: session.approvals.map((approval) => ({
        id: approval.id,
        status: approval.status,
        privilege_class: approval.privilege_class,
      })),
      metadata: {
        builder_session_id: session.id,
        shadow_mode: session.shadow_mode,
        linked_surfaces: session.linked_surfaces,
      },
    }))
    .slice(0, limit);
}

export async function listBuilderSyntheticApprovals(status?: string | null): Promise<BuilderSyntheticApproval[]> {
  const store = await readStoreFile();
  return sortByUpdatedAtDesc(Object.values(store.sessions)).flatMap((session) =>
    session.approvals
      .filter((approval) => !status || approval.status === status)
      .map((approval) => ({
        id: approval.id,
        related_run_id: `builder-run-${session.id}`,
        related_task_id: session.id,
        requested_action: approval.requested_action,
        privilege_class: approval.privilege_class,
        reason: approval.reason,
        status: approval.status,
        requested_at: toUnixSeconds(approval.created_at),
        task_prompt: session.task_envelope.goal,
        task_agent_id: session.route_decision.primary_adapter,
        task_priority: "normal",
        task_status: session.status,
        metadata: {
          builder_session_id: session.id,
          shadow_mode: session.shadow_mode,
        },
      })),
  );
}

export async function __resetBuilderStoreForTests(): Promise<void> {
  writeQueue = Promise.resolve();
}
