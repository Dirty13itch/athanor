import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function POST(request: NextRequest) {
  return proxyAgentOperatorJson(
    request,
    "/v1/governor/heartbeat",
    "Failed to update operator heartbeat",
    {
      privilegeClass: "operator",
      defaultActor: "dashboard-heartbeat",
      defaultReason: "Dashboard heartbeat acknowledgement",
    },
  );
}
