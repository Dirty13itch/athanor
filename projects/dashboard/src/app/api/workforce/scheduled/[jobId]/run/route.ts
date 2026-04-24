import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await context.params;
  return proxyAgentOperatorJson(
    request,
    `/v1/tasks/scheduled/${encodeURIComponent(jobId)}/run`,
    "Failed to run scheduled job",
    {
      privilegeClass: "admin",
      defaultReason: `Triggered scheduled job ${jobId} from dashboard`,
    }
  );
}
