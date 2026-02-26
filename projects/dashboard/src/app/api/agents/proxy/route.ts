import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

function buildUpstreamUrl(request: NextRequest): { url: string; error?: never } | { url?: never; error: NextResponse } {
  const path = request.nextUrl.searchParams.get("path");
  if (!path) {
    return { error: NextResponse.json({ error: "Missing path parameter" }, { status: 400 }) };
  }

  // Only allow /v1/ paths to prevent open redirect
  if (!path.startsWith("/v1/") && !path.startsWith("/health")) {
    return { error: NextResponse.json({ error: "Invalid path" }, { status: 403 }) };
  }

  // Forward remaining query params
  const params = new URLSearchParams();
  for (const [key, value] of request.nextUrl.searchParams.entries()) {
    if (key !== "path") params.set(key, value);
  }
  const qs = params.toString();
  return { url: `${config.agentServer.url}${path}${qs ? `?${qs}` : ""}` };
}

// Generic proxy to the agent server — avoids CORS for client components
// Usage: /api/agents/proxy?path=/v1/tasks&limit=20
export async function GET(request: NextRequest) {
  const result = buildUpstreamUrl(request);
  if (result.error) return result.error;

  try {
    const res = await fetch(result.url, { signal: AbortSignal.timeout(8000) });
    if (!res.ok) {
      return NextResponse.json(
        { error: `Upstream returned ${res.status}` },
        { status: res.status }
      );
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: "Agent server unreachable" }, { status: 502 });
  }
}

export async function POST(request: NextRequest) {
  const result = buildUpstreamUrl(request);
  if (result.error) return result.error;

  try {
    const body = await request.text();
    const res = await fetch(result.url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) {
      return NextResponse.json(
        { error: `Upstream returned ${res.status}` },
        { status: res.status }
      );
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: "Agent server unreachable" }, { status: 502 });
  }
}
