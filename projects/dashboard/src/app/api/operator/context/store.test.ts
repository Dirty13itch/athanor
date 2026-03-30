import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  __resetOperatorContextStoreForTests,
  readOperatorContext,
  saveAgentThread,
  saveDirectChatSession,
} from "./store";

describe("operator context store", () => {
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

  it("persists direct-chat sessions and agent threads to disk", async () => {
    await saveDirectChatSession({
      id: "chat-1",
      title: "Model review",
      modelId: "/models/reasoning",
      target: "litellm",
      createdAt: "2026-03-25T12:00:00.000Z",
      updatedAt: "2026-03-25T12:05:00.000Z",
      messages: [],
    });
    await saveAgentThread({
      id: "thread-1",
      agentId: "coding-agent",
      title: "Fix the governor",
      createdAt: "2026-03-25T12:01:00.000Z",
      updatedAt: "2026-03-25T12:06:00.000Z",
      messages: [],
    });

    const snapshot = await readOperatorContext();

    expect(snapshot.source).toBe("file");
    expect(snapshot.sessionCount).toBe(1);
    expect(snapshot.threadCount).toBe(1);
    expect(snapshot.sessions[0]?.id).toBe("chat-1");
    expect(snapshot.threads[0]?.id).toBe("thread-1");
    expect(snapshot.recentContext.map((item) => item.id)).toEqual(["thread-1", "chat-1"]);
  });
});
