import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/alerts", undefined, "Failed to fetch alerts");
}
