import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  __resetBuilderStoreForTests,
  createBuilderSession,
  listBuilderSyntheticApprovals,
  listBuilderSyntheticRuns,
  readBuilderSessionEvents,
  readBuilderSummary,
} from "@/lib/builder-store";

describe("builder store", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_BUILDER_STORE_PATH;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-builder-store-"));
    env.DASHBOARD_BUILDER_STORE_PATH = path.join(tempDir, "builder-sessions.json");
    await __resetBuilderStoreForTests();
  });

  afterEach(async () => {
    if (originalPath === undefined) {
      delete env.DASHBOARD_BUILDER_STORE_PATH;
    } else {
      env.DASHBOARD_BUILDER_STORE_PATH = originalPath;
    }

    if (tempDir) {
      await rm(tempDir, { recursive: true, force: true });
      tempDir = "";
    }
  });

  it("creates a live-ready codex session and projects it into builder summary and synthetic feeds", async () => {
    const session = await createBuilderSession({
      goal: "Implement the first builder front-door Codex route.",
      task_class: "multi_file_implementation",
      sensitivity_class: "private_but_cloud_allowed",
      workspace_mode: "repo_worktree",
      needs_background: false,
      needs_github: false,
      acceptance_criteria: [
        "Persist a builder session",
        "Select the Codex route",
        "Expose verification state",
      ],
    });

    expect(session.route_decision.primary_adapter).toBe("codex");
    expect(session.route_decision.activation_state).toBe("live_ready");
    expect(session.status).toBe("waiting_approval");
    expect(session.shadow_mode).toBe(false);
    expect(session.fallback_state).toBe("approval_pending");

    const summary = await readBuilderSummary();
    expect(summary.current_session?.id).toBe(session.id);
    expect(summary.pending_approval_count).toBe(1);
    expect(summary.current_session?.resumable_handle).toBeNull();

    const events = await readBuilderSessionEvents(session.id);
    expect(events?.count).toBeGreaterThanOrEqual(4);

    const runs = await listBuilderSyntheticRuns("waiting_approval");
    expect(runs[0]?.id).toBe(`builder-run-${session.id}`);
    expect(runs[0]?.approval_pending).toBe(true);

    const approvals = await listBuilderSyntheticApprovals("pending");
    expect(approvals[0]?.related_task_id).toBe(session.id);
    expect(approvals[0]?.task_agent_id).toBe("codex");
  });
});
