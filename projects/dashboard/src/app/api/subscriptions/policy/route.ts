import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/subscriptions/policy", undefined, "Failed to fetch subscription policy");
}
