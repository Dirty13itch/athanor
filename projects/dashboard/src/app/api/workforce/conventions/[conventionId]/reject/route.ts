import { NextRequest, NextResponse } from "next/server";
import { config, joinUrl } from "@/lib/config";

export async function POST(
  _request: NextRequest,
  context: { params: Promise<{ conventionId: string }> }
) {
  try {
    const { conventionId } = await context.params;
    const response = await fetch(joinUrl(config.agentServer.url, `/v1/conventions/${conventionId}/reject`), {
      method: "POST",
      signal: AbortSignal.timeout(10_000),
    });

    if (!response.ok) {
      return NextResponse.json({ error: `Upstream returned ${response.status}` }, { status: response.status });
    }

    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ error: "Failed to reject convention" }, { status: 502 });
  }
}
