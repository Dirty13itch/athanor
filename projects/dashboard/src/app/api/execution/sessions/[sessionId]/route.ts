import { loadExecutionSession } from "@/lib/executive-kernel";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ sessionId: string }> },
) {
  const { sessionId } = await context.params;
  const session = await loadExecutionSession(sessionId);
  if (!session) {
    return Response.json({ error: "Execution session not found" }, { status: 404 });
  }

  return Response.json(session);
}
