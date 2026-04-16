import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function POST(request: NextRequest) {
  return proxyAgentOperatorJson(
    request,
    "/v1/governor/resume",
    "Failed to resume automation",
    {
      privilegeClass: "admin",
      defaultReason: "Manual governor resume from dashboard",
    }
  );
}
