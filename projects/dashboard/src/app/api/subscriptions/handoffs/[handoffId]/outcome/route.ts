import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { requireOperatorMutationAccess } from "@/lib/operator-auth";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ handoffId: string }> }
) {
  const gate = requireOperatorMutationAccess(request);
  if (gate) {
    return gate;
  }

  const params = await context.params;
  const handoffId = encodeURIComponent(params.handoffId);
  return proxyAgentOperatorJson(
    request,
    `/v1/subscriptions/handoffs/${handoffId}/outcome`,
    "Failed to record handoff outcome",
    {
      privilegeClass: "admin",
      defaultActor: "dashboard-operator",
      defaultReason: "Recorded provider handoff outcome",
      timeoutMs: 30_000,
    }
  );
}
