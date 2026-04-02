import { NextRequest, NextResponse } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

type Context = {
  params: Promise<{ programId: string }>;
};

type BootstrapProgram = {
  id: string;
  next_action?: Record<string, unknown> | null;
  waiting_on_approval_family?: string;
  waiting_on_approval_slice_id?: string;
};

type BootstrapStatus = {
  approval_context?: { packet_id?: string } | null;
};

type BootstrapProgramsPayload = {
  programs?: BootstrapProgram[];
  status?: BootstrapStatus & Record<string, unknown>;
  takeover?: Record<string, unknown>;
};

type BootstrapSlice = {
  id: string;
  metadata?: {
    approved_packets?: string[];
  } | null;
};

type BootstrapSlicesPayload = {
  slices?: BootstrapSlice[];
};

async function fetchDashboardJson<T>(request: NextRequest, path: string): Promise<T | null> {
  try {
    const response = await fetch(new URL(path, request.url), {
      headers: {
        "Content-Type": "application/json",
        ...(request.headers.get("cookie")
          ? { cookie: request.headers.get("cookie") as string }
          : {}),
        ...(request.headers.get("origin")
          ? { origin: request.headers.get("origin") as string }
          : {}),
        ...(request.headers.get("referer")
          ? { referer: request.headers.get("referer") as string }
          : {}),
        ...(request.headers.get("x-forwarded-proto")
          ? { "x-forwarded-proto": request.headers.get("x-forwarded-proto") as string }
          : {}),
        ...(request.headers.get("x-forwarded-host")
          ? { "x-forwarded-host": request.headers.get("x-forwarded-host") as string }
          : {}),
      },
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

function hasApprovedPacket(slice: BootstrapSlice, packetId: string): boolean {
  const approvedPackets = Array.isArray(slice.metadata?.approved_packets)
    ? slice.metadata?.approved_packets
    : [];
  return approvedPackets.includes(packetId);
}

async function buildAlreadyApprovedResponse(
  request: NextRequest,
  programId: string,
  packetId: string
) {
  if (!packetId) {
    return null;
  }

  const [programsPayload, slicesPayload] = await Promise.all([
    fetchDashboardJson<BootstrapProgramsPayload>(request, "/api/bootstrap/programs"),
    fetchDashboardJson<BootstrapSlicesPayload>(
      request,
      `/api/bootstrap/slices?program_id=${encodeURIComponent(programId)}&limit=500`
    ),
  ]);

  const program = (programsPayload?.programs ?? []).find((item) => item.id === programId);
  if (!program) {
    return null;
  }

  const approvalContextPacketId = String(
    programsPayload?.status?.approval_context?.packet_id ?? ""
  ).trim();
  const stillWaitingOnSamePacket =
    approvalContextPacketId === packetId ||
    Boolean(program.waiting_on_approval_family) ||
    Boolean(program.waiting_on_approval_slice_id);
  if (stillWaitingOnSamePacket) {
    return null;
  }

  const approvedSliceIds = (slicesPayload?.slices ?? [])
    .filter((slice) => hasApprovedPacket(slice, packetId))
    .map((slice) => slice.id)
    .filter(Boolean);
  if (approvedSliceIds.length === 0) {
    return null;
  }

  return NextResponse.json({
    status: "approved",
    program,
    snapshot: programsPayload?.status ?? {},
    takeover: programsPayload?.takeover ?? {},
    approved_packet_id: packetId,
    approved_slice_ids: approvedSliceIds,
    resolved_blocker_ids: [],
    recommendation: program.next_action ?? null,
    next_action: program.next_action ?? null,
    already_approved: true,
  });
}

export async function POST(request: NextRequest, context: Context) {
  const { programId } = await context.params;
  const body = await request.json().catch(() => ({}));
  const packetId = typeof (body as { packet_id?: unknown }).packet_id === "string" ? (body as { packet_id: string }).packet_id : "";
  const response = await proxyAgentOperatorJson(
    request,
    `/v1/bootstrap/programs/${encodeURIComponent(programId)}/approve`,
    "Failed to approve bootstrap packet",
    {
      privilegeClass: "admin",
      defaultReason: "Approved bootstrap packet from dashboard",
      timeoutMs: 60_000,
      bodyOverride: {
        packet_id: packetId,
        reason:
          (body as { reason?: unknown }).reason ??
          (packetId ? `Approved bootstrap packet ${packetId} from dashboard` : "Approved bootstrap packet from dashboard"),
      },
    }
  );
  if (response.status !== 400) {
    return response;
  }

  const alreadyApproved = await buildAlreadyApprovedResponse(request, programId, packetId);
  return alreadyApproved ?? response;
}
