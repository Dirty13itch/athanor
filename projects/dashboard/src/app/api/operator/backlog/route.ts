import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const params = new URLSearchParams(request.nextUrl.searchParams);
  const query = params.toString();
  return proxyAgentJson(`/v1/operator/backlog${query ? `?${query}` : ""}`, undefined, "Failed to fetch operator backlog");
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  return proxyAgentOperatorJson(request, "/v1/operator/backlog", "Failed to create operator backlog item", {
    privilegeClass: "operator",
    defaultReason: "Created operator backlog item from dashboard",
    bodyOverride: {
      title: (body as { title?: unknown }).title ?? "",
      prompt: (body as { prompt?: unknown }).prompt ?? "",
      owner_agent: (body as { owner_agent?: unknown }).owner_agent ?? "",
      support_agents: (body as { support_agents?: unknown }).support_agents ?? [],
      scope_type: (body as { scope_type?: unknown }).scope_type ?? "global",
      scope_id: (body as { scope_id?: unknown }).scope_id ?? "athanor",
      work_class: (body as { work_class?: unknown }).work_class ?? "project_build",
      priority: (body as { priority?: unknown }).priority ?? 3,
      approval_mode: (body as { approval_mode?: unknown }).approval_mode ?? "none",
      dispatch_policy: (body as { dispatch_policy?: unknown }).dispatch_policy ?? "planner_eligible",
      preconditions: (body as { preconditions?: unknown }).preconditions ?? [],
      linked_goal_ids: (body as { linked_goal_ids?: unknown }).linked_goal_ids ?? [],
      linked_todo_ids: (body as { linked_todo_ids?: unknown }).linked_todo_ids ?? [],
      linked_idea_id: (body as { linked_idea_id?: unknown }).linked_idea_id ?? "",
      metadata: (body as { metadata?: unknown }).metadata ?? {},
      reason: (body as { reason?: unknown }).reason ?? "Created operator backlog item from dashboard",
    },
  });
}
