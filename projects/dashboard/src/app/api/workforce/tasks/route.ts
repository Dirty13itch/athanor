import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const params = new URLSearchParams(request.nextUrl.searchParams);
  const query = params.toString();
  return proxyAgentJson(`/v1/tasks${query ? `?${query}` : ""}`, undefined, "Failed to fetch tasks");
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  return proxyAgentOperatorJson(
    request,
    "/v1/tasks",
    "Failed to submit task",
    {
      privilegeClass: "operator",
      defaultReason: "Manual task submission from dashboard",
      bodyOverride: {
        agent: (body as { agent?: unknown }).agent ?? "general-assistant",
        prompt: (body as { prompt?: unknown }).prompt ?? "",
        priority: (body as { priority?: unknown }).priority ?? "normal",
        metadata: (body as { metadata?: unknown }).metadata ?? {},
        reason: (body as { reason?: unknown }).reason ?? "Manual task submission from dashboard",
      },
      timeoutMs: 15_000,
    }
  );
}
