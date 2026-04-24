import { NextRequest } from "next/server";
import { applyExecutionReviewDecision } from "@/lib/execution-review-control";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { requireSameOriginOperatorSessionAccess } from "@/lib/operator-auth";

type Context = { params: Promise<{ approvalId: string }> };

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

  const { approvalId } = await params;
  const body = getBodyRecord(await request.json().catch(() => ({})));
  const handled = await applyExecutionReviewDecision(
    request,
    approvalId,
    "approve",
    typeof body.reason === "string" ? body.reason : null,
  );
  if (handled) {
    return handled;
  }

  return proxyAgentOperatorJson(
    request,
    `/v1/operator/approvals/${encodeURIComponent(approvalId)}/approve`,
    "Failed to approve operator approval request",
    {
      privilegeClass: "admin",
      defaultReason: `Approved operator approval ${approvalId} from dashboard`,
      bodyOverride: {
        ...body,
        reason:
          typeof body.reason === "string" && body.reason.trim().length > 0
            ? body.reason
            : `Approved operator approval ${approvalId} from dashboard`,
      },
    }
  );
}
