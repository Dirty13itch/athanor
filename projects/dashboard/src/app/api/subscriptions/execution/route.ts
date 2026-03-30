import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { requireOperatorMutationAccess } from "@/lib/operator-auth";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.toString();
  const path = query ? `/v1/subscriptions/execution?${query}` : "/v1/subscriptions/execution";
  return proxyAgentJson(path, undefined, "Failed to fetch subscription execution snapshot");
}

export async function POST(request: NextRequest) {
  const gate = requireOperatorMutationAccess(request);
  if (gate) {
    return gate;
  }

  return proxyAgentOperatorJson(request, "/v1/subscriptions/execution", "Failed to execute provider request", {
    privilegeClass: "admin",
    defaultActor: "dashboard-operator",
    defaultReason: "Executed provider request",
    timeoutMs: 120_000,
  });
}
