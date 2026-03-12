import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ skillId: string }> }
) {
  const { skillId } = await context.params;
  return proxyAgentJson(`/v1/skills/${encodeURIComponent(skillId)}`, undefined, "Failed to fetch skill detail");
}
