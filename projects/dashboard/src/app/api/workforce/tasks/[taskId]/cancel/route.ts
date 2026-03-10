import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function POST(
  _request: NextRequest,
  context: { params: Promise<{ taskId: string }> }
) {
  const { taskId } = await context.params;
  return proxyAgentJson(`/v1/tasks/${taskId}/cancel`, { method: "POST" }, "Failed to cancel task");
}
