import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

type Context = { params: Promise<{ backlogId: string }> };

export async function POST(request: NextRequest, context: Context) {
  const { backlogId } = await context.params;
  const body = await request.json().catch(() => ({}));
  return proxyAgentOperatorJson(request, `/v1/operator/backlog/${encodeURIComponent(backlogId)}/transition`, "Failed to transition operator backlog item", {
    privilegeClass: "operator",
    defaultReason: "Transitioned operator backlog item from dashboard",
    bodyOverride: {
      status: (body as { status?: unknown }).status ?? "",
      note: (body as { note?: unknown }).note ?? "",
      blocking_reason: (body as { blocking_reason?: unknown }).blocking_reason ?? "",
      reason: (body as { reason?: unknown }).reason ?? "Transitioned operator backlog item from dashboard",
    },
  });
}
