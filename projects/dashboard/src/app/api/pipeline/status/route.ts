import { proxyAgentJson } from "@/lib/server-agent";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    return await proxyAgentJson("/v1/pipeline/status", undefined, "Failed to fetch pipeline status");
  } catch {
    return NextResponse.json({ status: "unavailable", message: "Pipeline status not yet implemented in Agent Server" }, { status: 200 });
  }
}
