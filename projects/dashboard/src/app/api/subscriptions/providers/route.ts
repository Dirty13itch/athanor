import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/subscriptions/providers", undefined, "Failed to fetch subscription providers");
}
