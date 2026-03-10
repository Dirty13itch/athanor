import { proxyAgentJson } from "@/lib/server-agent";

export async function POST() {
  return proxyAgentJson("/v1/patterns/run", { method: "POST" }, "Failed to trigger insights run");
}
