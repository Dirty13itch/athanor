import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/governor", undefined, "Failed to fetch governor snapshot");
}
