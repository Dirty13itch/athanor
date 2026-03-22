import { proxyAgentJson } from "@/lib/server-agent";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    return await proxyAgentJson("/v1/pipeline/plans", undefined, "Failed to fetch plans");
  } catch {
    return NextResponse.json({ plans: [], message: "Pipeline plans not yet implemented" }, { status: 200 });
  }
}
