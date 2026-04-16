import { afterEach, describe, expect, it } from "vitest";
import {
  buildOperatorSessionIdCookie,
  buildOperatorSessionCookie,
  clearOperatorSessionIdCookie,
  clearOperatorSessionCookie,
  getOperatorMutationToken,
  getOperatorSessionId,
  hasValidOperatorSession,
  hasValidOperatorSessionValue,
  isPrivilegedMutationPath,
  requireOperatorSessionAccess,
  requireOperatorMutationAccess,
  requireSameOriginOperatorSessionAccess,
  validateOperatorToken,
} from "./operator-auth";

describe("operator auth", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalDashboardToken = env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;
  const originalAgentToken = env.ATHANOR_AGENT_API_TOKEN;
  const originalNodeEnv = env.NODE_ENV;

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
  });

  it("recognizes privileged mutation routes and ignores read-only routes", () => {
    expect(isPrivilegedMutationPath("/api/governor/pause", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/pipeline/plans/plan-1/approve", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/operator/nav-attention", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/operator/ui-preferences", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/gallery/rate", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/push/send", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/subscriptions/execution", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/subscriptions/handoffs/hand-off-1/outcome", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/research/jobs", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/research/jobs/job-1/execute", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/skills", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/skills/skill-1/execution", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/skills/skill-1", "DELETE")).toBe(true);
    expect(isPrivilegedMutationPath("/api/consolidation", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/learning/benchmarks", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/improvement/trigger", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/insights/run", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/models/proving-ground", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/governor/heartbeat", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/projects/athanor/packet", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/projects/athanor/architecture", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/projects/athanor/foundry/runs", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/projects/athanor/deployments", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/projects/athanor/promote", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/projects/athanor/rollback", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/projects/athanor/slices", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/projects/athanor/maintenance", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/bootstrap/programs/launch-readiness-bootstrap/promote", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/bootstrap/programs/launch-readiness-bootstrap/nudge", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/operator/approvals/approval-1/approve", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/operator/approvals/approval-1/reject", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/operator/system-mode", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/operator/context/direct-chats", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/operator/context/agent-threads/thread-1", "DELETE")).toBe(true);
    expect(isPrivilegedMutationPath("/api/preferences", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/feedback", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/feedback/implicit", "POST")).toBe(true);
    expect(isPrivilegedMutationPath("/api/governor/pause", "GET")).toBe(false);
    expect(isPrivilegedMutationPath("/api/chat", "POST")).toBe(false);
  });

  it("validates a configured operator token against headers and cookies", () => {
    env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = "secret-token";

    expect(validateOperatorToken("secret-token")).toBe(true);
    expect(validateOperatorToken("wrong-token")).toBe(false);
    expect(hasValidOperatorSessionValue("secret-token")).toBe(true);
    expect(hasValidOperatorSessionValue("wrong-token")).toBe(false);
    expect(
      hasValidOperatorSession(
        new Request("http://localhost/api/governor/pause", {
          headers: {
            cookie: "athanor_operator_session=secret-token; athanor_operator_session_id=session-123",
          },
        })
      )
    ).toBe(true);
    expect(
      getOperatorSessionId(
        new Request("http://localhost/api/governor/pause", {
          headers: {
            cookie: "athanor_operator_session=secret-token; athanor_operator_session_id=session-123",
          },
        })
      )
    ).toBe("session-123");
  });

  it("does not treat the agent api token as a browser operator-session token", () => {
    delete env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;
    env.ATHANOR_AGENT_API_TOKEN = "agent-secret";

    expect(getOperatorMutationToken()).toBe("");
    expect(hasValidOperatorSessionValue("agent-secret")).toBe(true);
    expect(
      hasValidOperatorSession(
        new Request("http://localhost/api/governor/pause", {
          headers: {
            cookie: "athanor_operator_session=agent-secret; athanor_operator_session_id=session-123",
          },
        })
      )
    ).toBe(true);
  });

  it("requires same-origin context for cookie-backed privileged mutations", async () => {
    env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = "secret-token";

    const accepted = requireOperatorMutationAccess(
      new Request("http://localhost/api/gallery/rate", {
        method: "POST",
        headers: {
          cookie: "athanor_operator_session=secret-token",
          origin: "http://localhost",
        },
      })
    );
    expect(accepted).toBeNull();

    const denied = requireOperatorMutationAccess(
      new Request("http://localhost/api/gallery/rate", {
        method: "POST",
        headers: {
          cookie: "athanor_operator_session=secret-token",
          origin: "http://evil.example",
        },
      })
    );
    expect(denied?.status).toBe(403);
    await expect(denied?.json()).resolves.toMatchObject({
      gate: "athanor-operator-origin",
    });
  });

  it("accepts loopback alias origins for protected read routes", () => {
    env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = "secret-token";

    const accepted = requireSameOriginOperatorSessionAccess(
      new Request("http://localhost:3005/api/operator/terminal-bridge", {
        headers: {
          cookie: "athanor_operator_session=secret-token",
          "x-athanor-request-origin": "http://127.0.0.1:3005",
        },
      })
    );

    expect(accepted).toBeNull();
  });

  it("accepts forwarded canonical origins for protected read routes", () => {
    env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = "secret-token";

    const accepted = requireSameOriginOperatorSessionAccess(
      new Request("http://localhost:3001/api/bootstrap/programs/launch-readiness-bootstrap/approve", {
        method: "POST",
        headers: {
          cookie: "athanor_operator_session=secret-token",
          origin: "https://athanor.local",
          "x-forwarded-proto": "https",
          "x-forwarded-host": "athanor.local",
        },
      })
    );

    expect(accepted).toBeNull();
  });

  it("accepts forwarded canonical origins for cookie-backed privileged mutations", () => {
    env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = "secret-token";

    const accepted = requireOperatorMutationAccess(
      new Request("http://localhost:3001/api/gallery/rate", {
        method: "POST",
        headers: {
          cookie: "athanor_operator_session=secret-token",
          origin: "https://athanor.local",
          "x-forwarded-proto": "https",
          "x-forwarded-host": "athanor.local",
        },
      })
    );

    expect(accepted).toBeNull();
  });

  it("requires an operator session for protected read routes", async () => {
    env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = "secret-token";

    const denied = requireOperatorSessionAccess(
      new Request("http://localhost/api/operator/terminal-bridge", {
        headers: {
          cookie: "athanor_operator_session=wrong-token",
        },
      })
    );
    expect(denied?.status).toBe(403);
    await expect(denied?.json()).resolves.toMatchObject({
      gate: "athanor-operator-session",
    });

    const accepted = requireOperatorSessionAccess(
      new Request("http://localhost/api/operator/terminal-bridge", {
        headers: {
          cookie: "athanor_operator_session=secret-token",
        },
      })
    );
    expect(accepted).toBeNull();
  });

  it("builds and clears the operator session cookie", () => {
    expect(buildOperatorSessionCookie("secret-token")).toContain("athanor_operator_session=secret-token");
    expect(buildOperatorSessionCookie("secret-token")).toContain("SameSite=Strict");
    expect(clearOperatorSessionCookie()).toContain("Max-Age=0");
    expect(buildOperatorSessionIdCookie("session-123")).toContain("athanor_operator_session_id=session-123");
    expect(clearOperatorSessionIdCookie()).toContain("Max-Age=0");
  });
});
