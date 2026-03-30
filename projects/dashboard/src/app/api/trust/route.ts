import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/trust", undefined, "Failed to fetch trust scores");
}
