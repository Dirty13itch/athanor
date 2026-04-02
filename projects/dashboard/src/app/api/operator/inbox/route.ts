import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const params = new URLSearchParams(request.nextUrl.searchParams);
  const query = params.toString();
  return proxyAgentJson(`/v1/operator/inbox${query ? `?${query}` : ""}`, undefined, "Failed to fetch operator inbox");
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  return proxyAgentOperatorJson(request, "/v1/operator/inbox", "Failed to create operator inbox item", {
    privilegeClass: "operator",
    defaultReason: "Created operator inbox item from dashboard",
    bodyOverride: {
      kind: (body as { kind?: unknown }).kind ?? "",
      title: (body as { title?: unknown }).title ?? "",
      description: (body as { description?: unknown }).description ?? "",
      severity: (body as { severity?: unknown }).severity ?? 1,
      source: (body as { source?: unknown }).source ?? "dashboard",
      requires_decision: (body as { requires_decision?: unknown }).requires_decision ?? false,
      decision_type: (body as { decision_type?: unknown }).decision_type ?? "",
      related_run_id: (body as { related_run_id?: unknown }).related_run_id ?? "",
      related_task_id: (body as { related_task_id?: unknown }).related_task_id ?? "",
      related_project_id: (body as { related_project_id?: unknown }).related_project_id ?? "",
      related_domain_id: (body as { related_domain_id?: unknown }).related_domain_id ?? "",
      metadata: (body as { metadata?: unknown }).metadata ?? {},
      reason: (body as { reason?: unknown }).reason ?? "Created operator inbox item from dashboard",
    },
  });
}
