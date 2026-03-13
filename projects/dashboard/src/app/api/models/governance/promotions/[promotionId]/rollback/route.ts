import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ promotionId: string }> }
) {
  const { promotionId } = await context.params;
  const body = await request.text();
  return proxyAgentJson(
    `/v1/models/governance/promotions/${encodeURIComponent(promotionId)}/rollback`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    },
    "Failed to roll back promotion candidate"
  );
}
