import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  __resetBuilderStoreForTests,
  createBuilderSession,
  readBuilderSession,
  readBuilderSummary,
} from "@/lib/builder-store";
import { GET as builderSummaryGet } from "@/app/api/builder/summary/route";
import { POST as controlPost } from "@/app/api/builder/sessions/[sessionId]/control/route";

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () =>
    new Response(
      JSON.stringify({
        available: true,
        degraded: false,
        tasks: {
          pending_approval: 0,
          failed_actionable: 0,
          stale_lease: 0,
          failed_historical_repaired: 0,
        },
      }),
      { status: 200 },
    ),
  ),
}));

vi.mock("@/lib/operator-frontdoor", () => ({
  loadSteadyStateFrontDoor: vi.fn(async () => ({
    snapshot: null,
    status: {
      available: true,
      degraded: false,
      detail: null,
      sourceKind: null,
      sourcePath: null,
    },
  })),
}));

import { GET as operatorSummaryGet } from "@/app/api/operator/summary/route";
import { proxyAgentJson } from "@/lib/server-agent";

describe("protocol-first builder kernel formal eval", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_BUILDER_STORE_PATH;
  const originalRepoRoot = env.DASHBOARD_BUILDER_REPO_ROOT;
  const originalTestMode = env.DASHBOARD_BUILDER_TEST_EXECUTION_MODE;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-builder-formal-eval-"));
    env.DASHBOARD_BUILDER_STORE_PATH = path.join(tempDir, "builder-sessions.json");
    env.DASHBOARD_BUILDER_REPO_ROOT = "/mnt/c/Athanor";
    delete env.DASHBOARD_BUILDER_TEST_EXECUTION_MODE;
    await __resetBuilderStoreForTests();
  });

  afterEach(async () => {
    vi.clearAllMocks();
    if (originalPath === undefined) {
      delete env.DASHBOARD_BUILDER_STORE_PATH;
    } else {
      env.DASHBOARD_BUILDER_STORE_PATH = originalPath;
    }

    if (originalRepoRoot === undefined) {
      delete env.DASHBOARD_BUILDER_REPO_ROOT;
    } else {
      env.DASHBOARD_BUILDER_REPO_ROOT = originalRepoRoot;
    }

    if (originalTestMode === undefined) {
      delete env.DASHBOARD_BUILDER_TEST_EXECUTION_MODE;
    } else {
      env.DASHBOARD_BUILDER_TEST_EXECUTION_MODE = originalTestMode;
    }

    if (tempDir) {
      await rm(tempDir, { recursive: true, force: true });
      tempDir = "";
    }
  });

  it("keeps sovereign-only tasks on the local-only lane", async () => {
    const session = await createBuilderSession({
      goal: "Keep this task on a sovereign-only coding lane.",
      task_class: "sovereign_private_coding",
      sensitivity_class: "sovereign_only",
      workspace_mode: "same_repo",
      needs_background: false,
      needs_github: false,
      acceptance_criteria: ["Do not route this task to a cloud-capable worker."],
    });

    expect(session.route_decision.route_id).toBe("builder:sovereign:local_only");
    expect(session.route_decision.activation_state).toBe("local_only");
    expect(session.route_decision.primary_adapter).toBe("sovereign_coder");
    expect(session.status).toBe("blocked");
  });

  it("keeps GitHub-dependent tasks off the live Codex route until an adapter is linked", async () => {
    const session = await createBuilderSession({
      goal: "Delegate this repo change through a GitHub-native async builder lane.",
      task_class: "multi_file_implementation",
      sensitivity_class: "private_but_cloud_allowed",
      workspace_mode: "repo_worktree",
      needs_background: true,
      needs_github: true,
      acceptance_criteria: ["Do not queue the live Codex route for this task."],
    });

    expect(session.route_decision.route_id).toBe("builder:copilot:github_async");
    expect(session.route_decision.activation_state).toBe("planned_future");
    expect(session.status).toBe("blocked");
  });

  it("fails closed when the live builder route hits a controlled execution failure", async () => {
    env.DASHBOARD_BUILDER_TEST_EXECUTION_MODE = "failure";
    const session = await createBuilderSession({
      goal: "Drive the builder route through a controlled failure path.",
      task_class: "multi_file_implementation",
      sensitivity_class: "private_but_cloud_allowed",
      workspace_mode: "repo_worktree",
      needs_background: false,
      needs_github: false,
      acceptance_criteria: ["Publish a failed result packet instead of false success."],
    });

    const approvalId = session.approvals[0]?.id;
    expect(approvalId).toBeTruthy();

    const response = await controlPost(
      new NextRequest(`http://localhost/api/builder/sessions/${session.id}/control`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ action: "approve", approval_id: approvalId }),
      }),
      { params: Promise.resolve({ sessionId: session.id }) },
    );

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      ok: true,
      session: {
        id: session.id,
        status: "running",
      },
    });

    await new Promise((resolve) => setTimeout(resolve, 120));
    const failed = await readBuilderSession(session.id);
    expect(failed?.status).toBe("failed");
    expect(failed?.verification_state.status).toBe("failed");
    expect(failed?.latest_result_packet?.outcome).toBe("failed");
    expect(failed?.latest_result_packet?.recovery_gate).toBe("resume_available");
    expect(failed?.latest_result_packet?.resumable_handle).toBeTruthy();
  });

  it("keeps builder and operator summary projections coherent for the active session", async () => {
    const session = await createBuilderSession({
      goal: "Project the current builder lane through the operator front door.",
      task_class: "multi_file_implementation",
      sensitivity_class: "private_but_cloud_allowed",
      workspace_mode: "repo_worktree",
      needs_background: false,
      needs_github: false,
      acceptance_criteria: ["Expose the same current builder session across summary routes."],
    });

    const canonical = await readBuilderSummary();
    const builderResponse = await builderSummaryGet();
    const operatorResponse = await operatorSummaryGet();
    const builderPayload = await builderResponse.json();
    const operatorPayload = await operatorResponse.json();

    expect(builderPayload.current_session.id).toBe(session.id);
    expect(builderPayload.current_session.id).toBe(canonical.current_session?.id);
    expect(operatorPayload.builderFrontDoor.current_session.id).toBe(canonical.current_session?.id);
    expect(operatorPayload.builderFrontDoor.current_session.current_route).toBe(
      canonical.current_session?.current_route,
    );
    expect(operatorPayload.builderFrontDoor.pending_approval_count).toBe(
      canonical.pending_approval_count,
    );
    expect(proxyAgentJson).toHaveBeenCalledOnce();
  });
});
