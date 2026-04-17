import path from "node:path";
import { readFile, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  __resetBuilderStoreForTests,
  createBuilderSession,
  readBuilderSession,
} from "@/lib/builder-store";
import { POST as controlPost } from "@/app/api/builder/sessions/[sessionId]/control/route";

const env = process.env as Record<string, string | undefined>;
const liveIt = env.ATHANOR_ENABLE_LIVE_BUILDER_FORMAL_EVAL === "1" ? it : it.skip;

describe("protocol-first builder kernel live route formal eval", () => {
  const originalStorePath = env.DASHBOARD_BUILDER_STORE_PATH;
  const originalRepoRoot = env.DASHBOARD_BUILDER_REPO_ROOT;
  const originalRunsRoot = env.DASHBOARD_BUILDER_RUNS_ROOT;
  const originalWorktreeRoot = env.DASHBOARD_BUILDER_WORKTREE_ROOT;
  const originalSourceCodexHome = env.DASHBOARD_BUILDER_SOURCE_CODEX_HOME;
  const originalExecTimeout = env.DASHBOARD_BUILDER_EXECUTION_TIMEOUT_MS;
  const originalTestMode = env.DASHBOARD_BUILDER_TEST_EXECUTION_MODE;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp("/tmp/athanor-builder-live-formal-eval-");
    env.DASHBOARD_BUILDER_STORE_PATH = path.join(tempDir, "builder-sessions.json");
    env.DASHBOARD_BUILDER_RUNS_ROOT = path.join(tempDir, "runs");
    env.DASHBOARD_BUILDER_WORKTREE_ROOT = path.join(tempDir, "worktrees");
    env.DASHBOARD_BUILDER_REPO_ROOT = "/mnt/c/Athanor";
    env.DASHBOARD_BUILDER_SOURCE_CODEX_HOME = "/mnt/c/Users/Shaun/.codex";
    env.DASHBOARD_BUILDER_EXECUTION_TIMEOUT_MS = "300000";
    delete env.DASHBOARD_BUILDER_TEST_EXECUTION_MODE;
    await __resetBuilderStoreForTests();
  });

  afterEach(async () => {
    for (const [key, value] of [
      ["DASHBOARD_BUILDER_STORE_PATH", originalStorePath],
      ["DASHBOARD_BUILDER_REPO_ROOT", originalRepoRoot],
      ["DASHBOARD_BUILDER_RUNS_ROOT", originalRunsRoot],
      ["DASHBOARD_BUILDER_WORKTREE_ROOT", originalWorktreeRoot],
      ["DASHBOARD_BUILDER_SOURCE_CODEX_HOME", originalSourceCodexHome],
      ["DASHBOARD_BUILDER_EXECUTION_TIMEOUT_MS", originalExecTimeout],
      ["DASHBOARD_BUILDER_TEST_EXECUTION_MODE", originalTestMode],
    ] as const) {
      if (value === undefined) {
        delete env[key];
      } else {
        env[key] = value;
      }
    }

    if (tempDir) {
      await rm(tempDir, { recursive: true, force: true });
      tempDir = "";
    }
  });

  async function waitForTerminalSession(sessionId: string, timeoutMs = 240000) {
    const startedAt = Date.now();
    while (Date.now() - startedAt < timeoutMs) {
      const session = await readBuilderSession(sessionId);
      if (session && ["completed", "failed", "cancelled"].includes(session.status)) {
        return session;
      }
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
    throw new Error(`Timed out waiting for builder session ${sessionId} to finish.`);
  }

  liveIt(
    "completes the live dashboard-targeting Codex route with TSC-backed verification",
    { timeout: 360000 },
    async () => {
      const relativeTargetPath = "projects/dashboard/PROTOCOL_FIRST_BUILDER_KERNEL_FORMAL_EVAL.md";
      const expectedBody = "Builder formal eval succeeded.";
      const session = await createBuilderSession({
        goal: `Create ${relativeTargetPath} in the builder workspace with exactly this single line:
${expectedBody}`,
        task_class: "multi_file_implementation",
        sensitivity_class: "private_but_cloud_allowed",
        workspace_mode: "repo_worktree",
        needs_background: false,
        needs_github: false,
        acceptance_criteria: [
          `Create ${relativeTargetPath} in the workspace.`,
          `Write exactly this line: ${expectedBody}`,
          "Leave the rest of the workspace untouched.",
        ],
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
      const approved = await response.json();
      expect(approved.session?.status).toBe("running");

      const completed = await waitForTerminalSession(session.id);
      const workspaceArtifactPath = completed.latest_result_packet?.artifacts?.find(
        (artifact) => artifact.kind === "workspace" && Boolean(artifact.local_path),
      )?.local_path;
      expect(workspaceArtifactPath).toBeTruthy();
      if (!workspaceArtifactPath) {
        throw new Error("Live builder route did not publish a workspace artifact path.");
      }
      const targetPath = path.join(workspaceArtifactPath, ...relativeTargetPath.split("/"));
      const targetBody = (await readFile(targetPath, "utf8")).trim();
      const targetedValidation = completed.latest_result_packet?.validation?.find(
        (record) => record.id === "targeted_tests_or_build",
      );
      const report = {
        session_id: session.id,
        final_status: completed.status,
        verification_status: completed.verification_state.status,
        resumable_handle: completed.latest_result_packet?.resumable_handle ?? null,
        target_relative_path: relativeTargetPath,
        target_file: targetPath,
        target_body: targetBody,
        files_changed: completed.latest_result_packet?.files_changed ?? [],
        validation: completed.latest_result_packet?.validation ?? [],
        targeted_validation: targetedValidation ?? null,
        remaining_risks: completed.latest_result_packet?.remaining_risks ?? [],
      };
      const outputPath = env.ATHANOR_BUILDER_LIVE_EVAL_OUTPUT?.trim();
      if (outputPath) {
        await mkdir(path.dirname(outputPath), { recursive: true });
        await writeFile(outputPath, `${JSON.stringify(report, null, 2)}
`, "utf8");
      }

      expect(report.final_status).toBe("completed");
      expect(report.verification_status).toBe("passed");
      expect(report.resumable_handle).toBeTruthy();
      expect(report.target_body).toBe(expectedBody);
      expect(report.files_changed).toContain(relativeTargetPath);
      expect(report.files_changed).not.toContain(".codex");
      expect(report.remaining_risks).toEqual([]);
      expect(targetedValidation?.status).toBe("passed");
      expect(targetedValidation?.detail).toContain("Type-check dashboard changes.");
    },
  );
});
