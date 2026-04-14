import { NextRequest, NextResponse } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

function buildDegradedHeartbeatResponse(detail: string) {
  return NextResponse.json(
    {
      status: "degraded",
      source: "dashboard_heartbeat",
      detail,
    },
    { status: 200 },
  );
}

async function handleHeartbeatPost(request: NextRequest) {
  try {
    const response = await proxyAgentOperatorJson(
      request,
      "/v1/governor/heartbeat",
      "Failed to update operator heartbeat",
      {
        privilegeClass: "operator",
        defaultActor: "dashboard-heartbeat",
        defaultReason: "Dashboard heartbeat acknowledgement",
      },
    );

    if (response.status >= 500) {
      return buildDegradedHeartbeatResponse("Governor heartbeat upstream is temporarily unavailable.");
    }

    return response;
  } catch {
    return buildDegradedHeartbeatResponse("Governor heartbeat route failed soft while proxying the signal.");
  }
}

export async function POST(request: NextRequest) {
  return handleHeartbeatPost(request);
}

export async function GET() {
  return buildDegradedHeartbeatResponse("Heartbeat endpoint is write-only; POST records operator presence.");
}

export async function HEAD() {
  return new NextResponse(null, { status: 200 });
}
