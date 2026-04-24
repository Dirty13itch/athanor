import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { __resetBuilderStoreForTests, createBuilderSession } from "@/lib/builder-store";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true, proxied: true }), { status: 200 })),
}));

import { POST } from "./route";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

describe("POST /api/execution/reviews/[reviewId]/reject", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_BUILDER_STORE_PATH;
  const originalRepoRoot = env.DASHBOARD_BUILDER_REPO_ROOT;
  const originalTestMode = env.DASHBOARD_BUILDER_TEST_EXECUTION_MODE;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-execution-review-reject-"));
    env.DASHBOARD_BUILDER_STORE_PATH = path.join(tempDir, "builder-sessions.json");
    env.DASHBOARD_BUILDER_REPO_ROOT = "/mnt/c/Athanor";
    env.DASHBOARD_BUILDER_TEST_EXECUTION_MODE = "success";
    await __resetBuilderStoreForTests();
    vi.mocked(proxyAgentOperatorJson).mockClear();
  });

  afterEach(async () => {
    vi.restoreAllMocks();

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

  it("rejects builder execution reviews locally", async () => {
    const session = await createBuilderSession({
      goal: "Reject a builder session from the execution review surface.",
      task_class: "multi_file_implementation",
      sensitivity_class: "private_but_cloud_allowed",
      workspace_mode: "repo_worktree",
      needs_background: false,
      needs_github: false,
      acceptance_criteria: ["Execution review reject should bridge locally"],
    });
    const reviewId = session.approvals[0]?.id;
    expect(reviewId).toBeTruthy();

    const response = await POST(
      new NextRequest(`http://localhost/api/execution/reviews/${reviewId}/reject`, {
        method: "POST",
        headers: { origin: "http://localhost" },
      }),
      { params: Promise.resolve({ reviewId: String(reviewId) }) },
    );

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      ok: true,
      review_id: reviewId,
      session: {
        id: session.id,
        family: "builder",
        status: "cancelled",
      },
    });
  });

  it("fails closed for bootstrap execution review rejection", async () => {
    const reviewId =
      "bootstrap-approval:launch-readiness-bootstrap:persist-04-activation-cutover:db_schema_change";

    const response = await POST(
      new NextRequest(`http://localhost/api/execution/reviews/${reviewId}/reject`, {
        method: "POST",
        headers: { origin: "http://localhost" },
      }),
      { params: Promise.resolve({ reviewId }) },
    );

    expect(response.status).toBe(409);
    await expect(response.json()).resolves.toMatchObject({
      review_id: reviewId,
      error: "Bootstrap synthetic reviews do not yet support reject through the shared execution review path.",
    });
  });

  it("forwards operator-backed rejection ids through the canonical operator approval path", async () => {
    const reviewId = "approval:task-123";

    const response = await POST(
      new NextRequest(`http://localhost/api/execution/reviews/${encodeURIComponent(reviewId)}/reject`, {
        method: "POST",
        headers: { origin: "http://localhost" },
      }),
      { params: Promise.resolve({ reviewId }) },
    );

    expect(response.status).toBe(200);
    expect(proxyAgentOperatorJson).toHaveBeenCalledWith(
      expect.anything(),
      "/v1/operator/approvals/approval%3Atask-123/reject",
      "Failed to reject operator approval request",
      expect.objectContaining({
        privilegeClass: "admin",
        defaultReason: "Rejected operator approval approval:task-123 from shared execution reviews",
        bodyOverride: {
          reason: "Rejected operator approval approval:task-123 from shared execution reviews",
        },
      }),
    );
  });

  it("returns not found for unknown execution reviews", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/execution/reviews/review-unknown/reject", {
        method: "POST",
        headers: { origin: "http://localhost" },
      }),
      { params: Promise.resolve({ reviewId: "review-unknown" }) },
    );

    expect(response.status).toBe(404);
    await expect(response.json()).resolves.toMatchObject({
      error: "Execution review not found",
    });
  });
});
