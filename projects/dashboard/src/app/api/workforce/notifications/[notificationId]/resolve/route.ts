import { NextRequest, NextResponse } from "next/server";
import { config, joinUrl } from "@/lib/config";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ notificationId: string }> }
) {
  try {
    const { notificationId } = await context.params;
    const body = await request.json();
    const response = await fetch(
      joinUrl(config.agentServer.url, `/v1/notifications/${notificationId}/resolve`),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved: Boolean(body.approved) }),
        signal: AbortSignal.timeout(10_000),
      }
    );

    if (!response.ok) {
      return NextResponse.json({ error: `Upstream returned ${response.status}` }, { status: response.status });
    }

    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ error: "Failed to resolve notification" }, { status: 502 });
  }
}
