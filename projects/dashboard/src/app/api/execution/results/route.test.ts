import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { __resetBuilderStoreForTests, createBuilderSession } from "@/lib/builder-store";

vi.mock("@/lib/executive-kernel", () => ({
  loadExecutionResults: vi.fn(async () => []),
}));

import { GET } from "./route";
import { loadExecutionResults } from "@/lib/executive-kernel";

describe("GET /api/execution/results", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_BUILDER_STORE_PATH;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-execution-results-"));
    env.DASHBOARD_BUILDER_STORE_PATH = path.join(tempDir, "builder-sessions.json");
    await __resetBuilderStoreForTests();
    vi.mocked(loadExecutionResults).mockReset();
    vi.mocked(loadExecutionResults).mockImplementation(async () => []);
  });

  afterEach(async () => {
    vi.restoreAllMocks();

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

  it("returns generic execution result projections from builder result packets", async () => {
    const session = await createBuilderSession({
      goal: "Expose builder result packets through the generic execution results route.",
      task_class: "multi_file_implementation",
      sensitivity_class: "private_but_cloud_allowed",
      workspace_mode: "repo_worktree",
      needs_background: false,
      needs_github: false,
      acceptance_criteria: ["Expose generic execution results"],
    });

    vi.mocked(loadExecutionResults).mockResolvedValueOnce([
      {
        id: `builder-result:${session.id}`,
        family: "builder",
        source: "builder_front_door",
        owner_kind: "session",
        owner_id: session.id,
        related_run_id: `builder-run-${session.id}`,
        status: session.status,
        outcome: session.latest_result_packet?.outcome ?? "planned",
        summary: session.latest_result_packet?.summary ?? session.title,
        artifact_count: session.latest_result_packet?.artifacts.length ?? 0,
        artifacts: session.latest_result_packet?.artifacts ?? [],
        files_changed: session.latest_result_packet?.files_changed ?? [],
        validation: session.latest_result_packet?.validation ?? [],
        remaining_risks: session.latest_result_packet?.remaining_risks ?? [],
        resumable_handle: session.latest_result_packet?.resumable_handle ?? null,
        recovery_gate: session.latest_result_packet?.recovery_gate ?? null,
        verification_status: session.verification_state.status,
        updated_at: session.updated_at,
        deep_link: `/builder?session=${encodeURIComponent(session.id)}`,
        metadata: { builder_session_id: session.id },
      },
    ]);

    const response = await GET(
      new NextRequest("http://localhost/api/execution/results?family=builder&outcome=planned"),
    );
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload.count).toBe(1);
    expect(payload.results[0]).toMatchObject({
      id: `builder-result:${session.id}`,
      family: "builder",
      owner_kind: "session",
      owner_id: session.id,
      outcome: "planned",
    });
  });
});
