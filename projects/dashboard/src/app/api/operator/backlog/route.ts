import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { proxyOperatorReadJson } from "@/app/api/operator/fail-soft";

export async function GET(request: NextRequest) {
  const params = new URLSearchParams(request.nextUrl.searchParams);
  const status = params.get("status")?.trim().toLowerCase() ?? "";
  if (status === "all") {
    params.delete("status");
  }
  const query = params.toString();
  return proxyOperatorReadJson(
    `/v1/operator/backlog${query ? `?${query}` : ""}`,
    "Failed to fetch operator backlog",
    {
      backlog: [],
      count: 0,
    },
  );
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
      family: (body as { family?: unknown }).family ?? "",
      project_id: (body as { project_id?: unknown }).project_id ?? "",
      source_type: (body as { source_type?: unknown }).source_type ?? "",
      source_ref: (body as { source_ref?: unknown }).source_ref ?? "",
      routing_class: (body as { routing_class?: unknown }).routing_class ?? "",
      verification_contract: (body as { verification_contract?: unknown }).verification_contract ?? "",
      closure_rule: (body as { closure_rule?: unknown }).closure_rule ?? "",
      materialization_source: (body as { materialization_source?: unknown }).materialization_source ?? "",
      materialization_reason: (body as { materialization_reason?: unknown }).materialization_reason ?? "",
      recurrence_program_id: (body as { recurrence_program_id?: unknown }).recurrence_program_id ?? "",
      result_id: (body as { result_id?: unknown }).result_id ?? "",
      review_id: (body as { review_id?: unknown }).review_id ?? "",
      metadata: (body as { metadata?: unknown }).metadata ?? {},
      reason: (body as { reason?: unknown }).reason ?? "Created operator backlog item from dashboard",
    },
  });
}
