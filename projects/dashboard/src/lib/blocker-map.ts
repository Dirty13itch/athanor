import { access, readFile } from "node:fs/promises";
import { candidateTruthInventoryPaths, type TruthInventoryCandidatePath, type TruthInventorySourceKind } from "@/lib/truth-inventory-paths";

export type BlockerMapSourceKind = TruthInventorySourceKind;
type BlockerMapCandidatePath = TruthInventoryCandidatePath<BlockerMapSourceKind>;

export interface BlockerMap {
  generatedAt: string;
  objective: string;
  activeWorkstream: {
    id: string | null;
    title: string | null;
    claimTaskId: string | null;
    claimTaskTitle: string | null;
    claimLaneFamily: string | null;
    dispatchStatus: string | null;
  };
  remaining: {
    cashNow: number;
    boundedFollowOn: number;
    programSlice: number;
    familyCount: number;
    pathCount: number;
    familyIds: string[];
  };
  nextTranche: {
    id: string | null;
    title: string | null;
    executionClass: string | null;
    matchCount: number;
    nextAction: string | null;
    decompositionRequired: boolean;
    decompositionReasons: string[];
    categories: string[];
  };
  queue: {
    total: number;
    dispatchable: number;
    blocked: number;
    suppressed: number;
  };
  stableOperatingDay: {
    met: boolean;
    coveredWindowHours: number;
    requiredWindowHours: number;
    includedPassCount: number;
    consecutiveHealthyPassCount: number;
    detail: string | null;
  };
  resultEvidence: {
    thresholdRequired: number;
    thresholdProgress: number;
    thresholdMet: boolean;
    resultBackedCompletionCount: number;
    reviewBackedOutputCount: number;
  };
  proofGate: {
    open: boolean;
    status: string;
    blockingCheckIds: string[];
  };
  autoMutation: {
    state: string;
    proofGateOpen: boolean;
    detail: string | null;
  };
  sourceKind: BlockerMapSourceKind;
  sourcePath: string;
}

export interface BlockerMapReadStatus {
  available: boolean;
  degraded: boolean;
  detail: string | null;
  sourceKind: BlockerMapSourceKind | null;
  sourcePath: string | null;
}

export interface BlockerMapReadResult {
  blockerMap: BlockerMap | null;
  status: BlockerMapReadStatus;
}

function candidatePaths(): BlockerMapCandidatePath[] {
  return candidateTruthInventoryPaths("blocker-map.json");
}

function toNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function toStringList(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item: unknown): item is string => typeof item === "string" && item.length > 0)
    : [];
}

