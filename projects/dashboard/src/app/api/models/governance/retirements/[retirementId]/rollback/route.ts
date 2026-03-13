import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ retirementId: string }> }
) {
  const { retirementId } = await context.params;
  const body = await request.text();
  return proxyAgentJson(
    `/v1/models/governance/retirements/${encodeURIComponent(retirementId)}/rollback`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    },
    "Failed to roll back retirement candidate"
  );
}
