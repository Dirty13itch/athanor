import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/goals", {}, "Failed to fetch goals");
}

export async function POST(request: NextRequest) {
  return proxyAgentOperatorJson(request, "/v1/goals", "Failed to create goal", {
    privilegeClass: "operator",
    defaultActor: "dashboard-operator",
    defaultReason: "Created steering goal",
  });
}
