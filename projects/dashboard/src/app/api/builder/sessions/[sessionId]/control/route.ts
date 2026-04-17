import { builderSessionControlRequestSchema } from "@/lib/contracts";
import { applyBuilderSessionControl, createBuilderEvent, mutateBuilderSession, readBuilderSession } from "@/lib/builder-store";
import { cancelBuilderExecution, resumeBuilderExecution, startBuilderExecution } from "@/lib/builder-worker-bridge";
import { requireOperatorMutationAccess } from "@/lib/operator-auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(
  request: Request,
  context: { params: Promise<{ sessionId: string }> },
) {
  const gate = requireOperatorMutationAccess(request);
  if (gate) {
    return gate;
  }

  try {
    const { sessionId } = await context.params;
    const body = await request.json().catch(() => ({}));
    const parsed = builderSessionControlRequestSchema.safeParse(body);
    if (!parsed.success) {
      return Response.json(
        { error: "Invalid builder control payload", issues: parsed.error.flatten() },
        { status: 400 },
      );
    }

    const result = await applyBuilderSessionControl(
      sessionId,
      parsed.data.action,
      parsed.data.approval_id ?? null,
    );

    const isLiveCodexRoute =
      result.session.route_decision.route_id === "builder:codex:direct_cli" &&
      result.session.route_decision.activation_state === "live_ready";

    if (isLiveCodexRoute) {
      try {
        if (parsed.data.action === "approve") {
          if (result.session.latest_result_packet?.resumable_handle) {
            await resumeBuilderExecution(sessionId);
          } else {
            await startBuilderExecution(sessionId);
          }
        } else if (parsed.data.action === "cancel") {
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

    const session = (await readBuilderSession(sessionId)) ?? result.session;
    return Response.json({ ok: true, session, terminal_href: result.terminal_href });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to update builder session";
    const status = message.includes("not found") || message.includes("Unknown builder session") ? 404 : 500;
    return Response.json({ error: message }, { status });
  }
}
