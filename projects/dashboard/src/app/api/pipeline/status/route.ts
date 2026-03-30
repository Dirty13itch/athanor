import { proxyAgentJson } from "@/lib/server-agent";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const response = await proxyAgentJson(
      "/v1/pipeline/status",
      undefined,
      "Failed to fetch pipeline status"
    );
    if (response.ok) {
      return response;
    }
  } catch {
    // fall through to the documented compatibility payload
  }

  return NextResponse.json(
    {
      recent_cycles: [],
      pending_plans: [],
      recent_outcomes_count: 0,
      avg_quality: null,
      last_cycle: null,
      status: "unavailable",
      message: "Pipeline status not yet implemented in Agent Server",
    },
    { status: 200 }
  );
}
