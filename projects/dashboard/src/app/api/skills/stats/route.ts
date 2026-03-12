import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/skills/stats", undefined, "Failed to fetch skill statistics");
}
