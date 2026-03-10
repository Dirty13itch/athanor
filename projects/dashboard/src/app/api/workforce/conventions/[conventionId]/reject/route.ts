import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function POST(
  _request: NextRequest,
  context: { params: Promise<{ conventionId: string }> }
) {
  const { conventionId } = await context.params;
  return proxyAgentJson(
    `/v1/conventions/${conventionId}/reject`,
    { method: "POST" },
    "Failed to reject convention"
  );
}
