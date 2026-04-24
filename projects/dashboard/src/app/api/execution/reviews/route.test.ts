import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { __resetBuilderStoreForTests, createBuilderSession } from "@/lib/builder-store";

vi.mock("@/lib/executive-kernel", () => ({
  loadExecutionReviews: vi.fn(async () => []),
}));

import { GET } from "./route";
import { loadExecutionReviews } from "@/lib/executive-kernel";

describe("GET /api/execution/reviews", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_BUILDER_STORE_PATH;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-execution-reviews-"));
    env.DASHBOARD_BUILDER_STORE_PATH = path.join(tempDir, "builder-sessions.json");
    await __resetBuilderStoreForTests();
    vi.mocked(loadExecutionReviews).mockReset();
    vi.mocked(loadExecutionReviews).mockImplementation(async () => []);
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

  it("returns generic execution review projections from builder approvals", async () => {
    const session = await createBuilderSession({
      goal: "Project the builder approval into generic execution reviews.",
      task_class: "multi_file_implementation",
      sensitivity_class: "private_but_cloud_allowed",
      workspace_mode: "repo_worktree",
      needs_background: false,
      needs_github: false,
      acceptance_criteria: ["Expose generic execution reviews"],
    });

    vi.mocked(loadExecutionReviews).mockResolvedValueOnce([
      {
        id: session.approvals[0]!.id,
        family: "builder",
        source: "builder_front_door",
        owner_kind: "session",
        owner_id: session.id,
        related_run_id: `builder-run-${session.id}`,
        related_task_id: session.id,
        requested_action: session.approvals[0]!.requested_action,
        privilege_class: "admin",
        reason: session.approvals[0]!.reason,
        status: "pending",
        requested_at: Date.now() / 1000,
        task_prompt: session.task_envelope.goal,
        task_agent_id: "codex",
        task_priority: "normal",
        task_status: session.status,
        deep_link: `/builder?session=${encodeURIComponent(session.id)}`,
        metadata: { builder_session_id: session.id },
      },
    ]);

    const response = await GET(new NextRequest("http://localhost/api/execution/reviews?status=pending"));
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload.count).toBe(1);
    expect(payload.reviews[0]).toMatchObject({
      id: session.approvals[0]?.id,
      family: "builder",
      owner_kind: "session",
      owner_id: session.id,
      status: "pending",
      requested_action: session.approvals[0]?.requested_action,
    });
  });

  it("returns generic execution review projections from bootstrap approval contexts", async () => {
    vi.mocked(loadExecutionReviews).mockResolvedValueOnce([
      {
        id: "bootstrap-approval:launch-readiness-bootstrap:persist-04-activation-cutover:db_schema_change",
        family: "bootstrap_takeover",
        source: "bootstrap_program",
        owner_kind: "program",
        owner_id: "launch-readiness-bootstrap",
        related_run_id: "bootstrap-program:launch-readiness-bootstrap",
        related_task_id: "persist-04-activation-cutover",
        requested_action: "approve",
        privilege_class: "admin",
        reason: "Authorize the durable persistence schema and runtime cutover maintenance window.",
        status: "pending",
        requested_at: Date.now() / 1000,
        task_prompt: "Drive the external builder lane to takeover readiness.",
        task_agent_id: "durable_persistence_activation",
        task_priority: "high",
        task_status: "waiting_approval",
        deep_link: "/bootstrap?program=launch-readiness-bootstrap&slice=persist-04-activation-cutover",
        metadata: {
          bootstrap_program_id: "launch-readiness-bootstrap",
          bootstrap_slice_id: "persist-04-activation-cutover",
          packet_id: "db_schema_change",
        },
      },
    ]);

    const response = await GET(new NextRequest("http://localhost/api/execution/reviews?family=bootstrap_takeover"));
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload.count).toBe(1);
    expect(payload.reviews[0]).toMatchObject({
      id: "bootstrap-approval:launch-readiness-bootstrap:persist-04-activation-cutover:db_schema_change",
      family: "bootstrap_takeover",
      owner_kind: "program",
      owner_id: "launch-readiness-bootstrap",
      status: "pending",
      requested_action: "approve",
    });
  });
});
