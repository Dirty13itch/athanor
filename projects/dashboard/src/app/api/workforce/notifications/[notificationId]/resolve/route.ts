import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ notificationId: string }> }
) {
  const { notificationId } = await context.params;
  const body = await request.json();
  return proxyAgentJson(
    `/v1/notifications/${notificationId}/resolve`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approved: Boolean(body.approved) }),
    },
    "Failed to resolve notification"
  );
}
