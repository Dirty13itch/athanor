import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/operator/summary", undefined, "Failed to fetch operator work summary");
}
