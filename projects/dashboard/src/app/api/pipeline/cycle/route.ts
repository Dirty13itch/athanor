import { proxyAgentJson } from "@/lib/server-agent";

export async function POST() {
  return proxyAgentJson(
    "/v1/pipeline/cycle",
    { method: "POST" },
    "Failed to trigger pipeline cycle",
    30_000
  );
}
