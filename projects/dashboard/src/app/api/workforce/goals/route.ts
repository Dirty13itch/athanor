import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function POST(request: NextRequest) {
  const body = await request.json();
  return proxyAgentJson(
    "/v1/goals",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: body.text ?? "",
        agent: body.agent ?? "global",
        priority: body.priority ?? "normal",
      }),
    },
    "Failed to create goal"
  );
}
