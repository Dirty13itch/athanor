import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function POST(request: NextRequest) {
  return proxyAgentOperatorJson(
    request,
    "/v1/governor/presence",
    "Failed to update operator presence",
    {
      privilegeClass: "admin",
      defaultReason: "Manual operator presence update from dashboard",
    }
  );
}
