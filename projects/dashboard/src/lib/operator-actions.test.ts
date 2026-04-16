import { describe, expect, it } from "vitest";
import { NextResponse } from "next/server";
import { buildOperatorActionRequest } from "./operator-actions";

describe("operator actions", () => {
  it("backfills an operator session id when no operator token is configured", () => {
    const env = process.env as Record<string, string | undefined>;
    const originalToken = env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;
    delete env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;

    try {
      const result = buildOperatorActionRequest(
        new Request("http://localhost/api/operator/terminal-bridge"),
        { reason: "Open terminal bridge" },
        { privilegeClass: "operator" }
      );

      expect(result).not.toBeInstanceOf(NextResponse);
      if (result instanceof NextResponse) {
        return;
      }

      expect(result.action.session_id).toMatch(/^dashboard-session-/);
      expect(result.payload.session_id).toBe(result.action.session_id);
    } finally {
      if (originalToken === undefined) {
        delete env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;
      } else {
        env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = originalToken;
      }
    }
  });

  it("builds an operator action envelope from the session cookie", () => {
    const result = buildOperatorActionRequest(
      new Request("http://localhost/api/governor/pause", {
        headers: {
          cookie:
            "athanor_operator_session=secret-token; athanor_operator_session_id=session-123",
        },
      }),
      { scope: "global", reason: "Pause all automation" },
      { privilegeClass: "admin" }
    );

    expect(result).not.toBeInstanceOf(NextResponse);
    if (result instanceof NextResponse) {
      return;
    }

    expect(result.action.actor).toBe("dashboard-operator");
    expect(result.action.session_id).toBe("session-123");
    expect(result.action.reason).toBe("Pause all automation");
    expect(result.payload.correlation_id).toBeTruthy();
  });

  it("backfills an operator session id for valid header-authenticated requests", () => {
    const env = process.env as Record<string, string | undefined>;
    const originalToken = env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;
    env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = "secret-token";

    try {
      const result = buildOperatorActionRequest(
        new Request("http://localhost/api/governor/pause", {
          headers: {
            "x-athanor-operator-token": "secret-token",
          },
        }),
        { scope: "global", reason: "Pause all automation" },
        { privilegeClass: "admin" }
      );

      expect(result).not.toBeInstanceOf(NextResponse);
      if (result instanceof NextResponse) {
        return;
      }

      expect(result.action.session_id).toMatch(/^dashboard-session-/);
      expect(result.payload.session_id).toBe(result.action.session_id);
    } finally {
      if (originalToken === undefined) {
        delete env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;
      } else {
        env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = originalToken;
      }
    }
  });

  it("rejects admin actions without a reason", async () => {
    const result = buildOperatorActionRequest(
      new Request("http://localhost/api/governor/pause", {
        headers: {
          cookie:
            "athanor_operator_session=secret-token; athanor_operator_session_id=session-123",
        },
      }),
      { scope: "global" },
      { privilegeClass: "admin" }
    );

    expect(result).toBeInstanceOf(NextResponse);
    if (!(result instanceof NextResponse)) {
      return;
    }

    expect(result.status).toBe(400);
    await expect(result.json()).resolves.toMatchObject({
      error: "reason is required for admin and destructive-admin actions",
    });
  });
});
