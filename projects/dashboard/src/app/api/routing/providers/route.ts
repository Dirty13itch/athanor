import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/subscriptions/provider-status", undefined, "Failed to fetch provider status");
}
