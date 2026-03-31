import { createHmac, randomUUID } from "node:crypto";
import type { OperatorActionRequest } from "@/lib/contracts";

const DEFAULT_BRIDGE_TICKET_TTL_SECONDS = 300;
const MIN_BRIDGE_TICKET_TTL_SECONDS = 30;
const MAX_BRIDGE_TICKET_TTL_SECONDS = 3600;

export type BridgeAccessResponse = {
  bridgeUrl: string;
  authMode: "required" | "optional";
  allowedNodes: string[];
  ticket: string | null;
  expiresAt: string | null;
  bridgeReachable?: boolean;
};

export type BridgeTicketPayload = {
  v: 1;
  aud: "ws-pty-bridge";
  jti: string;
  iat: number;
  exp: number;
  allowed_nodes: string[];
  action?: OperatorActionRequest;
};

type BridgeTicketIssueOptions = {
  action?: OperatorActionRequest | null;
};

function firstEnv(names: string[]): string {
  for (const name of names) {
    const value = process.env[name]?.trim();
    if (value) {
      return value;
    }
  }
  return "";
}

function normalizeAllowedNodes(allowedNodes: string[]): string[] {
  return Array.from(
    new Set(
      allowedNodes
        .map((node) => node.trim().toLowerCase())
        .filter(Boolean)
    )
  );
}

function clampTtlSeconds(value: number): number {
  if (!Number.isFinite(value)) {
    return DEFAULT_BRIDGE_TICKET_TTL_SECONDS;
  }
  return Math.min(MAX_BRIDGE_TICKET_TTL_SECONDS, Math.max(MIN_BRIDGE_TICKET_TTL_SECONDS, Math.trunc(value)));
}

export function getBridgeTicketSecret(): string {
  return firstEnv([
    "ATHANOR_WS_PTY_BRIDGE_TICKET_SECRET",
    "ATHANOR_WS_PTY_BRIDGE_AUTH_TOKEN",
    "ATHANOR_WS_PTY_BRIDGE_BEARER_TOKEN",
    "ATHANOR_WS_PTY_BRIDGE_API_TOKEN",
    "ATHANOR_AGENT_API_TOKEN",
    "ATHANOR_API_BEARER_TOKEN",
  ]);
}

export function getBridgeTicketTtlSeconds(): number {
  const raw = firstEnv(["ATHANOR_WS_PTY_BRIDGE_TICKET_TTL_SECONDS"]);
  return clampTtlSeconds(Number.parseInt(raw || String(DEFAULT_BRIDGE_TICKET_TTL_SECONDS), 10));
}

function base64UrlEncodeJson(value: object): string {
  return Buffer.from(JSON.stringify(value), "utf8").toString("base64url");
}

function signTicket(encodedPayload: string, secret: string): string {
  return createHmac("sha256", secret).update(encodedPayload).digest("base64url");
}

function normalizeOperatorAction(action: OperatorActionRequest | null | undefined): OperatorActionRequest | undefined {
  if (!action) {
    return undefined;
  }

  return {
    actor: action.actor.trim(),
    session_id: action.session_id.trim(),
    correlation_id: action.correlation_id.trim(),
    reason: action.reason.trim(),
    dry_run: Boolean(action.dry_run),
    protected_mode: Boolean(action.protected_mode),
  };
}

export function issueBridgeAccessTicket(
  allowedNodes: string[],
  options: BridgeTicketIssueOptions = {}
): {
  ticket: string;
  expiresAt: string;
} | null {
  const secret = getBridgeTicketSecret();
  if (!secret) {
    return null;
  }

  const normalizedAllowedNodes = normalizeAllowedNodes(allowedNodes);
  const ttlSeconds = getBridgeTicketTtlSeconds();
  const issuedAt = Math.floor(Date.now() / 1000);
  const expiresAt = issuedAt + ttlSeconds;
  const normalizedAction = normalizeOperatorAction(options.action);
  const payload: BridgeTicketPayload = {
    v: 1,
    aud: "ws-pty-bridge",
    jti: randomUUID(),
    iat: issuedAt,
    exp: expiresAt,
    allowed_nodes: normalizedAllowedNodes,
    ...(normalizedAction ? { action: normalizedAction } : {}),
  };

  const encodedPayload = base64UrlEncodeJson(payload);
  const signature = signTicket(encodedPayload, secret);
  return {
    ticket: `${encodedPayload}.${signature}`,
    expiresAt: new Date(expiresAt * 1000).toISOString(),
  };
}
