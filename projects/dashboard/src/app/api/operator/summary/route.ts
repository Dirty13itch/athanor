import { NextResponse } from "next/server";
import { readSteadyStateFrontDoor } from "@/lib/operator-frontdoor";
import { proxyAgentJson } from "@/lib/server-agent";

const TASKS_FALLBACK = {
  pending_approval: 0,
  failed_actionable: 0,
  stale_lease: 0,
  failed_historical_repaired: 0,
};

export async function GET() {
  const [response, steadyState] = await Promise.all([
    proxyAgentJson("/v1/operator/summary", undefined, "Failed to fetch operator work summary", 25_000),
    readSteadyStateFrontDoor(),
  ]);

  const payload = (await response.json()) as Record<string, unknown>;
  if (response.status >= 500) {
    return NextResponse.json(
      {
        available: false,
        degraded: true,
        source: "agent-server",
        detail: "Failed to fetch operator work summary",
        tasks: TASKS_FALLBACK,
        steadyState,
      },
      { status: 200 },
    );
  }

  return NextResponse.json(
    {
      ...payload,
      source: typeof payload.source === "string" ? payload.source : "agent-server",
      steadyState,
    },
    { status: response.status },
  );
}