function buildBlockerMap(raw: Record<string, any>, candidate: BlockerMapCandidatePath): BlockerMap {
  return {
    generatedAt: typeof raw.generated_at === "string" ? raw.generated_at : "",
    objective: typeof raw.objective === "string" ? raw.objective : "unknown",
    activeWorkstream: {
      id: typeof raw.active_workstream?.id === "string" ? raw.active_workstream.id : null,
      title: typeof raw.active_workstream?.title === "string" ? raw.active_workstream.title : null,
      claimTaskId:
        typeof raw.active_workstream?.claim_task_id === "string" ? raw.active_workstream.claim_task_id : null,
      claimTaskTitle:
        typeof raw.active_workstream?.claim_task_title === "string"
          ? raw.active_workstream.claim_task_title
          : null,
      claimLaneFamily:
        typeof raw.active_workstream?.claim_lane_family === "string"
          ? raw.active_workstream.claim_lane_family
          : null,
      dispatchStatus:
        typeof raw.active_workstream?.dispatch_status === "string" ? raw.active_workstream.dispatch_status : null,
    },
    remaining: {
      cashNow: toNumber(raw.remaining?.cash_now),
      boundedFollowOn: toNumber(raw.remaining?.bounded_follow_on),
      programSlice: toNumber(raw.remaining?.program_slice),
      familyCount: toNumber(raw.remaining?.family_count),
      pathCount: toNumber(raw.remaining?.path_count),
      familyIds: toStringList(raw.remaining?.family_ids),
    },
    nextTranche: {
      id: typeof raw.next_tranche?.id === "string" ? raw.next_tranche.id : null,
      title: typeof raw.next_tranche?.title === "string" ? raw.next_tranche.title : null,
      executionClass:
        typeof raw.next_tranche?.execution_class === "string" ? raw.next_tranche.execution_class : null,
      matchCount: toNumber(raw.next_tranche?.match_count),
      nextAction: typeof raw.next_tranche?.next_action === "string" ? raw.next_tranche.next_action : null,
      decompositionRequired: Boolean(raw.next_tranche?.decomposition_required),
      decompositionReasons: toStringList(raw.next_tranche?.decomposition_reasons),
      categories: toStringList(raw.next_tranche?.categories),
    },
    queue: {
      total: toNumber(raw.queue?.total),
      dispatchable: toNumber(raw.queue?.dispatchable),
      blocked: toNumber(raw.queue?.blocked),
      suppressed: toNumber(raw.queue?.suppressed),
    },
    stableOperatingDay: {
      met: Boolean(raw.stable_operating_day?.met),
      coveredWindowHours: toNumber(raw.stable_operating_day?.covered_window_hours),
      requiredWindowHours: toNumber(raw.stable_operating_day?.required_window_hours),
      includedPassCount: toNumber(raw.stable_operating_day?.included_pass_count),
      consecutiveHealthyPassCount: toNumber(raw.stable_operating_day?.consecutive_healthy_pass_count),
      detail: typeof raw.stable_operating_day?.detail === "string" ? raw.stable_operating_day.detail : null,
    },
    resultEvidence: {
      thresholdRequired: toNumber(raw.result_evidence?.threshold_required),
      thresholdProgress: toNumber(raw.result_evidence?.threshold_progress),
      thresholdMet: Boolean(raw.result_evidence?.threshold_met),
      resultBackedCompletionCount: toNumber(raw.result_evidence?.result_backed_completion_count),
      reviewBackedOutputCount: toNumber(raw.result_evidence?.review_backed_output_count),
    },
    proofGate: {
      open: Boolean(raw.proof_gate?.open),
      status: typeof raw.proof_gate?.status === "string" ? raw.proof_gate.status : "unknown",
      blockingCheckIds: toStringList(raw.proof_gate?.blocking_check_ids),
    },
    autoMutation: {
      state: typeof raw.auto_mutation?.state === "string" ? raw.auto_mutation.state : "unknown",
      proofGateOpen: Boolean(raw.auto_mutation?.proof_gate_open),
      detail: typeof raw.auto_mutation?.detail === "string" ? raw.auto_mutation.detail : null,
    },
    sourceKind: candidate.kind,
    sourcePath: candidate.path,
  };
}

export async function loadBlockerMap(): Promise<BlockerMapReadResult> {
  for (const candidate of candidatePaths()) {
    try {
      await access(candidate.path);
    } catch {
      continue;
    }

    try {
      const text = await readFile(candidate.path, "utf-8");
      const raw = JSON.parse(text) as Record<string, any>;
      const blockerMap = buildBlockerMap(raw, candidate);
      return {
        blockerMap,
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
        blockerMap: null,
        status: {
          available: false,
          degraded: true,
          detail: `Invalid blocker-map artifact at ${candidate.path}: ${error instanceof Error ? error.message : "unknown parse error"}`,
          sourceKind: candidate.kind,
          sourcePath: candidate.path,
        },
      };
    }
  }

  return {
    blockerMap: null,
    status: {
      available: false,
      degraded: true,
      detail: "Blocker-map artifact was not found in the workspace report or repo-root fallback path.",
      sourceKind: null,
      sourcePath: null,
    },
  };
}
