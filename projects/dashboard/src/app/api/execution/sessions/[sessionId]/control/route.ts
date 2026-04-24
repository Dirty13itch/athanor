import { executionSessionControlRequestSchema } from "@/lib/contracts";
import { controlBuilderSessionWithExecutionBridge } from "@/lib/builder-session-control";
import { loadExecutionSession } from "@/lib/executive-kernel";
import { readBuilderSession } from "@/lib/builder-store";
import { requireOperatorMutationAccess } from "@/lib/operator-auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type BootstrapSliceRecord = {
  id: string;
  program_id?: string;
  metadata?: Record<string, unknown> | null;
  blocking_packet_id?: string;
};

type BootstrapSlicesPayload = {
  slices?: BootstrapSliceRecord[];
};

function forwardedHeaders(request: Request) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  for (const name of ["cookie", "origin", "referer", "x-forwarded-proto", "x-forwarded-host"]) {
    const value = request.headers.get(name);
    if (value) {
      headers[name] = value;
    }
  }

  return headers;
}

async function fetchDashboardJson<T>(request: Request, path: string): Promise<T | null> {
  try {
    const response = await fetch(new URL(path, request.url).toString(), {
      headers: forwardedHeaders(request),
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

async function postDashboardJson(
  request: Request,
  path: string,
  body: Record<string, unknown>,
): Promise<Response> {
  return fetch(new URL(path, request.url).toString(), {
    method: "POST",
    headers: forwardedHeaders(request),
    body: JSON.stringify(body),
    cache: "no-store",
    signal: AbortSignal.timeout(60_000),
  });
}

function blockingPacketIdForSlice(slice: BootstrapSliceRecord) {
  const direct = typeof slice.blocking_packet_id === "string" ? slice.blocking_packet_id.trim() : "";
  if (direct) {
    return direct;
  }
  const fromMetadata =
    slice.metadata && typeof slice.metadata["blocking_packet_id"] === "string"
      ? String(slice.metadata["blocking_packet_id"]).trim()
      : "";
  return fromMetadata;
}

async function approveBootstrapExecutionSession(request: Request, sessionId: string) {
  const slicesPayload = await fetchDashboardJson<BootstrapSlicesPayload>(
    request,
    "/api/bootstrap/slices?limit=500",
  );
  const slice = (slicesPayload?.slices ?? []).find((item) => item.id === sessionId);
  if (!slice) {
    return Response.json({ error: "Execution session not found" }, { status: 404 });
  }

  const programId = typeof slice.program_id === "string" ? slice.program_id.trim() : "";
  const packetId = blockingPacketIdForSlice(slice);
  if (!programId || !packetId) {
    return Response.json(
      { error: "Bootstrap execution session is not waiting on an approval packet" },
      { status: 409 },
    );
  }

  return postDashboardJson(
    request,
    `/api/bootstrap/programs/${encodeURIComponent(programId)}/approve`,
    {
      packet_id: packetId,
      reason: `Approved bootstrap packet ${packetId} from generic execution control`,
    },
  );
}

export async function POST(
  request: Request,
  context: { params: Promise<{ sessionId: string }> },
) {
  const gate = requireOperatorMutationAccess(request);
  if (gate) {
    return gate;
  }

  try {
    const { sessionId } = await context.params;
    const body = await request.json().catch(() => ({}));
    const parsed = executionSessionControlRequestSchema.safeParse(body);
    if (!parsed.success) {
      return Response.json(
        { error: "Invalid execution session control payload", issues: parsed.error.flatten() },
        { status: 400 },
      );
    }

    const [builderSession, projectedSession] = await Promise.all([
      readBuilderSession(sessionId),
      loadExecutionSession(sessionId),
    ]);
    if (!builderSession) {
      if (projectedSession) {
        if (projectedSession.family === "bootstrap_takeover" && parsed.data.action === "approve") {
          const response = await approveBootstrapExecutionSession(request, sessionId);
          if (!response.ok) {
            const payload = await response.json().catch(() => ({ error: "Failed to approve bootstrap session" }));
            return Response.json(payload, { status: response.status });
          }

          const refreshed = await loadExecutionSession(sessionId);
          return Response.json({
            ok: true,
            session: refreshed ?? projectedSession,
            terminal_href: null,
          });
        }

        return Response.json(
          { error: `Execution control is not yet available for ${projectedSession.family} sessions` },
          { status: 409 },
        );
      }
      return Response.json({ error: "Execution session not found" }, { status: 404 });
    }

    const result = await controlBuilderSessionWithExecutionBridge(
      sessionId,
      parsed.data.action,
      parsed.data.approval_id ?? null,
    );
    const projected = await loadExecutionSession(sessionId);

    return Response.json({
      ok: true,
      session: projected ?? null,
      terminal_href: result.terminal_href,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to update execution session";
    const status = message.includes("not found") || message.includes("Unknown builder session") ? 404 : 500;
    return Response.json({ error: message }, { status });
  }
}
