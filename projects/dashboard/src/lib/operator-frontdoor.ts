import { access, readFile } from "node:fs/promises";
import path from "node:path";
import {
  steadyStateSnapshotSchema,
  type SteadyStateReadStatus,
  type SteadyStateSnapshot,
} from "@/lib/contracts";

interface SteadyStateCandidatePath {
  kind: "workspace_report" | "repo_root_fallback";
  path: string;
}

export interface SteadyStateFrontDoorReadResult {
  snapshot: SteadyStateSnapshot | null;
  status: SteadyStateReadStatus;
}

function steadyStateCandidatePaths(): SteadyStateCandidatePath[] {
  return [
    {
      kind: "workspace_report",
      path: path.resolve(process.cwd(), "reports", "truth-inventory", "steady-state-status.json"),
    },
    {
      kind: "repo_root_fallback",
      path: path.resolve(process.cwd(), "..", "..", "reports", "truth-inventory", "steady-state-status.json"),
    },
  ];
}

function buildSnapshot(raw: Record<string, any>, candidate: SteadyStateCandidatePath): SteadyStateSnapshot {
  return steadyStateSnapshotSchema.parse({
    generatedAt: raw.generated_at,
    closureState: raw.closure_state,
    operatorMode: raw.operator_mode,
    interventionLabel: raw.intervention_label,
    interventionLevel: raw.intervention_level,
    interventionSummary: raw.intervention_summary,
    needsYou: raw.needs_you,
    nextOperatorAction: raw.next_operator_action,
    queueDispatchable: raw.queue_dispatchable ?? 0,
    queueTotal: raw.queue_total ?? 0,
    suppressedTaskCount: raw.suppressed_task_count ?? 0,
    runtimePacketCount: raw.runtime_packet_count ?? 0,
    currentWork: raw.current_work
      ? {
          taskId: raw.current_work.task_id ?? null,
          taskTitle: raw.current_work.task_title ?? null,
          providerLabel: raw.current_work.provider_label ?? null,
          laneFamily: raw.current_work.lane_family ?? null,
        }
      : null,
    nextUp: raw.next_up
      ? {
          taskId: raw.next_up.task_id ?? null,
          taskTitle: raw.next_up.task_title ?? null,
          providerLabel: raw.next_up.provider_label ?? null,
          laneFamily: raw.next_up.lane_family ?? null,
        }
      : null,
    sourceKind: candidate.kind,
    sourcePath: candidate.path,
  });
}

export async function loadSteadyStateFrontDoor(): Promise<SteadyStateFrontDoorReadResult> {
  for (const candidate of steadyStateCandidatePaths()) {
    try {
      await access(candidate.path);
    } catch {
      continue;
    }

    try {
      const text = await readFile(candidate.path, "utf-8");
      const raw = JSON.parse(text) as Record<string, any>;
      const snapshot = buildSnapshot(raw, candidate);
      return {
        snapshot,
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
        snapshot: null,
        status: {
          available: false,
          degraded: true,
          detail: `Invalid steady-state front door at ${candidate.path}: ${error instanceof Error ? error.message : "unknown parse error"}`,
          sourceKind: candidate.kind,
          sourcePath: candidate.path,
        },
      };
    }
  }

  return {
    snapshot: null,
    status: {
      available: false,
      degraded: true,
      detail: "Steady-state front door was not found in the workspace report or repo-root fallback path.",
      sourceKind: null,
      sourcePath: null,
    },
  };
}

export async function readSteadyStateFrontDoor(): Promise<SteadyStateSnapshot | null> {
  const result = await loadSteadyStateFrontDoor();
  if (!result.snapshot && result.status.degraded) {
    throw new Error(result.status.detail ?? "Steady-state front door is unavailable.");
  }
  return result.snapshot;
}
