import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const params = new URLSearchParams(request.nextUrl.searchParams);
  const query = params.toString();
  return proxyAgentJson(`/v1/tasks${query ? `?${query}` : ""}`, undefined, "Failed to fetch tasks");
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  return proxyAgentJson(
    "/v1/tasks",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        agent: body.agent ?? "general-assistant",
        prompt: body.prompt ?? "",
        priority: body.priority ?? "normal",
        metadata: body.metadata ?? {},
      }),
    },
    "Failed to submit task",
    15_000
  );
}
