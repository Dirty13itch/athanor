import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { requireOperatorMutationAccess } from "@/lib/operator-auth";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.toString();
  const path = query ? `/v1/subscriptions/handoffs?${query}` : "/v1/subscriptions/handoffs";
  return proxyAgentJson(path, undefined, "Failed to fetch subscription handoffs");
}

export async function POST(request: NextRequest) {
  const gate = requireOperatorMutationAccess(request);
  if (gate) {
    return gate;
  }

  return proxyAgentOperatorJson(request, "/v1/subscriptions/handoffs", "Failed to create subscription handoff", {
    privilegeClass: "operator",
    defaultActor: "dashboard-operator",
    defaultReason: "Created provider handoff bundle",
    timeoutMs: 30_000,
  });
}
