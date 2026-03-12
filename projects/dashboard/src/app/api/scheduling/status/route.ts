import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/scheduling/status", undefined, "Failed to fetch scheduling status");
}
