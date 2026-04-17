import { access, readFile } from "node:fs/promises";
import path from "node:path";
import {
  capabilityPilotReadinessSnapshotSchema,
  type CapabilityPilotReadinessSnapshot,
} from "@/lib/contracts";

type CapabilityPilotReadinessCandidatePath = {
  kind: "workspace_generated_atlas" | "repo_root_fallback";
  path: string;
};

const CAPABILITY_PRIORITY = [
  {
    capabilityId: "letta-memory-plane",
    label: "Letta Memory Plane",
  },
  {
    capabilityId: "openhands-bounded-worker-lane",
    label: "OpenHands Bounded Worker Lane",
  },
  {
    capabilityId: "agent-governance-toolkit-policy-plane",
    label: "Agent Governance Toolkit Policy Plane",
  },
] as const;

function candidatePaths(): CapabilityPilotReadinessCandidatePath[] {
  return [
    {
      kind: "workspace_generated_atlas",
      path: path.resolve(process.cwd(), "src", "generated", "master-atlas.json"),
    },
    {
      kind: "repo_root_fallback",
      path: path.resolve(process.cwd(), "projects", "dashboard", "src", "generated", "master-atlas.json"),
    },
  ];
}

function coerceString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function coerceBoolean(value: unknown): boolean {
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "string") {
    return /^(1|true|yes|on)$/i.test(value.trim());
  }
  if (typeof value === "number") {
    return value !== 0;
  }
  return false;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value
        .filter((item): item is string => typeof item === "string" && item.trim().length > 0)
        .map((item) => item.trim())
    : [];
}

function buildFallbackSnapshot(detail: string, candidate: CapabilityPilotReadinessCandidatePath | null = null) {
  return capabilityPilotReadinessSnapshotSchema.parse({
    generatedAt: new Date().toISOString(),
    available: false,
    degraded: true,
    detail,
    sourceKind: candidate?.kind ?? null,
    sourcePath: candidate?.path ?? null,
    summary: {
      total: 0,
      formalEvalComplete: 0,
      formalEvalFailed: 0,
      manualReviewPending: 0,
      readyForFormalEval: 0,
      operatorSmokeOnly: 0,
      scaffoldOnly: 0,
      blocked: 0,
    },
    records: [],
  });
}

