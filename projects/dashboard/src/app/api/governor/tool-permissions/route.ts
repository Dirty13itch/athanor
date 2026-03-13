import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson(
    "/v1/governor/tool-permissions",
    undefined,
    "Failed to fetch tool-permission snapshot"
  );
}
