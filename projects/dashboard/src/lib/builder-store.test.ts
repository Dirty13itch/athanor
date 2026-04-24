import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  __resetBuilderStoreForTests,
  applyBuilderSyntheticInboxAction,
  applyBuilderSyntheticTodoTransition,
  createBuilderSession,
  listBuilderSyntheticInboxItems,
  listBuilderSyntheticApprovals,
  listBuilderSyntheticRuns,
  listBuilderSyntheticTodos,
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

  it("keeps the live codex route bounded to repo worktrees", async () => {
    const session = await createBuilderSession({
      goal: "Do not widen the first builder kernel route beyond repo worktrees.",
      task_class: "multi_file_implementation",
      sensitivity_class: "private_but_cloud_allowed",
      workspace_mode: "same_repo",
      needs_background: false,
      needs_github: false,
      acceptance_criteria: ["Keep same-repo mutation off the live builder slice."],
    });

    expect(session.route_decision.route_id).toBe("builder:claude_code:rescue");
    expect(session.route_decision.activation_state).toBe("planned_future");
    expect(session.status).toBe("blocked");
  });

  it("projects builder approvals into inbox items and converts them into synthetic todos", async () => {
    const session = await createBuilderSession({
      goal: "Approve the live builder session and capture follow-up.",
      task_class: "multi_file_implementation",
      sensitivity_class: "private_but_cloud_allowed",
      workspace_mode: "repo_worktree",
      needs_background: false,
      needs_github: false,
      acceptance_criteria: ["Expose inbox projection", "Convert builder inbox to todo"],
    });

    const inbox = await listBuilderSyntheticInboxItems("new");
    const approvalItem = inbox.find((item) => item.related_task_id === session.id);

    expect(approvalItem?.id).toMatch(/^builder-inbox-/);
    expect(approvalItem?.requires_decision).toBe(true);
    expect(approvalItem?.decision_type).toBe("approve");

    const converted = await applyBuilderSyntheticInboxAction(approvalItem!.id, "convert");
    expect(converted.status).toBe("converted");

    const todos = await listBuilderSyntheticTodos("open");
    expect(todos[0]?.metadata?.linked_inbox_id).toBe(approvalItem?.id);
    expect(todos[0]?.metadata?.builder_session_id).toBe(session.id);

    const doneTodo = await applyBuilderSyntheticTodoTransition(String(todos[0]?.id), "done");
    expect(doneTodo.status).toBe("done");

    const convertedInbox = await listBuilderSyntheticInboxItems("converted");
    expect(convertedInbox.some((item) => item.id === approvalItem?.id)).toBe(true);
  });
});
