import { NextRequest } from "next/server";
import { applyExecutionReviewDecision } from "@/lib/execution-review-control";
import { requireSameOriginOperatorSessionAccess } from "@/lib/operator-auth";

type Context = { params: Promise<{ reviewId: string }> };

function getBodyRecord(body: unknown): Record<string, unknown> {
  return body && typeof body === "object" && !Array.isArray(body)
    ? (body as Record<string, unknown>)
    : {};
}

export async function POST(request: NextRequest, { params }: Context) {
  const gate = requireSameOriginOperatorSessionAccess(request);
  if (gate) {
    return gate;
  }

  const { reviewId } = await params;
  const body = getBodyRecord(await request.json().catch(() => ({})));
  const handled = await applyExecutionReviewDecision(
    request,
    reviewId,
    "reject",
    typeof body.reason === "string" ? body.reason : null,
  );

  if (handled) {
    return handled;
  }

  return Response.json({ error: "Execution review not found" }, { status: 404 });
}
