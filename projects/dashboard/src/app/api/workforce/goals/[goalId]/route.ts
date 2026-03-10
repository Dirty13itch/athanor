import { NextRequest, NextResponse } from "next/server";
import { config, joinUrl } from "@/lib/config";

export async function DELETE(
  _request: NextRequest,
  context: { params: Promise<{ goalId: string }> }
) {
  try {
    const { goalId } = await context.params;
    const response = await fetch(joinUrl(config.agentServer.url, `/v1/goals/${goalId}`), {
      method: "DELETE",
      signal: AbortSignal.timeout(10_000),
    });

    if (!response.ok) {
      return NextResponse.json({ error: `Upstream returned ${response.status}` }, { status: response.status });
    }

    const text = await response.text();
    return NextResponse.json(text ? JSON.parse(text) : { ok: true });
  } catch {
    return NextResponse.json({ error: "Failed to delete goal" }, { status: 502 });
  }
}
