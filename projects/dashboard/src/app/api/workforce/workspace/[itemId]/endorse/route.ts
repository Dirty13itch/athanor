import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ itemId: string }> }
) {
  const { itemId } = await context.params;
  const body = await request.json();
  return proxyAgentJson(
    `/v1/workspace/${itemId}/endorse`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent_name: body.agentName ?? "" }),
    },
    "Failed to endorse workspace item"
  );
}
