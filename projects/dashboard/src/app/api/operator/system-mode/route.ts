import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function GET() {
  return proxyAgentJson("/v1/operator/system-mode", undefined, "Failed to fetch operator system mode");
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  return proxyAgentOperatorJson(request, "/v1/operator/system-mode", "Failed to update operator system mode", {
    privilegeClass: "admin",
    defaultReason: "Updated operator system mode from dashboard",
    bodyOverride: {
      mode: (body as { mode?: unknown }).mode ?? "",
      trigger: (body as { trigger?: unknown }).trigger ?? "",
      exit_conditions: (body as { exit_conditions?: unknown }).exit_conditions ?? "",
      notes: (body as { notes?: unknown }).notes ?? "",
      metadata: (body as { metadata?: unknown }).metadata ?? {},
      reason: (body as { reason?: unknown }).reason ?? "Updated operator system mode from dashboard",
    },
  });
}
