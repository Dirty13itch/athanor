import { NextRequest, NextResponse } from "next/server";
import { config, joinUrl } from "@/lib/config";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const response = await fetch(joinUrl(config.agentServer.url, "/v1/workplan/redirect"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ direction: body.direction ?? "" }),
      signal: AbortSignal.timeout(15_000),
    });

    if (!response.ok) {
      return NextResponse.json({ error: `Upstream returned ${response.status}` }, { status: response.status });
    }

    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ error: "Failed to redirect work plan" }, { status: 502 });
  }
}
