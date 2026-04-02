import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/operator/governance", undefined, "Failed to fetch operator governance");
}
