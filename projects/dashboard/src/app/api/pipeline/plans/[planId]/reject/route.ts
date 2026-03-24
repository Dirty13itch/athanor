import { proxyAgentJson } from "@/lib/server-agent";

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ planId: string }> }
) {
  const { planId } = await params;
  return proxyAgentJson(
    `/v1/plans/${planId}/reject`,
    { method: "POST" },
    "Failed to reject plan"
  );
}
