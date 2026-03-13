import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson(
    "/v1/models/governance",
    undefined,
    "Failed to fetch model governance snapshot"
  );
}
