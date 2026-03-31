import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function POST(request: NextRequest) {
  return proxyAgentOperatorJson(
    request,
    "/v1/governor/pause",
    "Failed to pause automation",
    {
      privilegeClass: "admin",
      defaultReason: "Manual governor pause from dashboard",
    }
  );
}
