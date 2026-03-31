import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/digests/latest", undefined, "Failed to fetch latest digest");
}
