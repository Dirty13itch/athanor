import type { NextRequest } from "next/server";
import { parseBootstrapSyntheticApprovalId } from "@/lib/bootstrap-approvals";
import { controlBuilderSessionWithExecutionBridge } from "@/lib/builder-session-control";
import { listBuilderSyntheticApprovals } from "@/lib/builder-store";
import { executionReviewProjectionSchema } from "@/lib/contracts";
import { loadExecutionReview, loadExecutionSession } from "@/lib/executive-kernel";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

function forwardedHeaders(request: Request) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  for (const name of ["cookie", "origin", "referer", "x-forwarded-proto", "x-forwarded-host"]) {
    const value = request.headers.get(name);
    if (value) {
      headers[name] = value;
    }
  }

  return headers;
}

export async function applyExecutionReviewDecision(
  request: NextRequest,
  reviewId: string,
  action: "approve" | "reject",
  reason?: string | null,
): Promise<Response | null> {
  const builderReview = (await listBuilderSyntheticApprovals("pending")).find((review) => review.id === reviewId);
  if (builderReview) {
    const result = await controlBuilderSessionWithExecutionBridge(
      String(builderReview.related_task_id || ""),
      action,
      reviewId,
    );
    const [updatedReview, session] = await Promise.all([
      listBuilderSyntheticApprovals().then((reviews) => reviews.find((review) => review.id === reviewId) ?? builderReview),
      loadExecutionSession(String(builderReview.related_task_id || "")),
    ]);
    const review = executionReviewProjectionSchema.parse({
      id: updatedReview.id,
      family: "builder",
      source: "builder_front_door",
      owner_kind: "session",
      owner_id: String(updatedReview.related_task_id ?? ""),
      related_run_id: String(updatedReview.related_run_id ?? ""),
      related_task_id: String(updatedReview.related_task_id ?? ""),
      requested_action: updatedReview.requested_action,
      privilege_class: updatedReview.privilege_class,
      reason: updatedReview.reason,
      status: updatedReview.status,
      requested_at: Number(updatedReview.requested_at ?? 0),
      task_prompt: updatedReview.task_prompt,
      task_agent_id: updatedReview.task_agent_id,
      task_priority: updatedReview.task_priority,
      task_status: updatedReview.task_status,
      deep_link: `/builder?session=${encodeURIComponent(String(updatedReview.related_task_id ?? ""))}`,
      metadata: updatedReview.metadata ?? {},
    });
    return Response.json({
      ok: true,
      review_id: reviewId,
      approval_id: reviewId,
      review,
      session,
      terminal_href: result.terminal_href,
    });
  }

  const bootstrapReview = parseBootstrapSyntheticApprovalId(reviewId);
  if (bootstrapReview) {
    if (action === "reject") {
      return Response.json(
        {
          error: "Bootstrap synthetic reviews do not yet support reject through the shared execution review path.",
          review_id: reviewId,
          approval_id: reviewId,
        },
        { status: 409 },
      );
    }

    const response = await fetch(
      new URL(`/api/bootstrap/programs/${encodeURIComponent(bootstrapReview.programId)}/approve`, request.url),
      {
        method: "POST",
        headers: forwardedHeaders(request),
        body: JSON.stringify({
          packet_id: bootstrapReview.packetId,
          reason:
            typeof reason === "string" && reason.trim().length > 0
              ? reason
              : `Approved bootstrap packet ${bootstrapReview.packetId} from shared execution reviews`,
        }),
        cache: "no-store",
        signal: AbortSignal.timeout(60_000),
      },
    );

    if (!response.ok) {
      const payload = await response.json().catch(() => ({ error: "Failed to approve bootstrap packet" }));
      return Response.json(payload, { status: response.status });
    }

    const [review, session] = await Promise.all([
      loadExecutionReview(reviewId),
      loadExecutionSession(bootstrapReview.sliceId),
    ]);
    return Response.json({
      ok: true,
      review_id: reviewId,
      approval_id: reviewId,
      review,
      session,
      terminal_href: null,
    });
  }

  if (reviewId.startsWith("approval:")) {
    const actionLabel = action === "approve" ? "Approved" : "Rejected";
    return proxyAgentOperatorJson(
      request,
      `/v1/operator/approvals/${encodeURIComponent(reviewId)}/${action}`,
      `Failed to ${action} operator approval request`,
      {
        privilegeClass: "admin",
        defaultReason: `${actionLabel} operator approval ${reviewId} from shared execution reviews`,
        bodyOverride: {
          reason:
            typeof reason === "string" && reason.trim().length > 0
              ? reason
              : `${actionLabel} operator approval ${reviewId} from shared execution reviews`,
        },
      },
    );
  }

  return null;
}
