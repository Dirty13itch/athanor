import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/briefing", undefined, "Failed to fetch briefing");
}
