import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ taskId: string }> }
) {
  const { taskId } = await context.params;
  return proxyAgentOperatorJson(
    request,
    `/v1/tasks/${taskId}/cancel`,
    "Failed to cancel task",
    {
      privilegeClass: "admin",
      defaultReason: `Cancelled task ${taskId} from dashboard`,
    }
  );
}
