import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/workplan", undefined, "Failed to fetch current work plan");
}

export async function POST(request: NextRequest) {
  return proxyAgentOperatorJson(request, "/v1/workplan/generate", "Failed to generate work plan", {
    privilegeClass: "admin",
    defaultActor: "dashboard-operator",
    defaultReason: "Generated work plan",
    timeoutMs: 120_000,
  });
}
