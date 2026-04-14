import { NextResponse } from "next/server";
import { agentServerHeaders, config, joinUrl } from "@/lib/config";
import { pickMasterAtlasSummary, readGeneratedMasterAtlas } from "@/lib/master-atlas";

export async function GET() {
  try {
    const response = await fetch(joinUrl(config.agentServer.url, "/v1/governor/operations"), {
      headers: agentServerHeaders(),
      signal: AbortSignal.timeout(10_000),
    });

    if (!response.ok) {
      return NextResponse.json({ error: `Upstream returned ${response.status}` }, { status: response.status });
    }

    const text = await response.text();
    const payload = text ? (JSON.parse(text) as Record<string, unknown>) : { ok: true };
    const atlasSummary = pickMasterAtlasSummary(await readGeneratedMasterAtlas());
    return NextResponse.json({
      ...payload,
      master_atlas: atlasSummary,
    });
  } catch {
    return NextResponse.json({ error: "Failed to fetch operations-readiness snapshot" }, { status: 502 });
  }
}
