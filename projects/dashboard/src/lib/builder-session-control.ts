import {
  applyBuilderSessionControl,
  createBuilderEvent,
  mutateBuilderSession,
  readBuilderSession,
} from "@/lib/builder-store";
import { cancelBuilderExecution, resumeBuilderExecution, startBuilderExecution } from "@/lib/builder-worker-bridge";
import type { BuilderControlAction, BuilderExecutionSession } from "@/lib/contracts";

export async function controlBuilderSessionWithExecutionBridge(
  sessionId: string,
  action: BuilderControlAction,
  approvalId?: string | null,
): Promise<{ session: BuilderExecutionSession; terminal_href: string | null }> {
  const result = await applyBuilderSessionControl(sessionId, action, approvalId ?? null);

  const isLiveCodexRoute =
    result.session.route_decision.route_id === "builder:codex:direct_cli" &&
    result.session.route_decision.activation_state === "live_ready";

  if (isLiveCodexRoute) {
    try {
      if (action === "approve") {
        if (result.session.latest_result_packet?.resumable_handle) {
          await resumeBuilderExecution(sessionId);
        } else {
          await startBuilderExecution(sessionId);
        }
      } else if (action === "cancel") {
        await cancelBuilderExecution(sessionId);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Builder execution handoff failed";
      await mutateBuilderSession(sessionId, (session, events) => {
        session.status = "failed";
        session.shadow_mode = false;
        session.fallback_state = "execution_launch_failed";
        session.verification_state = {
          status: "failed",
          summary: message,
          completed_checks: [],
          failed_checks: ["execution_launch_failed"],
          last_updated_at: new Date().toISOString(),
        };
        session.latest_result_packet = session.latest_result_packet
          ? {
              ...session.latest_result_packet,
              outcome: "failed",
              summary: message,
              recovery_gate: "operator_review_required",
              remaining_risks: [message],
            }
          : {
              outcome: "failed",
              summary: message,
              artifacts: [],
              files_changed: [],
              validation: [],
              remaining_risks: [message],
              resumable_handle: null,
              recovery_gate: "operator_review_required",
            };
        events.push(
          createBuilderEvent(
            "execution_launch_failed",
            "Execution handoff failed",
            message,
            "danger",
          ),
        );
      });
    }
  }

  return {
    session: (await readBuilderSession(sessionId)) ?? result.session,
    terminal_href: result.terminal_href,
  };
}
