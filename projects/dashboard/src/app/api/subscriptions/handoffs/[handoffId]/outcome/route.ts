import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ handoffId: string }> }
) {
  const params = await context.params;
  const handoffId = encodeURIComponent(params.handoffId);
  const body = await request.text();
  return proxyAgentJson(
    `/v1/subscriptions/handoffs/${handoffId}/outcome`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    },
    "Failed to record handoff outcome",
    30_000
  );
}
