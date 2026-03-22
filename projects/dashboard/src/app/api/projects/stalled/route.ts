import { proxyAgentJson } from "@/lib/server-agent";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    return await proxyAgentJson("/v1/projects/stalled", undefined, "Failed to fetch stalled projects");
  } catch {
    return NextResponse.json({ projects: [], message: "Stalled detection not yet implemented" }, { status: 200 });
  }
}
