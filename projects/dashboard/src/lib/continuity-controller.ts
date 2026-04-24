import { access, readFile } from "node:fs/promises";
import { candidateTruthInventoryPaths, type TruthInventoryCandidatePath, type TruthInventorySourceKind } from "@/lib/truth-inventory-paths";

export type ContinuityControllerSourceKind = TruthInventorySourceKind;
type ContinuityControllerCandidatePath = TruthInventoryCandidatePath<ContinuityControllerSourceKind>;

export interface ContinuityControllerState {
  generatedAt: string;
  controllerStatus: string;
  activePassId: string | null;
  activeFamilyId: string | null;
  activeSubtrancheId: string | null;
  startedAt: string | null;
  finishedAt: string | null;
  lastSuccessfulPassAt: string | null;
  lastMeaningfulDeltaAt: string | null;
  lastSkipReason: string | null;
  backoffUntil: string | null;
  consecutiveNoDeltaPasses: number;
  nextTarget: {
    kind: string;
    familyId: string | null;
    familyTitle: string | null;
    subtrancheId: string | null;
    subtrancheTitle: string | null;
  } | null;
  sourceKind: ContinuityControllerSourceKind;
  sourcePath: string;
}

export interface ContinuityControllerReadStatus {
  available: boolean;
  degraded: boolean;
  detail: string | null;
  sourceKind: ContinuityControllerSourceKind | null;
  sourcePath: string | null;
}

export interface ContinuityControllerReadResult {
  continuityController: ContinuityControllerState | null;
  status: ContinuityControllerReadStatus;
}

function candidatePaths(): ContinuityControllerCandidatePath[] {
  return candidateTruthInventoryPaths("continuity-controller-state.json");
}

function toNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function buildContinuityController(
  raw: Record<string, any>,
  candidate: ContinuityControllerCandidatePath,
): ContinuityControllerState {
  return {
    generatedAt: typeof raw.generated_at === "string" ? raw.generated_at : "",
    controllerStatus: typeof raw.controller_status === "string" ? raw.controller_status : "unknown",
    activePassId: typeof raw.active_pass_id === "string" ? raw.active_pass_id : null,
    activeFamilyId: typeof raw.active_family_id === "string" ? raw.active_family_id : null,
    activeSubtrancheId: typeof raw.active_subtranche_id === "string" ? raw.active_subtranche_id : null,
    startedAt: typeof raw.started_at === "string" ? raw.started_at : null,
    finishedAt: typeof raw.finished_at === "string" ? raw.finished_at : null,
    lastSuccessfulPassAt:
      typeof raw.last_successful_pass_at === "string" ? raw.last_successful_pass_at : null,
    lastMeaningfulDeltaAt:
      typeof raw.last_meaningful_delta_at === "string" ? raw.last_meaningful_delta_at : null,
    lastSkipReason: typeof raw.last_skip_reason === "string" ? raw.last_skip_reason : null,
    backoffUntil: typeof raw.backoff_until === "string" ? raw.backoff_until : null,
    consecutiveNoDeltaPasses: toNumber(raw.consecutive_no_delta_passes),
    nextTarget:
      raw.next_target && typeof raw.next_target === "object"
        ? {
            kind: typeof raw.next_target.kind === "string" ? raw.next_target.kind : "unknown",
            familyId: typeof raw.next_target.family_id === "string" ? raw.next_target.family_id : null,
            familyTitle: typeof raw.next_target.family_title === "string" ? raw.next_target.family_title : null,
            subtrancheId:
              typeof raw.next_target.subtranche_id === "string" ? raw.next_target.subtranche_id : null,
            subtrancheTitle:
              typeof raw.next_target.subtranche_title === "string" ? raw.next_target.subtranche_title : null,
          }
        : null,
    sourceKind: candidate.kind,
    sourcePath: candidate.path,
  };
}

export async function loadContinuityController(): Promise<ContinuityControllerReadResult> {
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
        continuityController: buildContinuityController(raw, candidate),
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
        continuityController: null,
        status: {
          available: false,
          degraded: true,
          detail: `Invalid continuity controller artifact at ${candidate.path}: ${error instanceof Error ? error.message : "unknown parse error"}`,
          sourceKind: candidate.kind,
          sourcePath: candidate.path,
        },
      };
    }
  }

  return {
    continuityController: null,
    status: {
      available: false,
      degraded: true,
      detail: "Continuity controller artifact was not found in the workspace report or repo-root fallback path.",
      sourceKind: null,
      sourcePath: null,
    },
  };
}
