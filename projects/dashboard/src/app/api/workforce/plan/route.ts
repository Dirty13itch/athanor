import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/workplan", undefined, "Failed to fetch current work plan");
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  return proxyAgentJson(
    "/v1/workplan/generate",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ focus: body.focus ?? "" }),
    },
    "Failed to generate work plan",
    120_000
  );
}
