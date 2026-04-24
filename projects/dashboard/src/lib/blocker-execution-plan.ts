import { access, readFile } from "node:fs/promises";
import { candidateTruthInventoryPaths, type TruthInventoryCandidatePath, type TruthInventorySourceKind } from "@/lib/truth-inventory-paths";

export type BlockerExecutionPlanSourceKind = TruthInventorySourceKind;
type BlockerExecutionPlanCandidatePath = TruthInventoryCandidatePath<BlockerExecutionPlanSourceKind>;

export interface BlockerExecutionPlan {
  generatedAt: string;
  selectionMode: string;
  nextFamilyId: string | null;
  nextTarget: {
    kind: string;
    familyId: string | null;
    familyTitle: string | null;
    subtrancheId: string | null;
    subtrancheTitle: string | null;
    executionClass: string | null;
    approvalGated: boolean;
    externalBlocked: boolean;
  };
  families: Array<{
    id: string;
    title: string;
    executionClass: string;
    matchCount: number;
    nextAction: string;
    decompositionRequired: boolean;
    nextSubtrancheId: string | null;
    nextSubtrancheTitle: string | null;
    subtranches: Array<{
      id: string;
      title: string;
      sequence: number;
      status: string;
    }>;
  }>;
  sourceKind: BlockerExecutionPlanSourceKind;
  sourcePath: string;
}

export interface BlockerExecutionPlanReadStatus {
  available: boolean;
  degraded: boolean;
  detail: string | null;
  sourceKind: BlockerExecutionPlanSourceKind | null;
  sourcePath: string | null;
}

export interface BlockerExecutionPlanReadResult {
  blockerExecutionPlan: BlockerExecutionPlan | null;
  status: BlockerExecutionPlanReadStatus;
}

function candidatePaths(): BlockerExecutionPlanCandidatePath[] {
  return candidateTruthInventoryPaths("blocker-execution-plan.json");
}

function toNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function buildPlan(raw: Record<string, any>, candidate: BlockerExecutionPlanCandidatePath): BlockerExecutionPlan {
  return {
    generatedAt: typeof raw.generated_at === "string" ? raw.generated_at : "",
    selectionMode: typeof raw.selection_mode === "string" ? raw.selection_mode : "unknown",
    nextFamilyId: typeof raw.next_family_id === "string" ? raw.next_family_id : null,
    nextTarget: {
      kind: typeof raw.next_target?.kind === "string" ? raw.next_target.kind : "unknown",
      familyId: typeof raw.next_target?.family_id === "string" ? raw.next_target.family_id : null,
      familyTitle: typeof raw.next_target?.family_title === "string" ? raw.next_target.family_title : null,
      subtrancheId: typeof raw.next_target?.subtranche_id === "string" ? raw.next_target.subtranche_id : null,
      subtrancheTitle:
        typeof raw.next_target?.subtranche_title === "string" ? raw.next_target.subtranche_title : null,
      executionClass:
        typeof raw.next_target?.execution_class === "string" ? raw.next_target.execution_class : null,
      approvalGated: Boolean(raw.next_target?.approval_gated),
      externalBlocked: Boolean(raw.next_target?.external_blocked),
    },
    families: Array.isArray(raw.families)
      ? raw.families
          .filter((item: unknown): item is Record<string, any> => Boolean(item && typeof item === "object"))
          .map((item) => ({
            id: typeof item.id === "string" ? item.id : "",
            title: typeof item.title === "string" ? item.title : "",
            executionClass: typeof item.execution_class === "string" ? item.execution_class : "unknown",
            matchCount: toNumber(item.match_count),
            nextAction: typeof item.next_action === "string" ? item.next_action : "",
            decompositionRequired: Boolean(item.decomposition_required),
            nextSubtrancheId: typeof item.next_subtranche_id === "string" ? item.next_subtranche_id : null,
            nextSubtrancheTitle:
              typeof item.next_subtranche_title === "string" ? item.next_subtranche_title : null,
            subtranches: Array.isArray(item.subtranches)
              ? item.subtranches
                  .filter((subtranche: unknown): subtranche is Record<string, any> => Boolean(subtranche && typeof subtranche === "object"))
                  .map((subtranche) => ({
                    id: typeof subtranche.id === "string" ? subtranche.id : "",
                    title: typeof subtranche.title === "string" ? subtranche.title : "",
                    sequence: toNumber(subtranche.sequence),
                    status: typeof subtranche.status === "string" ? subtranche.status : "pending",
                  }))
              : [],
          }))
      : [],
    sourceKind: candidate.kind,
    sourcePath: candidate.path,
  };
}

export async function loadBlockerExecutionPlan(): Promise<BlockerExecutionPlanReadResult> {
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
        blockerExecutionPlan: buildPlan(raw, candidate),
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
        blockerExecutionPlan: null,
        status: {
          available: false,
          degraded: true,
          detail: `Invalid blocker execution plan artifact at ${candidate.path}: ${error instanceof Error ? error.message : "unknown parse error"}`,
          sourceKind: candidate.kind,
          sourcePath: candidate.path,
        },
      };
    }
  }

  return {
    blockerExecutionPlan: null,
    status: {
      available: false,
      degraded: true,
      detail: "Blocker execution plan artifact was not found in the workspace report or repo-root fallback path.",
      sourceKind: null,
      sourcePath: null,
    },
  };
}
