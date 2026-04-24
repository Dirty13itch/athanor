import { NextRequest, NextResponse } from "next/server";
import { applyBuilderSyntheticInboxAction, isBuilderSyntheticInboxId } from "@/lib/builder-store";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ inboxId: string }> }
) {
  const { inboxId } = await params;
  const body = await request.json().catch(() => ({}));
  if (isBuilderSyntheticInboxId(inboxId)) {
    const item = await applyBuilderSyntheticInboxAction(inboxId, "convert", {
      category: (body as { category?: unknown }).category,
      priority: (body as { priority?: unknown }).priority,
      energy_class: (body as { energy_class?: unknown }).energy_class,
    });
    return NextResponse.json({ ok: true, item });
  }
  return proxyAgentOperatorJson(
    request,
    `/v1/operator/inbox/${encodeURIComponent(inboxId)}/convert`,
    "Failed to convert inbox item",
    {
      privilegeClass: "operator",
      defaultReason: `Converted inbox item ${inboxId} to todo from dashboard`,
      bodyOverride: {
        category: (body as { category?: unknown }).category ?? "decision",
        priority: (body as { priority?: unknown }).priority ?? 3,
        energy_class: (body as { energy_class?: unknown }).energy_class ?? "quick",
        reason:
          (body as { reason?: unknown }).reason ??
          `Converted inbox item ${inboxId} to todo from dashboard`,
      },
    }
  );
}
