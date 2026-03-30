import { NextRequest, NextResponse } from "next/server";
import { getTerminalBridgeBaseUrl } from "@/lib/runtime-hosts";
import { buildOperatorActionRequest, emitOperatorAuditEvent } from "@/lib/operator-actions";
import { requireSameOriginOperatorSessionAccess } from "@/lib/operator-auth";
import { getBridgeTicketSecret, issueBridgeAccessTicket, type BridgeAccessResponse } from "@/lib/bridge-ticket";
import { isDashboardFixtureMode } from "@/lib/dashboard-fixtures";

export const runtime = "nodejs";

const DEFAULT_ALLOWED_NODES = ["dev", "foundry", "workshop"];

function normalizeNodeId(nodeId: string): string {
  const normalized = nodeId.trim().toLowerCase();
  if (normalized === "node1") {
    return "foundry";
  }
  if (normalized === "node2") {
    return "workshop";
  }
  return normalized;
}

function parseAllowedNodes(): string[] {
  const configured = process.env.ATHANOR_WS_PTY_BRIDGE_ALLOWED_NODES?.trim();
  if (!configured) {
    return DEFAULT_ALLOWED_NODES;
  }

  const nodes = configured
    .split(",")
    .map((node) => normalizeNodeId(node))
    .filter(Boolean);
  return nodes.length > 0 ? Array.from(new Set(nodes)) : DEFAULT_ALLOWED_NODES;
}

function getBridgeUrl(): string {
  return getTerminalBridgeBaseUrl();
}

async function probeBridgeReachability(bridgeUrl: string): Promise<boolean> {
  try {
    const endpoint = new URL(bridgeUrl);
    endpoint.pathname = `${endpoint.pathname.replace(/\/+$/, "")}/health`;
    const response = await fetch(endpoint.toString(), {
      cache: "no-store",
      signal: AbortSignal.timeout(1_000),
    });
    return response.ok;
  } catch {
    return false;
  }
}

export async function GET(request: NextRequest) {
  const gate = requireSameOriginOperatorSessionAccess(request);
  if (gate) {
    return gate;
  }

  const prepared = buildOperatorActionRequest(request, {}, {
    privilegeClass: "operator",
    defaultActor: "dashboard-operator",
    defaultReason: "Manual terminal bridge session issuance from dashboard",
  });
  if (prepared instanceof NextResponse) {
    return prepared;
  }

  const bridgeUrl = getBridgeUrl();
  const bridgeTicketSecret = getBridgeTicketSecret();
  const authMode =
    bridgeTicketSecret || process.env.NODE_ENV === "production" ? "required" : "optional";
  const allowedNodes = parseAllowedNodes();

  if (authMode === "required" && !bridgeTicketSecret) {
    return NextResponse.json(
      { error: "ATHANOR_WS_PTY_BRIDGE_TICKET_SECRET or bridge auth token is required for operator terminal access" },
      { status: 503 }
    );
  }

  const issuedTicket =
    authMode === "required"
      ? issueBridgeAccessTicket(allowedNodes, { action: prepared.action })
      : null;
  const bridgeReachable = isDashboardFixtureMode()
    ? await probeBridgeReachability(bridgeUrl)
    : undefined;
  const response: BridgeAccessResponse = {
    bridgeUrl,
    authMode,
    allowedNodes,
    ticket: issuedTicket?.ticket ?? null,
    expiresAt: issuedTicket?.expiresAt ?? null,
    ...(bridgeReachable === undefined ? {} : { bridgeReachable }),
  };

  await emitOperatorAuditEvent({
    service: "dashboard",
    route: "/api/operator/terminal-bridge",
    action_class: "operator",
    decision: "accepted",
    status_code: 200,
    detail: issuedTicket ? "Issued bridge access ticket" : "Returned optional bridge access metadata",
    target: "ws-pty-bridge",
    metadata: {
      allowed_nodes: allowedNodes,
      auth_mode: authMode,
      expires_at: response.expiresAt,
      bridge_reachable: bridgeReachable ?? null,
    },
    action: prepared.action,
  });

  return NextResponse.json(response);
}
