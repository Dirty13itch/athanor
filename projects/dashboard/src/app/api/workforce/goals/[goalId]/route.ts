import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function DELETE(
  _request: NextRequest,
  context: { params: Promise<{ goalId: string }> }
) {
  const { goalId } = await context.params;
  return proxyAgentJson(`/v1/goals/${goalId}`, { method: "DELETE" }, "Failed to delete goal");
}
