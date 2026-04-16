import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson(
    "/v1/governor/operator-tests",
    undefined,
    "Failed to fetch operator-test snapshot"
  );
}

export async function POST(request: NextRequest) {
  return proxyAgentOperatorJson(
    request,
    "/v1/governor/operator-tests/run",
    "Failed to run synthetic operator tests",
    {
      privilegeClass: "admin",
      defaultReason: "Manual operator test run from dashboard",
    }
  );
}
