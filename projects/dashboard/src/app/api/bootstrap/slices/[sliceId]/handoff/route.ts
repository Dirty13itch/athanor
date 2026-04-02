import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function POST(request: NextRequest, context: { params: Promise<{ sliceId: string }> }) {
  const { sliceId } = await context.params;
  const body = await request.json().catch(() => ({}));
  return proxyAgentOperatorJson(request, `/v1/bootstrap/slices/${encodeURIComponent(sliceId)}/handoff`, "Failed to hand off bootstrap slice", {
    privilegeClass: "admin",
    defaultReason: "Handed off bootstrap slice from dashboard",
    bodyOverride: {
      from_host: (body as { from_host?: unknown }).from_host ?? "",
      to_host: (body as { to_host?: unknown }).to_host ?? "",
      current_ref: (body as { current_ref?: unknown }).current_ref ?? "",
      worktree_path: (body as { worktree_path?: unknown }).worktree_path ?? "",
      files_touched: (body as { files_touched?: unknown }).files_touched ?? [],
      validation_status: (body as { validation_status?: unknown }).validation_status ?? "pending",
      open_risks: (body as { open_risks?: unknown }).open_risks ?? [],
      next_step: (body as { next_step?: unknown }).next_step ?? "",
      stop_reason: (body as { stop_reason?: unknown }).stop_reason ?? "",
      resume_instructions: (body as { resume_instructions?: unknown }).resume_instructions ?? "",
      cooldown_minutes: (body as { cooldown_minutes?: unknown }).cooldown_minutes ?? 30,
      blocker_class: (body as { blocker_class?: unknown }).blocker_class ?? "",
      approval_required: (body as { approval_required?: unknown }).approval_required ?? false,
      reason: (body as { reason?: unknown }).reason ?? "Handed off bootstrap slice from dashboard",
    },
  });
}
