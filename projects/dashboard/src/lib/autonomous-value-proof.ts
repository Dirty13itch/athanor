import { access, readFile } from "node:fs/promises";
import { candidateTruthInventoryPaths, type TruthInventoryCandidatePath, type TruthInventorySourceKind } from "@/lib/truth-inventory-paths";

export type AutonomousValueProofSourceKind = TruthInventorySourceKind;
type AutonomousValueProofCandidatePath = TruthInventoryCandidatePath<AutonomousValueProofSourceKind>;

export interface AutonomousValueProof {
  generatedAt: string;
  acceptedEntryCount: number;
  acceptedOperatorValueCount: number;
  acceptedProductValueCount: number;
  disqualifiedEntryCount: number;
  failureCounts: Record<string, number>;
  latestAcceptedEntry: {
    packetId: string;
    title: string;
    valueClass: string;
    deliverableKind: string;
    beneficiarySurface: string;
    acceptedAt: string | null;
  } | null;
  acceptedEntries: Array<{
    packetId: string;
    title: string;
    valueClass: string;
    deliverableKind: string;
    beneficiarySurface: string;
    deliverableRefs: string[];
    acceptedAt: string | null;
  }>;
  disqualifiedEntries: Array<{
    packetId: string;
    title: string;
    disqualificationReason: string;
  }>;
  stageStatus: {
    operatorValue: {
      requiredCount: number;
      acceptedCount: number;
      distinctFamilyCount: number;
      remainingRequired: number;
      met: boolean;
    };
    productValue: {
      requiredCount: number;
      acceptedCount: number;
      visibleSurfaceCount: number;
      remainingRequired: number;
      met: boolean;
    };
  };
  degradedSections: string[];
  sourceKind: AutonomousValueProofSourceKind;
  sourcePath: string;
}

export interface AutonomousValueProofReadStatus {
  available: boolean;
  degraded: boolean;
  detail: string | null;
  sourceKind: AutonomousValueProofSourceKind | null;
  sourcePath: string | null;
}

export interface AutonomousValueProofReadResult {
  proof: AutonomousValueProof | null;
  status: AutonomousValueProofReadStatus;
}

function candidatePaths(): AutonomousValueProofCandidatePath[] {
  return candidateTruthInventoryPaths("autonomous-value-proof.json");
}

function toNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function toString(value: unknown) {
  return typeof value === "string" ? value : "";
}

function toStringList(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item: unknown): item is string => typeof item === "string" && item.length > 0)
    : [];
}

function buildProof(raw: Record<string, any>, candidate: AutonomousValueProofCandidatePath): AutonomousValueProof {
  const latest = raw.latest_accepted_entry && typeof raw.latest_accepted_entry === "object" ? raw.latest_accepted_entry : null;
  return {
    generatedAt: toString(raw.generated_at),
    acceptedEntryCount: toNumber(raw.accepted_entry_count),
    acceptedOperatorValueCount: toNumber(raw.accepted_operator_value_count),
    acceptedProductValueCount: toNumber(raw.accepted_product_value_count),
    disqualifiedEntryCount: toNumber(raw.disqualified_entry_count),
    failureCounts:
      raw.failure_counts && typeof raw.failure_counts === "object"
        ? { ...(raw.failure_counts as Record<string, number>) }
        : {},
    latestAcceptedEntry: latest
      ? {
          packetId: toString(latest.packet_id),
          title: toString(latest.title),
          valueClass: toString(latest.value_class),
          deliverableKind: toString(latest.deliverable_kind),
          beneficiarySurface: toString(latest.beneficiary_surface),
          acceptedAt: toString(latest.accepted_at) || null,
        }
      : null,
    acceptedEntries: Array.isArray(raw.accepted_entries)
      ? raw.accepted_entries.map((item: Record<string, unknown>) => ({
          packetId: toString(item.packet_id),
          title: toString(item.title),
          valueClass: toString(item.value_class),
          deliverableKind: toString(item.deliverable_kind),
          beneficiarySurface: toString(item.beneficiary_surface),
          deliverableRefs: toStringList(item.deliverable_refs),
          acceptedAt: toString(item.accepted_at) || null,
        }))
      : [],
    disqualifiedEntries: Array.isArray(raw.disqualified_entries)
      ? raw.disqualified_entries.map((item: Record<string, unknown>) => ({
          packetId: toString(item.packet_id),
          title: toString(item.title),
          disqualificationReason: toString(item.disqualification_reason),
        }))
      : [],
    stageStatus: {
      operatorValue: {
        requiredCount: toNumber(raw.stage_status?.operator_value?.required_count),
        acceptedCount: toNumber(raw.stage_status?.operator_value?.accepted_count),
        distinctFamilyCount: toNumber(raw.stage_status?.operator_value?.distinct_family_count),
        remainingRequired: toNumber(raw.stage_status?.operator_value?.remaining_required),
        met: Boolean(raw.stage_status?.operator_value?.met),
      },
      productValue: {
        requiredCount: toNumber(raw.stage_status?.product_value?.required_count),
        acceptedCount: toNumber(raw.stage_status?.product_value?.accepted_count),
        visibleSurfaceCount: toNumber(raw.stage_status?.product_value?.visible_surface_count),
        remainingRequired: toNumber(raw.stage_status?.product_value?.remaining_required),
        met: Boolean(raw.stage_status?.product_value?.met),
      },
    },
    degradedSections: Array.isArray(raw.degraded_sections)
      ? raw.degraded_sections.filter((item: unknown): item is string => typeof item === "string" && item.length > 0)
      : [],
    sourceKind: candidate.kind,
    sourcePath: candidate.path,
  };
}

export async function loadAutonomousValueProof(): Promise<AutonomousValueProofReadResult> {
  for (const candidate of candidatePaths()) {
    try {
      await access(candidate.path);
    } catch {
      continue;
    }

    try {
      const text = await readFile(candidate.path, "utf-8");
      const raw = JSON.parse(text) as Record<string, any>;
      const proof = buildProof(raw, candidate);
      const degradedDetail =
        proof.degradedSections.length > 0
          ? `Autonomous value proof is running in degraded mode: ${proof.degradedSections.join(" · ")}`
          : null;
      return {
        proof,
        status: {
          available: true,
          degraded: Boolean(degradedDetail),
          detail: degradedDetail,
          sourceKind: candidate.kind,
          sourcePath: candidate.path,
        },
      };
    } catch (error) {
      return {
        proof: null,
        status: {
          available: false,
          degraded: true,
          detail: `Invalid autonomous-value proof at ${candidate.path}: ${error instanceof Error ? error.message : "unknown parse error"}`,
          sourceKind: candidate.kind,
          sourcePath: candidate.path,
        },
      };
    }
  }

  return {
    proof: null,
    status: {
      available: false,
      degraded: true,
      detail: "Autonomous-value proof artifact was not found in the workspace report or repo-root fallback path.",
      sourceKind: null,
      sourcePath: null,
    },
  };
}
