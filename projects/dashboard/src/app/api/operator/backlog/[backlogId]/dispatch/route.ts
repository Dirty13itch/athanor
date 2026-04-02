import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

type Context = { params: Promise<{ backlogId: string }> };

export async function POST(request: NextRequest, context: Context) {
  const { backlogId } = await context.params;
  const body = await request.json().catch(() => ({}));
  return proxyAgentOperatorJson(request, `/v1/operator/backlog/${encodeURIComponent(backlogId)}/dispatch`, "Failed to dispatch operator backlog item", {
    privilegeClass: "operator",
    defaultReason: "Dispatched operator backlog item from dashboard",
    bodyOverride: {
      lane_override: (body as { lane_override?: unknown }).lane_override ?? "",
      reason: (body as { reason?: unknown }).reason ?? "Dispatched operator backlog item from dashboard",
    },
  });
}
