import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson(
    "/v1/notifications?include_resolved=true",
    undefined,
    "Failed to fetch workforce notifications"
  );
}
