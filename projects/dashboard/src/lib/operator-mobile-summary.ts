import { access, readFile } from "node:fs/promises";
import { candidateTruthInventoryPaths, type TruthInventoryCandidatePath, type TruthInventorySourceKind } from "@/lib/truth-inventory-paths";

export type OperatorMobileSummarySourceKind = TruthInventorySourceKind;
type OperatorMobileSummaryCandidatePath = TruthInventoryCandidatePath<OperatorMobileSummarySourceKind>;

export interface OperatorMobileSummary {
  generatedAt: string;
  attentionLevel: string;
  attentionLabel: string;
  needsYou: boolean;
  currentObjective: string;
  currentWork: Record<string, unknown>;
  nextTarget: Record<string, unknown>;
  onlyTypedBrakesRemain: boolean;
  nextOperatorAction: string | null;
  runtimePacketNext: Record<string, unknown> | null;
  controller: {
    host: string;
    mode: string;
    status: string;
    activePassId: string | null;
    typedBrake: string | null;
  };
  runtimeParity: {
    driftClass: string;
    detail: string | null;
  };
  proofGate: {
    open: boolean;
    blockingCheckIds: string[];
    thresholdProgress: number;
    thresholdRequired: number;
    coveredWindowHours: number;
    requiredWindowHours: number;
  };
  systemCapabilities: {
    requiredNowGreen: boolean;
    blockingDomainIds: string[];
  };
  supervisorHealth: {
    healthStatus: string;
    detail: string | null;
  };
  projectFactory: {
    acceptedProjectOutputCount: number;
    broadProjectFactoryReady: boolean;
    distinctProjectCount: number;
    eligibleNowCount: number;
    factoryOperatingMode: string;
    latestDeliverableKind: string;
    latestPendingDeliverableKind: string;
    latestPendingProjectId: string | null;
    latestProjectId: string | null;
    pendingCandidateCount: number;
    pendingHybridAcceptanceCount: number;
    projectOutputStageMet: boolean;
    remainingProjectOutputs: number;
    topPriorityProjectId: string | null;
    topPriorityProjectLabel: string | null;
  };
  availableActions: string[];
  sourceKind: OperatorMobileSummarySourceKind;
  sourcePath: string;
}

export interface OperatorMobileSummaryReadStatus {
  available: boolean;
  degraded: boolean;
  detail: string | null;
  sourceKind: OperatorMobileSummarySourceKind | null;
  sourcePath: string | null;
}

export interface OperatorMobileSummaryReadResult {
  summary: OperatorMobileSummary | null;
  status: OperatorMobileSummaryReadStatus;
}

function candidatePaths(): OperatorMobileSummaryCandidatePath[] {
  return candidateTruthInventoryPaths("operator-mobile-summary.json");
}

function toNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function toStringList(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item: unknown): item is string => typeof item === "string" && item.length > 0)
    : [];
}

