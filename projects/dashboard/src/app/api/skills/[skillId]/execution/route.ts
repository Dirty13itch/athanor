import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ skillId: string }> }
) {
  const { skillId } = await context.params;
  const body = await request.text();
  return proxyAgentJson(
    `/v1/skills/${encodeURIComponent(skillId)}/execution`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    },
    "Failed to record skill execution"
  );
}
