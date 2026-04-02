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
    `/v1/operator/inbox/${encodeURIComponent(inboxId)}/resolve`,
    "Failed to resolve inbox item",
    {
      privilegeClass: "operator",
      defaultReason: `Resolved inbox item ${inboxId} from dashboard`,
      bodyOverride: {
        note: (body as { note?: unknown }).note ?? "",
        reason: (body as { reason?: unknown }).reason ?? `Resolved inbox item ${inboxId} from dashboard`,
      },
    }
  );
}
