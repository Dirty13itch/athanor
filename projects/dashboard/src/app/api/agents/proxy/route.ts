import { NextRequest, NextResponse } from "next/server";
import { agentServerHeaders, config, joinUrl } from "@/lib/config";

export async function GET(request: NextRequest) {
  const path = request.nextUrl.searchParams.get("path");
  if (!path) {
    return NextResponse.json({ error: "Missing path parameter" }, { status: 400 });
  }

  try {
    const url = joinUrl(config.agentServer.url, path);
    const resp = await fetch(url, {
      headers: agentServerHeaders(),
      signal: AbortSignal.timeout(10_000),
    });
    const data = await resp.json();
    return NextResponse.json(data, { status: resp.status });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Agent server request failed";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}

export async function POST(request: NextRequest) {
  const path = request.nextUrl.searchParams.get("path");
  if (!path) {
    return NextResponse.json({ error: "Missing path parameter" }, { status: 400 });
  }

  try {
    const url = joinUrl(config.agentServer.url, path);
    const contentType = request.headers.get("content-type") ?? "";
    const hasBody = contentType.includes("application/json");
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        ...agentServerHeaders(),
        ...(hasBody ? { "Content-Type": "application/json" } : {}),
      },
      body: hasBody ? await request.text() : undefined,
      signal: AbortSignal.timeout(10_000),
    });
    const text = await resp.text();
    const data = text ? JSON.parse(text) : null;
    return NextResponse.json(data, { status: resp.status });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Agent server request failed";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
