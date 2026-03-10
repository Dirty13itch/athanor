import { NextRequest, NextResponse } from "next/server";
import { config, joinUrl } from "@/lib/config";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ itemId: string }> }
) {
  try {
    const { itemId } = await context.params;
    const body = await request.json();
    const response = await fetch(joinUrl(config.agentServer.url, `/v1/workspace/${itemId}/endorse`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent_name: body.agentName ?? "" }),
      signal: AbortSignal.timeout(10_000),
    });

    if (!response.ok) {
      return NextResponse.json({ error: `Upstream returned ${response.status}` }, { status: response.status });
    }

    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ error: "Failed to endorse workspace item" }, { status: 502 });
  }
}
