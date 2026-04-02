import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/bootstrap/programs", undefined, "Failed to fetch bootstrap programs");
}