function buildOperatorMobileSummary(
  raw: Record<string, any>,
  candidate: OperatorMobileSummaryCandidatePath,
): OperatorMobileSummary {
  return {
    generatedAt: typeof raw.generated_at === "string" ? raw.generated_at : "",
    attentionLevel: typeof raw.attention_level === "string" ? raw.attention_level : "unknown",
    attentionLabel: typeof raw.attention_label === "string" ? raw.attention_label : "unknown",
    needsYou: Boolean(raw.needs_you),
    currentObjective: typeof raw.current_objective === "string" ? raw.current_objective : "unknown",
    currentWork: raw.current_work && typeof raw.current_work === "object" ? raw.current_work : {},
    nextTarget: raw.next_target && typeof raw.next_target === "object" ? raw.next_target : {},
    onlyTypedBrakesRemain: Boolean(raw.only_typed_brakes_remain),
    nextOperatorAction: typeof raw.next_operator_action === "string" ? raw.next_operator_action : null,
    runtimePacketNext:
      raw.runtime_packet_next && typeof raw.runtime_packet_next === "object" ? raw.runtime_packet_next : null,
    controller: {
      host: typeof raw.controller?.host === "string" ? raw.controller.host : "dev",
      mode: typeof raw.controller?.mode === "string" ? raw.controller.mode : "unknown",
      status: typeof raw.controller?.status === "string" ? raw.controller.status : "unknown",
      activePassId: typeof raw.controller?.active_pass_id === "string" ? raw.controller.active_pass_id : null,
      typedBrake: typeof raw.controller?.typed_brake === "string" ? raw.controller.typed_brake : null,
    },
    runtimeParity: {
      driftClass: typeof raw.runtime_parity?.drift_class === "string" ? raw.runtime_parity.drift_class : "unknown",
      detail: typeof raw.runtime_parity?.detail === "string" ? raw.runtime_parity.detail : null,
    },
    proofGate: {
      open: Boolean(raw.proof_gate?.open),
      blockingCheckIds: toStringList(raw.proof_gate?.blocking_check_ids),
      thresholdProgress: toNumber(raw.proof_gate?.threshold_progress),
      thresholdRequired: toNumber(raw.proof_gate?.threshold_required),
      coveredWindowHours: toNumber(raw.proof_gate?.covered_window_hours),
      requiredWindowHours: toNumber(raw.proof_gate?.required_window_hours),
    },
    systemCapabilities: {
      requiredNowGreen: Boolean(raw.system_capabilities?.required_now_green),
      blockingDomainIds: toStringList(raw.system_capabilities?.blocking_domain_ids),
    },
    supervisorHealth: {
      healthStatus:
        typeof raw.supervisor_health?.health_status === "string" ? raw.supervisor_health.health_status : "unknown",
      detail: typeof raw.supervisor_health?.detail === "string" ? raw.supervisor_health.detail : null,
    },
    projectFactory: {
      acceptedProjectOutputCount: toNumber(raw.project_factory?.accepted_project_output_count),
      broadProjectFactoryReady: Boolean(raw.project_factory?.broad_project_factory_ready),
      distinctProjectCount: toNumber(raw.project_factory?.distinct_project_count),
      eligibleNowCount: toNumber(raw.project_factory?.eligible_now_count),
      factoryOperatingMode:
        typeof raw.project_factory?.factory_operating_mode === "string"
          ? raw.project_factory.factory_operating_mode
          : "unknown",
      latestDeliverableKind:
        typeof raw.project_factory?.latest_deliverable_kind === "string"
          ? raw.project_factory.latest_deliverable_kind
          : "unknown",
      latestPendingDeliverableKind:
        typeof raw.project_factory?.latest_pending_deliverable_kind === "string"
          ? raw.project_factory.latest_pending_deliverable_kind
          : "unknown",
      latestPendingProjectId:
        typeof raw.project_factory?.latest_pending_project_id === "string"
          ? raw.project_factory.latest_pending_project_id
          : null,
      latestProjectId:
        typeof raw.project_factory?.latest_project_id === "string" ? raw.project_factory.latest_project_id : null,
      pendingCandidateCount: toNumber(raw.project_factory?.pending_candidate_count),
      pendingHybridAcceptanceCount: toNumber(raw.project_factory?.pending_hybrid_acceptance_count),
      projectOutputStageMet: Boolean(raw.project_factory?.project_output_stage_met),
      remainingProjectOutputs: toNumber(raw.project_factory?.remaining_project_outputs),
      topPriorityProjectId:
        typeof raw.project_factory?.top_priority_project_id === "string"
          ? raw.project_factory.top_priority_project_id
          : null,
      topPriorityProjectLabel:
        typeof raw.project_factory?.top_priority_project_label === "string"
          ? raw.project_factory.top_priority_project_label
          : null,
    },
    availableActions: toStringList(raw.available_actions),
    sourceKind: candidate.kind,
    sourcePath: candidate.path,
  };
}

export async function loadOperatorMobileSummary(): Promise<OperatorMobileSummaryReadResult> {
  for (const candidate of candidatePaths()) {
    try {
      await access(candidate.path);
    } catch {
      continue;
    }

    try {
      const text = await readFile(candidate.path, "utf-8");
      const raw = JSON.parse(text) as Record<string, any>;
      return {
        summary: buildOperatorMobileSummary(raw, candidate),
        status: {
          available: true,
          degraded: false,
          detail: null,
          sourceKind: candidate.kind,
          sourcePath: candidate.path,
        },
      };
    } catch (error) {
      return {
        summary: null,
        status: {
          available: false,
          degraded: true,
          detail: `Invalid operator mobile summary artifact at ${candidate.path}: ${error instanceof Error ? error.message : "unknown parse error"}`,
          sourceKind: candidate.kind,
          sourcePath: candidate.path,
        },
      };
    }
  }

  return {
    summary: null,
    status: {
      available: false,
      degraded: true,
      detail: "Operator mobile summary artifact was not found in the workspace report or repo-root fallback path.",
      sourceKind: null,
      sourcePath: null,
    },
  };
}
