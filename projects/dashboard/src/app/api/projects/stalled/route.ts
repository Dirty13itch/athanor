import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/projects/stalled", undefined, "Failed to fetch stalled projects");
}
