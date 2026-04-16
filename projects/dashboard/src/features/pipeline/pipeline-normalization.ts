export interface PipelineStatus {
  recent_cycles: number;
  pending_plans: number;
  recent_outcomes_count: number;
  avg_quality: number;
  last_cycle: string | null;
}

export interface PipelineOutcome {
  task_id: string;
  agent: string;
  prompt: string;
  quality_score: number;
  success: boolean;
  ts: string;
}

export interface PipelinePlan {
  id: string;
  title: string;
  intent_source: string;
  approach: string;
  risk_level: string;
  status: string;
}

export interface SynthesisProposal {
  text: string;
  priority: number;
  project: string;
  agent: string;
  twelve_word: string;
  explore: boolean;
  reasoning: string;
}

type UnknownRecord = Record<string, unknown>;

function asRecord(value: unknown): UnknownRecord | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as UnknownRecord)
    : null;
}

function readString(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}

function readNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function readBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

function readArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export function normalizePipelineStatus(value: unknown): PipelineStatus {
  const record = asRecord(value);
  const recentCycles = record?.recent_cycles;
  const pendingPlans = record?.pending_plans;
  const lastCycleRecord = asRecord(record?.last_cycle);

  return {
    recent_cycles: readNumber(recentCycles) ?? readArray(recentCycles).length,
    pending_plans: readNumber(pendingPlans) ?? readArray(pendingPlans).length,
    recent_outcomes_count: readNumber(record?.recent_outcomes_count) ?? 0,
    avg_quality: readNumber(record?.avg_quality) ?? 0,
    last_cycle:
      readString(record?.last_cycle) ??
      readString(lastCycleRecord?.completed_at) ??
      readString(lastCycleRecord?.started_at) ??
      readString(lastCycleRecord?.created_at) ??
      null,
  };
}

export function normalizePipelineOutcomes(value: unknown): PipelineOutcome[] {
  const root = asRecord(value);
  const outcomes = readArray(root?.outcomes ?? value);

  return outcomes.map((entry, index) => {
    const record = asRecord(entry);
    const status = readString(record?.status) ?? "completed";

    return {
      task_id:
        readString(record?.task_id) ??
        readString(record?.id) ??
        readString(record?.plan_id) ??
        `pipeline-outcome-${index}`,
      agent: readString(record?.agent) ?? "pipeline",
      prompt:
        readString(record?.prompt) ??
        readString(record?.title) ??
        readString(record?.plan_id) ??
        "Pipeline outcome",
      quality_score:
        readNumber(record?.quality_score) ??
        readNumber(record?.quality) ??
        0,
      success:
        readBoolean(record?.success) ??
        !["failed", "rejected", "review_required"].includes(status),
      ts:
        readString(record?.ts) ??
        readString(record?.recorded_at) ??
        readString(record?.completed_at) ??
        new Date(0).toISOString(),
    };
  });
}

export function normalizePipelinePlans(value: unknown): PipelinePlan[] {
  const root = asRecord(value);
  const plans = readArray(root?.plans ?? value);

  return plans.map((entry, index) => {
    const record = asRecord(entry);
    const requiresApproval = readBoolean(record?.requires_approval) ?? false;

    return {
      id: readString(record?.id) ?? `pipeline-plan-${index}`,
      title: readString(record?.title) ?? "Untitled plan",
      intent_source:
        readString(record?.intent_source) ??
        readString(record?.source) ??
        readString(record?.status) ??
        "pipeline",
      approach:
        readString(record?.approach) ??
        readString(record?.summary) ??
        readString(record?.description) ??
        readString(record?.title) ??
        "No execution approach is available yet.",
      risk_level:
        readString(record?.risk_level) ??
        (requiresApproval ? "high" : "medium"),
      status: readString(record?.status) ?? "pending",
    };
  });
}

export function normalizePipelineProposals(value: unknown): SynthesisProposal[] {
  const root = asRecord(value);
  const proposals = readArray(root?.proposals ?? value);

  return proposals.map((entry) => {
    const record = asRecord(entry);

    return {
      text:
        readString(record?.text) ??
        readString(record?.title) ??
        "Untitled proposal",
      priority:
        readNumber(record?.priority) ??
        readNumber(record?.confidence) ??
        0,
      project:
        readString(record?.project) ??
        readString(record?.domain) ??
        "general",
      agent: readString(record?.agent) ?? "pipeline",
      twelve_word: readString(record?.twelve_word) ?? "",
      explore: readBoolean(record?.explore) ?? false,
      reasoning: readString(record?.reasoning) ?? "",
    };
  });
}
