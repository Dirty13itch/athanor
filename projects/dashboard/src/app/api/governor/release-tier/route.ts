import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function POST(request: NextRequest) {
  return proxyAgentOperatorJson(
    request,
    "/v1/governor/release-tier",
    "Failed to update release tier",
    {
      privilegeClass: "admin",
      defaultReason: "Manual release-tier change from dashboard",
    }
  );
}
