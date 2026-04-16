import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/learning/metrics", undefined, "Failed to fetch learning metrics");
}
