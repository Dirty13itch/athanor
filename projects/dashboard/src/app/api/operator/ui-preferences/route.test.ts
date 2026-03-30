import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { __resetUiPreferencesStoreForTests } from "./store";
import { GET, POST } from "./route";

describe("operator ui preferences route", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_UI_PREFERENCES_PATH;
  const originalToken = env.ATHANOR_DASHBOARD_OPERATOR_TOKEN;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-ui-preferences-"));
    env.DASHBOARD_UI_PREFERENCES_PATH = path.join(tempDir, "ui-preferences.json");
    env.ATHANOR_DASHBOARD_OPERATOR_TOKEN = "secret-token";
    await __resetUiPreferencesStoreForTests();
  });

  afterEach(async () => {
    if (originalPath === undefined) {
      delete env.DASHBOARD_UI_PREFERENCES_PATH;
    } else {
      env.DASHBOARD_UI_PREFERENCES_PATH = originalPath;
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
      new Request("http://localhost/api/operator/ui-preferences", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          density: "compact",
        }),
      })
    );

    expect(response.status).toBe(403);
  });

  it("stores and returns operator UI preferences", async () => {
    const createResponse = await POST(
      new Request("http://localhost/api/operator/ui-preferences", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-athanor-operator-token": "secret-token",
        },
        body: JSON.stringify({
          density: "compact",
          lastSelectedAgentId: "coding-agent",
          lastSelectedModelKey: "litellm::/models/qwen",
          dismissedHints: ["welcome"],
        }),
      })
    );

    expect(createResponse.status).toBe(200);
    const createPayload = (await createResponse.json()) as {
      preferences: { density: string; lastSelectedAgentId: string | null };
    };
    expect(createPayload.preferences.density).toBe("compact");
    expect(createPayload.preferences.lastSelectedAgentId).toBe("coding-agent");

    const response = await GET();
    expect(response.status).toBe(200);

    const payload = (await response.json()) as {
      preferences: { density: string; dismissedHints: string[] };
    };
    expect(payload.preferences.density).toBe("compact");
    expect(payload.preferences.dismissedHints).toEqual(["welcome"]);
  });
});
