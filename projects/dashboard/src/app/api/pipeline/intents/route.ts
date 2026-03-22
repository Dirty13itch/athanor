import { proxyAgentJson } from "@/lib/server-agent";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    return await proxyAgentJson("/v1/pipeline/intents", undefined, "Failed to fetch intents");
  } catch {
    return NextResponse.json({ intents: [], message: "Pipeline intents not yet implemented" }, { status: 200 });
  }
}
