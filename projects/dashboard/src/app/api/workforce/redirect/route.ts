import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function POST(request: NextRequest) {
  const body = await request.json();
  return proxyAgentJson(
    "/v1/workplan/redirect",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ direction: body.direction ?? "" }),
    },
    "Failed to redirect work plan",
    15_000
  );
}
