import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/improvement/summary", undefined, "Failed to fetch improvement summary");
}
