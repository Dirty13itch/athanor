import { proxyAgentJson } from "@/lib/server-agent";

export async function POST() {
  return proxyAgentJson(
    "/v1/improvement/benchmarks/run",
    { method: "POST" },
    "Failed to run benchmarks",
    15_000
  );
}
