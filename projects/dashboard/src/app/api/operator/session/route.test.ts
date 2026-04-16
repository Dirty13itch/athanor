import { afterEach, describe, expect, it } from "vitest";
import { NextRequest } from "next/server";
import { DELETE, GET, POST } from "./route";

describe("operator session route", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalDashboardToken = env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;
  const originalAgentToken = env.ATHANOR_AGENT_API_TOKEN;
  const originalNodeEnv = env.NODE_ENV;
  const originalFixtureMode = env.DASHBOARD_FIXTURE_MODE;

  afterEach(() => {
    if (originalDashboardToken === undefined) {
      delete env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;
    } else {
      env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = originalDashboardToken;
    }

    if (originalAgentToken === undefined) {
      delete env.ATHANOR_AGENT_API_TOKEN;
    } else {
      env.ATHANOR_AGENT_API_TOKEN = originalAgentToken;
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
  });

  it("reports whether operator session auth is configured", async () => {
    env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = "operator-secret";
    env.DASHBOARD_FIXTURE_MODE = "1";

    const response = await GET(new NextRequest("http://localhost/api/operator/session"));
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      configured: true,
      fixtureMode: true,
      requiresSession: true,
      unlocked: false,
      sessionIdPresent: false,
    });
  });

  it("stays unlocked when only the agent api token is configured", async () => {
    env.NODE_ENV = "production";
    delete env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;
    env.ATHANOR_AGENT_API_TOKEN = "agent-secret";

    const response = await GET(new NextRequest("http://localhost/api/operator/session"));
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      configured: false,
      requiresSession: false,
      unlocked: true,
    });
  });

  it("rejects invalid unlock attempts and sets the cookie for valid ones", async () => {
    env.NODE_ENV = "production";
    env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = "operator-secret";

    const invalid = await POST(
      new NextRequest("http://localhost/api/operator/session", {
        method: "POST",
        body: JSON.stringify({ token: "wrong-token" }),
      })
    );
    expect(invalid.status).toBe(403);

    const valid = await POST(
      new NextRequest("http://localhost/api/operator/session", {
        method: "POST",
        body: JSON.stringify({ token: "operator-secret" }),
      })
    );
    expect(valid.status).toBe(200);
    expect(valid.headers.get("Set-Cookie")).toContain("athanor_operator_session=operator-secret");
  });

  it("clears the operator session cookie on DELETE", async () => {
    const response = await DELETE();
    expect(response.status).toBe(200);
    expect(response.headers.get("Set-Cookie")).toContain("Max-Age=0");
  });

  it("treats unlock as a no-op when no dedicated dashboard token is configured", async () => {
    env.NODE_ENV = "production";
    delete env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;
    env.ATHANOR_AGENT_API_TOKEN = "agent-secret";

    const response = await POST(
      new NextRequest("http://localhost/api/operator/session", {
        method: "POST",
        body: JSON.stringify({ token: "anything" }),
      })
    );

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      ok: true,
      unlocked: true,
      configured: false,
    });
    expect(response.headers.get("Set-Cookie")).toBeNull();
  });
});
