import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

// Generic proxy to the agent server — avoids CORS for client components
// Usage: /api/agents/proxy?path=/v1/tasks&limit=20
export async function GET(request: NextRequest) {
  const path = request.nextUrl.searchParams.get("path");
  if (!path) {
    return NextResponse.json({ error: "Missing path parameter" }, { status: 400 });
  }

  // Only allow /v1/ paths to prevent open redirect
  if (!path.startsWith("/v1/") && !path.startsWith("/health")) {
    return NextResponse.json({ error: "Invalid path" }, { status: 403 });
  }

  // Forward remaining query params
  const params = new URLSearchParams();
  for (const [key, value] of request.nextUrl.searchParams.entries()) {
    if (key !== "path") params.set(key, value);
  }
  const qs = params.toString();
  const url = `${config.agentServer.url}${path}${qs ? `?${qs}` : ""}`;

  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(8000) });
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
