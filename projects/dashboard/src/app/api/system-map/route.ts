import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/system-map", undefined, "Failed to fetch system map");
}
