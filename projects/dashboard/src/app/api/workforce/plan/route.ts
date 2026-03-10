import { NextRequest, NextResponse } from "next/server";
import { config, joinUrl } from "@/lib/config";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const response = await fetch(joinUrl(config.agentServer.url, "/v1/workplan/generate"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ focus: body.focus ?? "" }),
      signal: AbortSignal.timeout(15_000),
    });

    if (!response.ok) {
      return NextResponse.json({ error: `Upstream returned ${response.status}` }, { status: response.status });
    }

    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ error: "Failed to generate work plan" }, { status: 502 });
  }
}
