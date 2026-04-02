import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ inboxId: string }> }
) {
  const { inboxId } = await params;
  const body = await request.json().catch(() => ({}));
  return proxyAgentOperatorJson(
    request,
    `/v1/operator/inbox/${encodeURIComponent(inboxId)}/snooze`,
    "Failed to snooze inbox item",
    {
      privilegeClass: "operator",
      defaultReason: `Snoozed inbox item ${inboxId} from dashboard`,
      bodyOverride: {
        until: (body as { until?: unknown }).until ?? null,
        reason: (body as { reason?: unknown }).reason ?? `Snoozed inbox item ${inboxId} from dashboard`,
      },
    }
  );
}
