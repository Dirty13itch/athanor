import { access, readFile } from "node:fs/promises";
import path from "node:path";
import { steadyStateSnapshotSchema, type SteadyStateSnapshot } from "@/lib/contracts";

function steadyStateCandidatePaths() {
  return [
    path.resolve(process.cwd(), "reports", "truth-inventory", "steady-state-status.json"),
    path.resolve(process.cwd(), "..", "..", "reports", "truth-inventory", "steady-state-status.json"),
  ];
}

export async function readSteadyStateFrontDoor(): Promise<SteadyStateSnapshot | null> {
  for (const candidate of steadyStateCandidatePaths()) {
    try {
      await access(candidate);
      const text = await readFile(candidate, "utf-8");
      const raw = JSON.parse(text) as Record<string, any>;
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
      });
    } catch {
      continue;
    }
  }

  return null;
}
