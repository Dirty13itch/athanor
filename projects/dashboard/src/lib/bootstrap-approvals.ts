type BootstrapApprovalContext = {
  kind?: string;
  family?: string;
  slice_id?: string;
  approval_class?: string;
  packet_id?: string;
  packet_label?: string;
  approval_authority?: string;
  open_blocker_ids?: string[];
  follow_on_slice_id?: string;
  summary?: string;
  unlocks?: string;
  operator_instruction?: string;
  review_artifacts?: string[];
  exact_steps?: string[];
  rollback_steps?: string[];
};

type BootstrapProgram = {
  id: string;
  label?: string;
  objective?: string;
  current_family?: string;
  waiting_on_approval_family?: string;
  waiting_on_approval_slice_id?: string;
  updated_at?: string;
  next_action?: Record<string, unknown> | null;
};

export type BootstrapProgramsPayload = {
  programs?: BootstrapProgram[];
  status?: {
    active_program_id?: string;
    approval_context?: BootstrapApprovalContext | null;
  } | null;
};

export type BootstrapSyntheticApproval = {
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

const BOOTSTRAP_APPROVAL_PREFIX = "bootstrap-approval:";

function toUnixSeconds(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.max(0, Math.floor(value));
  }
  if (typeof value === "string" && value.trim().length > 0) {
    const parsed = Date.parse(value);
    if (Number.isFinite(parsed)) {
      return Math.max(0, Math.floor(parsed / 1000));
    }
  }
  return 0;
}

function normalizeString(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function encodeApprovalPart(value: string) {
  return encodeURIComponent(value);
}

function decodeApprovalPart(value: string) {
  return decodeURIComponent(value);
}

function resolveProgram(
  payload: BootstrapProgramsPayload,
  context: BootstrapApprovalContext,
): BootstrapProgram | null {
  const programs = Array.isArray(payload.programs) ? payload.programs : [];
  const activeProgramId = normalizeString(payload.status?.active_program_id);
  const sliceId = normalizeString(context.slice_id);
  const family = normalizeString(context.family);

  if (activeProgramId) {
    const active = programs.find((program) => program.id === activeProgramId);
    if (active) {
      return active;
    }
  }

  const bySlice = programs.find(
    (program) =>
      normalizeString(program.waiting_on_approval_slice_id) === sliceId ||
      normalizeString(program.next_action?.["slice_id"]) === sliceId,
  );
  if (bySlice) {
    return bySlice;
  }

  const byFamily = programs.find(
    (program) =>
      normalizeString(program.waiting_on_approval_family) === family ||
      normalizeString(program.current_family) === family,
  );
  return byFamily ?? null;
}

export function buildBootstrapSyntheticApprovalId(programId: string, sliceId: string, packetId: string) {
  return `${BOOTSTRAP_APPROVAL_PREFIX}${encodeApprovalPart(programId)}:${encodeApprovalPart(sliceId)}:${encodeApprovalPart(packetId)}`;
}

export function parseBootstrapSyntheticApprovalId(approvalId: string) {
  if (!approvalId.startsWith(BOOTSTRAP_APPROVAL_PREFIX)) {
    return null;
  }

  const remainder = approvalId.slice(BOOTSTRAP_APPROVAL_PREFIX.length);
  const [programId, sliceId, packetId] = remainder.split(":");
  if (!programId || !sliceId || !packetId) {
    return null;
  }

  return {
    programId: decodeApprovalPart(programId),
    sliceId: decodeApprovalPart(sliceId),
    packetId: decodeApprovalPart(packetId),
  };
}

export function buildBootstrapSyntheticApprovals(
  payload: BootstrapProgramsPayload | null | undefined,
  status?: string | null,
): BootstrapSyntheticApproval[] {
  if (status && status !== "pending") {
    return [];
  }

  const context = payload?.status?.approval_context;
  if (!context || normalizeString(context.kind || "approval_required") !== "approval_required") {
    return [];
  }

  const sliceId = normalizeString(context.slice_id);
  const packetId = normalizeString(context.packet_id);
  if (!sliceId || !packetId) {
    return [];
  }

  const program = resolveProgram(payload ?? {}, context);
  if (!program) {
    return [];
  }

  const programId = normalizeString(program.id);
  if (!programId) {
    return [];
  }

  return [
    {
      id: buildBootstrapSyntheticApprovalId(programId, sliceId, packetId),
      related_run_id: `bootstrap-program:${programId}`,
      related_task_id: sliceId,
      requested_action: "approve",
      privilege_class: "admin",
      reason:
        normalizeString(context.summary) ||
        normalizeString(context.operator_instruction) ||
        `Bootstrap approval required for ${sliceId}`,
      status: "pending",
      requested_at: toUnixSeconds(program.updated_at),
      task_prompt:
        normalizeString(program.objective) ||
        normalizeString(context.summary) ||
        normalizeString(program.label),
      task_agent_id:
        normalizeString(program.current_family) ||
        normalizeString(context.family) ||
        "bootstrap_supervisor",
      task_priority: "high",
      task_status: "waiting_approval",
      metadata: {
        source: "bootstrap",
        bootstrap_program_id: programId,
        bootstrap_slice_id: sliceId,
        packet_id: packetId,
        packet_label: normalizeString(context.packet_label) || packetId,
        approval_class: normalizeString(context.approval_class),
        follow_on_slice_id: normalizeString(context.follow_on_slice_id),
        review_artifacts: Array.isArray(context.review_artifacts) ? context.review_artifacts : [],
        exact_steps: Array.isArray(context.exact_steps) ? context.exact_steps : [],
        rollback_steps: Array.isArray(context.rollback_steps) ? context.rollback_steps : [],
        open_blocker_ids: Array.isArray(context.open_blocker_ids) ? context.open_blocker_ids : [],
        approval_authority: normalizeString(context.approval_authority) || "operator",
      },
    },
  ];
}
