import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  __resetNavAttentionStoreForTests,
  readNavAttentionState,
  saveNavAttentionState,
} from "./store";

describe("operator nav attention store", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_NAV_ATTENTION_PATH;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-nav-attention-"));
    env.DASHBOARD_NAV_ATTENTION_PATH = path.join(tempDir, "nav-attention.json");
    await __resetNavAttentionStoreForTests();
  });

  afterEach(async () => {
    if (originalPath === undefined) {
      delete env.DASHBOARD_NAV_ATTENTION_PATH;
    } else {
      env.DASHBOARD_NAV_ATTENTION_PATH = originalPath;
    }

    if (tempDir) {
      await rm(tempDir, { recursive: true, force: true });
      tempDir = "";
    }

    await rm(path.join(os.tmpdir(), "athanor-dashboard"), { recursive: true, force: true });
  });

  it("persists nav attention state to disk", async () => {
    await saveNavAttentionState({
      "/runs": {
        signature: "/runs|pending_approvals|urgent|1|task-1",
        firstSeenAt: "2026-03-25T12:00:00.000Z",
        acknowledgedAt: null,
      },
    });

    const snapshot = await readNavAttentionState();

    expect(snapshot.source).toBe("file");
    expect(snapshot.routeCount).toBe(1);
    expect(snapshot.state["/runs"]?.signature).toContain("pending_approvals");
  });
});
