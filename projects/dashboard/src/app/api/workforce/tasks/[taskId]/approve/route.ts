import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ taskId: string }> }
) {
  const { taskId } = await context.params;
  return proxyAgentOperatorJson(
    request,
    `/v1/tasks/${taskId}/approve`,
    "Failed to approve task",
    {
      privilegeClass: "admin",
      defaultReason: `Approved pending task ${taskId} from dashboard`,
    }
  );
}
