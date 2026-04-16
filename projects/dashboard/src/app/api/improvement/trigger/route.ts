import { NextRequest } from "next/server";
import { requireOperatorMutationAccess } from "@/lib/operator-auth";
import { proxyAgentJson } from "@/lib/server-agent";

export async function POST(request: NextRequest) {
  const gate = requireOperatorMutationAccess(request);
  if (gate) {
    return gate;
  }

  return proxyAgentJson("/v1/improvement/trigger", { method: "POST" }, "Failed to trigger improvement cycle", 30_000);
}
