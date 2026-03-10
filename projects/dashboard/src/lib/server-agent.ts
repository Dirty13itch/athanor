import { NextResponse } from "next/server";
import { config, joinUrl } from "@/lib/config";

export async function proxyAgentJson(
  path: string,
  init: RequestInit | undefined,
  errorMessage: string,
  timeoutMs = 10_000
) {
  try {
    const response = await fetch(joinUrl(config.agentServer.url, path), {
      ...init,
      signal: init?.signal ?? AbortSignal.timeout(timeoutMs),
    });

    if (!response.ok) {
      return NextResponse.json({ error: `Upstream returned ${response.status}` }, { status: response.status });
    }

    const text = await response.text();
    return NextResponse.json(text ? JSON.parse(text) : { ok: true });
  } catch {
    return NextResponse.json({ error: errorMessage }, { status: 502 });
  }
}