function readCapabilityPilotRecords(bundle: Record<string, unknown>) {
  const feed =
    bundle.capability_pilot_readiness &&
    typeof bundle.capability_pilot_readiness === "object" &&
    Array.isArray((bundle.capability_pilot_readiness as { records?: unknown[] }).records)
      ? ((bundle.capability_pilot_readiness as { records: Array<Record<string, unknown>> }).records ?? [])
      : [];

  const records = CAPABILITY_PRIORITY.flatMap(({ capabilityId, label }) => {
    const rawRecord = feed.find((record) => {
      const recordCapabilityId = coerceString(record.capability_id) || coerceString(record.initiative_id);
      return recordCapabilityId === capabilityId;
    });

    if (!rawRecord) {
      return [];
    }

    return [
      {
        capabilityId,
        label: coerceString(rawRecord.label) || label,
        laneStatus: coerceString(rawRecord.lane_status) || null,
        capabilityStage: coerceString(rawRecord.capability_stage) || null,
        hostId: coerceString(rawRecord.host_id) || "unknown",
        readinessState: coerceString(rawRecord.readiness_state) || "unknown",
        proofTier: coerceString(rawRecord.proof_tier) || null,
        blockingReasons: asStringArray(rawRecord.blocking_reasons),
        commandChecks: Array.isArray(rawRecord.command_checks)
          ? rawRecord.command_checks
              .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
              .map((item) => ({
                command: coerceString(item.command),
                availableLocally: coerceBoolean(item.available_locally),
                inventoryStatus: coerceString(item.inventory_status) || "missing",
                inventoryVersion: coerceString(item.inventory_version) || null,
                localPath: coerceString(item.local_path) || null,
              }))
          : [],
        packetPath: coerceString(rawRecord.packet_path) || null,
        latestEvalRunId: coerceString(rawRecord.run_id) || coerceString(rawRecord.latest_eval_run_id) || null,
        latestEvalStatus: coerceString(rawRecord.latest_eval_status) || null,
        latestEvalOutcome: coerceString(rawRecord.latest_eval_outcome) || null,
        latestEvalAt: coerceString(rawRecord.latest_eval_at) || null,
        formalEvalStatus: coerceString(rawRecord.formal_eval_status) || null,
        formalEvalAt: coerceString(rawRecord.formal_eval_at) || null,
        formalEvalDecisionReason: coerceString(rawRecord.formal_eval_decision_reason) || null,
        formalEvalPrimaryFailureHint: coerceString(rawRecord.formal_eval_primary_failure_hint) || null,
        formalPreflightStatus: coerceString(rawRecord.formal_preflight_status) || null,
        formalPreflightAt: coerceString(rawRecord.formal_preflight_at) || null,
        formalPreflightBlockerClass: coerceString(rawRecord.formal_preflight_blocker_class) || null,
        formalPreflightBlockingReasons: asStringArray(rawRecord.formal_preflight_blocking_reasons),
        formalPreflightMissingCommands: asStringArray(rawRecord.formal_preflight_missing_commands),
        formalPreflightMissingEnvVars: asStringArray(rawRecord.formal_preflight_missing_env_vars),
        formalPreflightMissingFixtureFiles: asStringArray(rawRecord.formal_preflight_missing_fixture_files),
        formalPreflightMissingResultFiles: asStringArray(rawRecord.formal_preflight_missing_result_files),
        manualReviewOutcome: coerceString(rawRecord.manual_review_outcome) || null,
        manualReviewSummary: coerceString(rawRecord.manual_review_summary) || null,
        nextAction: coerceString(rawRecord.next_action) || null,
        nextFormalGate: coerceString(rawRecord.next_formal_gate) || null,
        formalRunnerSupport: coerceString(rawRecord.formal_runner_support) || null,
      },
    ];
  });

  const missingCapabilityIds = CAPABILITY_PRIORITY.filter(
    ({ capabilityId }) => !records.some((record) => record.capabilityId === capabilityId),
  ).map(({ capabilityId, label }) => `${label} (${capabilityId})`);

  const summary = {
    total: records.length,
    formalEvalComplete: records.filter((record) => record.readinessState === "formal_eval_complete").length,
    formalEvalFailed: records.filter((record) => record.readinessState === "formal_eval_failed").length,
    manualReviewPending: records.filter((record) => record.readinessState === "manual_review_pending").length,
    readyForFormalEval: records.filter((record) => record.readinessState === "ready_for_formal_eval").length,
    operatorSmokeOnly: records.filter((record) => record.readinessState === "operator_smoke_only").length,
    scaffoldOnly: records.filter((record) => record.readinessState === "scaffold_only").length,
    blocked: records.filter((record) => record.readinessState === "blocked").length,
  };

  return { records, summary, missingCapabilityIds };
}

function buildSnapshotFromBundle(
  bundle: Record<string, unknown>,
  candidate: CapabilityPilotReadinessCandidatePath,
): CapabilityPilotReadinessSnapshot {
  const { records, summary, missingCapabilityIds } = readCapabilityPilotRecords(bundle);
  const rawGeneratedAt = coerceString(bundle.generated_at) || new Date().toISOString();
  const detail = missingCapabilityIds.length
    ? `Capability pilot readiness feed is missing records for ${missingCapabilityIds.join(", ")}.`
    : null;

  return capabilityPilotReadinessSnapshotSchema.parse({
    generatedAt: rawGeneratedAt,
    available: true,
    degraded: missingCapabilityIds.length > 0,
    detail,
    sourceKind: candidate.kind,
    sourcePath: candidate.path,
    summary,
    records,
  });
}

export async function loadCapabilityPilotReadiness(): Promise<CapabilityPilotReadinessSnapshot> {
  for (const candidate of candidatePaths()) {
    try {
      await access(candidate.path);
    } catch {
      continue;
    }

    try {
      const text = await readFile(candidate.path, "utf-8");
      const bundle = JSON.parse(text) as Record<string, unknown>;
      return buildSnapshotFromBundle(bundle, candidate);
    } catch (error) {
      return buildFallbackSnapshot(
        `Invalid capability pilot readiness feed at ${candidate.path}: ${error instanceof Error ? error.message : "unknown parse error"}`,
        candidate,
      );
    }
  }

  return buildFallbackSnapshot(
    "Capability pilot readiness feed was not found in the workspace master atlas or repo-root fallback path.",
  );
}
