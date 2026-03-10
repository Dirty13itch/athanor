import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

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
    15_000
  );
}
