import { proxyAgentJson } from "@/lib/server-agent";

export async function POST() {
  return proxyAgentJson("/v1/consolidate", { method: "POST" }, "Failed to run consolidation");
}
