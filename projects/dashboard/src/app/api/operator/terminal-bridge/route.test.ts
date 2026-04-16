import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET } from "./route";
import { getBridgeTicketSecret, type BridgeTicketPayload } from "@/lib/bridge-ticket";

function decodeTicketPayload(ticket: string): BridgeTicketPayload {
  const [encodedPayload] = ticket.split(".", 1);
  return JSON.parse(Buffer.from(encodedPayload, "base64url").toString("utf8")) as BridgeTicketPayload;
}

describe("GET /api/operator/terminal-bridge", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalOperatorToken = env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;
  const originalBridgeToken = env.ATHANOR_WS_PTY_BRIDGE_AUTH_TOKEN;
  const originalBridgeTicketSecret = env.ATHANOR_WS_PTY_BRIDGE_TICKET_SECRET;
  const originalBridgeUrl = env.ATHANOR_WS_PTY_BRIDGE_URL;
  const originalAllowedNodes = env.ATHANOR_WS_PTY_BRIDGE_ALLOWED_NODES;
  const originalTicketTtl = env.ATHANOR_WS_PTY_BRIDGE_TICKET_TTL_SECONDS;
  const originalNodeEnv = env.NODE_ENV;
  const originalFixtureMode = env.DASHBOARD_FIXTURE_MODE;

  afterEach(() => {
    if (originalOperatorToken === undefined) {
      delete env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;
    } else {
      env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = originalOperatorToken;
    }

    if (originalBridgeToken === undefined) {
      delete env.ATHANOR_WS_PTY_BRIDGE_AUTH_TOKEN;
    } else {
      env.ATHANOR_WS_PTY_BRIDGE_AUTH_TOKEN = originalBridgeToken;
    }

    if (originalBridgeTicketSecret === undefined) {
      delete env.ATHANOR_WS_PTY_BRIDGE_TICKET_SECRET;
    } else {
      env.ATHANOR_WS_PTY_BRIDGE_TICKET_SECRET = originalBridgeTicketSecret;
    }

    if (originalBridgeUrl === undefined) {
      delete env.ATHANOR_WS_PTY_BRIDGE_URL;
    } else {
      env.ATHANOR_WS_PTY_BRIDGE_URL = originalBridgeUrl;
    }

    if (originalAllowedNodes === undefined) {
      delete env.ATHANOR_WS_PTY_BRIDGE_ALLOWED_NODES;
    } else {
      env.ATHANOR_WS_PTY_BRIDGE_ALLOWED_NODES = originalAllowedNodes;
    }

    if (originalTicketTtl === undefined) {
      delete env.ATHANOR_WS_PTY_BRIDGE_TICKET_TTL_SECONDS;
    } else {
      env.ATHANOR_WS_PTY_BRIDGE_TICKET_TTL_SECONDS = originalTicketTtl;
    }

    if (originalNodeEnv === undefined) {
      delete env.NODE_ENV;
    } else {
      env.NODE_ENV = originalNodeEnv;
    }

    if (originalFixtureMode === undefined) {
      delete env.DASHBOARD_FIXTURE_MODE;
    } else {
      env.DASHBOARD_FIXTURE_MODE = originalFixtureMode;
    }

    vi.restoreAllMocks();
  });

  it("returns bridge access details for an unlocked operator session", async () => {
    env.NODE_ENV = "production";
    env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = "operator-secret";
    env.ATHANOR_WS_PTY_BRIDGE_TICKET_SECRET = "bridge-ticket-secret";
    env.ATHANOR_WS_PTY_BRIDGE_URL = "http://terminal.internal:3100";
    env.ATHANOR_WS_PTY_BRIDGE_ALLOWED_NODES = "node2,foundry";
    env.ATHANOR_WS_PTY_BRIDGE_TICKET_TTL_SECONDS = "120";

    const request = new NextRequest("http://localhost/api/operator/terminal-bridge", {
      headers: {
        cookie:
          "athanor_operator_session=operator-secret; athanor_operator_session_id=session-123",
        origin: "http://localhost",
      },
    });

    const response = await GET(request);
    expect(response.status).toBe(200);
    const payload = await response.json();
    expect(payload).toMatchObject({
      bridgeUrl: "http://terminal.internal:3100",
      authMode: "required",
      allowedNodes: ["workshop", "foundry"],
    });
    expect(payload.ticket).toEqual(expect.any(String));
    expect(payload.ticket.split(".")).toHaveLength(2);
    expect(payload.expiresAt).toEqual(expect.any(String));
    expect(getBridgeTicketSecret()).toBe("bridge-ticket-secret");

    const ticketPayload = decodeTicketPayload(payload.ticket);
    expect(ticketPayload.allowed_nodes).toEqual(["workshop", "foundry"]);
    expect(ticketPayload.action).toMatchObject({
      actor: "dashboard-operator",
      session_id: "session-123",
      reason: "Manual terminal bridge session issuance from dashboard",
      dry_run: false,
      protected_mode: false,
    });
    expect(ticketPayload.action?.correlation_id).toEqual(expect.any(String));
  });

  it("returns optional bridge access details when no operator session token is configured", async () => {
    env.NODE_ENV = "development";
    delete env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;
    delete env.ATHANOR_WS_PTY_BRIDGE_TICKET_SECRET;
    delete env.ATHANOR_WS_PTY_BRIDGE_AUTH_TOKEN;
    env.ATHANOR_WS_PTY_BRIDGE_URL = "http://terminal.internal:3100";
    env.ATHANOR_WS_PTY_BRIDGE_ALLOWED_NODES = "dev,workshop";

    const request = new NextRequest("http://localhost/api/operator/terminal-bridge", {
      headers: {
        origin: "http://localhost",
      },
    });

    const response = await GET(request);
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      bridgeUrl: "http://terminal.internal:3100",
      authMode: "optional",
      allowedNodes: ["dev", "workshop"],
      ticket: null,
      expiresAt: null,
    });
  });

  it("denies requests without an operator session", async () => {
    env.NODE_ENV = "production";
    env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = "operator-secret";
    env.ATHANOR_WS_PTY_BRIDGE_AUTH_TOKEN = "bridge-secret";

    const request = new NextRequest("http://localhost/api/operator/terminal-bridge");
    const response = await GET(request);

    expect(response.status).toBe(403);
    await expect(response.json()).resolves.toMatchObject({
      gate: "athanor-operator-session",
    });
  });

  it("denies cross-origin ticket issuance even with a valid operator session", async () => {
    env.NODE_ENV = "production";
    env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = "operator-secret";
    env.ATHANOR_WS_PTY_BRIDGE_TICKET_SECRET = "bridge-ticket-secret";

    const request = new NextRequest("http://localhost/api/operator/terminal-bridge", {
      headers: {
        cookie:
          "athanor_operator_session=operator-secret; athanor_operator_session_id=session-123",
        origin: "https://evil.example",
      },
    });

    const response = await GET(request);
    expect(response.status).toBe(403);
    await expect(response.json()).resolves.toMatchObject({
      gate: "athanor-operator-origin",
    });
  });

  it("marks the bridge unreachable in fixture mode when the health probe fails", async () => {
    env.NODE_ENV = "production";
    env.DASHBOARD_FIXTURE_MODE = "1";
    env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = "operator-secret";
    env.ATHANOR_WS_PTY_BRIDGE_TICKET_SECRET = "bridge-ticket-secret";
    env.ATHANOR_WS_PTY_BRIDGE_URL = "http://terminal.internal:3100";

    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("connect ECONNREFUSED"));

    const request = new NextRequest("http://localhost/api/operator/terminal-bridge", {
      headers: {
        cookie:
          "athanor_operator_session=operator-secret; athanor_operator_session_id=session-123",
        origin: "http://localhost",
      },
    });

    const response = await GET(request);
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      bridgeUrl: "http://terminal.internal:3100",
      bridgeReachable: false,
    });
  });
});
