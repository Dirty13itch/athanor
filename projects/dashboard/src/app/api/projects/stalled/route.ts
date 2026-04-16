import { proxyAgentJson } from "@/lib/server-agent";
import { NextResponse } from "next/server";

export async function GET() {
  const response = await proxyAgentJson(
    "/v1/projects/stalled",
    undefined,
    "Failed to fetch stalled projects"
  );
  if (response.status === 401 || response.status === 403) {
    return NextResponse.json({ stalled: [], projects: [], count: 0 }, { status: 200 });
  }
  const payload = (await response.json().catch(() => null)) as
    | { stalled?: unknown[]; projects?: unknown[]; count?: number }
    | null;
  const stalled = Array.isArray(payload?.stalled)
    ? payload.stalled
    : Array.isArray(payload?.projects)
      ? payload.projects
      : [];
  return NextResponse.json({ stalled, projects: stalled, count: stalled.length }, { status: 200 });
}
