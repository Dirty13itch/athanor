import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/outputs", undefined, "Failed to fetch outputs");
}
