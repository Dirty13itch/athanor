import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/consolidate/stats", undefined, "Failed to fetch consolidation stats");
}
