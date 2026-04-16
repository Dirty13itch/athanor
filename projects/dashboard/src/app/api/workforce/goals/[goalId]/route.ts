import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ goalId: string }> }
) {
  const { goalId } = await context.params;
  return proxyAgentOperatorJson(
    request,
    `/v1/goals/${goalId}`,
    "Failed to delete goal",
    {
      privilegeClass: "admin",
      defaultActor: "dashboard-operator",
      defaultReason: `Deleted goal ${goalId}`,
    }
  );
}
