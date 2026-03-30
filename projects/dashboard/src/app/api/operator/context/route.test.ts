import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { __resetOperatorContextStoreForTests, saveDirectChatSession } from "./store";
import { GET } from "./route";

describe("GET /api/operator/context", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_OPERATOR_CONTEXT_PATH;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-operator-context-"));
    env.DASHBOARD_OPERATOR_CONTEXT_PATH = path.join(tempDir, "operator-context.json");
    await __resetOperatorContextStoreForTests();
  });

  afterEach(async () => {
    if (originalPath === undefined) {
      delete env.DASHBOARD_OPERATOR_CONTEXT_PATH;
    } else {
      env.DASHBOARD_OPERATOR_CONTEXT_PATH = originalPath;
    }

    if (tempDir) {
      await rm(tempDir, { recursive: true, force: true });
      tempDir = "";
    }
  });

  it("returns the persisted operator context snapshot", async () => {
    await saveDirectChatSession({
      id: "chat-1",
      title: "Topology review",
      modelId: "/models/reasoning",
      target: "litellm",
      createdAt: "2026-03-25T12:00:00.000Z",
      updatedAt: "2026-03-25T12:05:00.000Z",
      messages: [],
    });

    const response = await GET();
    expect(response.status).toBe(200);

    const payload = (await response.json()) as {
      sessionCount: number;
      threadCount: number;
      sessions: Array<{ id: string }>;
    };

    expect(payload.sessionCount).toBe(1);
    expect(payload.threadCount).toBe(0);
    expect(payload.sessions[0]?.id).toBe("chat-1");
  });
});
