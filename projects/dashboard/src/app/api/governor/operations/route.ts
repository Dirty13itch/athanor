import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson(
    "/v1/governor/operations",
    undefined,
    "Failed to fetch operations-readiness snapshot"
  );
}
