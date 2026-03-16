import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/pipeline/status", undefined, "Failed to fetch pipeline status");
}
