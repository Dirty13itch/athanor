import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const params = new URLSearchParams(request.nextUrl.searchParams);
  const query = params.toString();
  return proxyAgentJson(`/v1/operator/todos${query ? `?${query}` : ""}`, undefined, "Failed to fetch operator todos");
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  return proxyAgentOperatorJson(request, "/v1/operator/todos", "Failed to create operator todo", {
    privilegeClass: "operator",
    defaultReason: "Created operator todo from dashboard",
    bodyOverride: {
      title: (body as { title?: unknown }).title ?? "",
      description: (body as { description?: unknown }).description ?? "",
      category: (body as { category?: unknown }).category ?? "ops",
      scope_type: (body as { scope_type?: unknown }).scope_type ?? "global",
      scope_id: (body as { scope_id?: unknown }).scope_id ?? "athanor",
      priority: (body as { priority?: unknown }).priority ?? 3,
      energy_class: (body as { energy_class?: unknown }).energy_class ?? "focused",
      due_at: (body as { due_at?: unknown }).due_at ?? null,
      linked_goal_ids: (body as { linked_goal_ids?: unknown }).linked_goal_ids ?? [],
      linked_inbox_ids: (body as { linked_inbox_ids?: unknown }).linked_inbox_ids ?? [],
      metadata: (body as { metadata?: unknown }).metadata ?? {},
      reason: (body as { reason?: unknown }).reason ?? "Created operator todo from dashboard",
    },
  });
}
