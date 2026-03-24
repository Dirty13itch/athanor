import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/pipeline/intents", undefined, "Failed to fetch pipeline intents");
}
