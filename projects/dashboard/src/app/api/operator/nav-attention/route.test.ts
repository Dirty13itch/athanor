import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { __resetNavAttentionStoreForTests } from "./store";
import { GET, POST } from "./route";

describe("operator nav attention route", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_NAV_ATTENTION_PATH;
  const originalToken = env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-nav-attention-"));
    env.DASHBOARD_NAV_ATTENTION_PATH = path.join(tempDir, "nav-attention.json");
    env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = "secret-token";
    await __resetNavAttentionStoreForTests();
  });

  afterEach(async () => {
    if (originalPath === undefined) {
      delete env.DASHBOARD_NAV_ATTENTION_PATH;
    } else {
      env.DASHBOARD_NAV_ATTENTION_PATH = originalPath;
    }

    if (originalToken === undefined) {
      delete env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;
    } else {
      env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = originalToken;
    }

    if (tempDir) {
      await rm(tempDir, { recursive: true, force: true });
      tempDir = "";
    }
  });

  it("rejects unauthenticated writes", async () => {
    const response = await POST(
      new Request("http://localhost/api/operator/nav-attention", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          "/services": {
            signature: "/services|degraded_core_services|urgent|1|dashboard",
            firstSeenAt: "2026-03-25T12:00:00.000Z",
          },
        }),
      })
    );

    expect(response.status).toBe(403);
  });

  it("stores and returns persisted nav attention state", async () => {
    const createResponse = await POST(
      new Request("http://localhost/api/operator/nav-attention", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-athanor-operator-token": "secret-token",
        },
        body: JSON.stringify({
          "/services": {
            signature: "/services|degraded_core_services|urgent|1|dashboard",
            firstSeenAt: "2026-03-25T12:00:00.000Z",
            acknowledgedAt: "2026-03-25T12:01:00.000Z",
          },
        }),
      })
    );

    expect(createResponse.status).toBe(200);
    const createPayload = (await createResponse.json()) as {
      routeCount: number;
      state: Record<string, { signature: string }>;
    };
    expect(createPayload.routeCount).toBe(1);
    expect(createPayload.state["/services"]?.signature).toContain("degraded_core_services");

    const response = await GET();
    expect(response.status).toBe(200);

    const payload = (await response.json()) as {
      routeCount: number;
      state: Record<string, { acknowledgedAt: string | null }>;
    };
    expect(payload.routeCount).toBe(1);
    expect(payload.state["/services"]?.acknowledgedAt).toBe("2026-03-25T12:01:00.000Z");
  });
});
