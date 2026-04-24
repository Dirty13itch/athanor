import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { NextRequest, NextResponse } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { __resetBuilderStoreForTests, createBuilderSession } from "@/lib/builder-store";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => NextResponse.json({ ok: true }, { status: 200 })),
}));

import { POST } from "./route";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

describe("operator approval reject api route", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_BUILDER_STORE_PATH;
  const originalRepoRoot = env.DASHBOARD_BUILDER_REPO_ROOT;
  const originalTestMode = env.DASHBOARD_BUILDER_TEST_EXECUTION_MODE;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-operator-reject-"));
    env.DASHBOARD_BUILDER_STORE_PATH = path.join(tempDir, "builder-sessions.json");
    env.DASHBOARD_BUILDER_REPO_ROOT = "/mnt/c/Athanor";
    env.DASHBOARD_BUILDER_TEST_EXECUTION_MODE = "success";
    await __resetBuilderStoreForTests();
    vi.mocked(proxyAgentOperatorJson).mockReset();
    vi.mocked(proxyAgentOperatorJson).mockImplementation(async () => NextResponse.json({ ok: true }, { status: 200 }));
  });

  afterEach(() => {
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
      void rm(tempDir, { recursive: true, force: true });
      tempDir = "";
    }
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it("forwards rejection decisions through the operator action proxy", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/operator/approvals/approval-1/reject", {
        method: "POST",
        headers: { origin: "http://localhost" },
        body: JSON.stringify({ reason: "Rejected from operator review" }),
      }),
      { params: Promise.resolve({ approvalId: "approval-1" }) }
    );

    expect(response.status).toBe(200);
    const [, path, errorMessage, options] = vi.mocked(proxyAgentOperatorJson).mock.calls[0]!;
    expect(path).toBe("/v1/operator/approvals/approval-1/reject");
    expect(errorMessage).toBe("Failed to reject operator approval request");
    expect(options).toMatchObject({
      privilegeClass: "admin",
      defaultReason: "Rejected operator approval approval-1 from dashboard",
    });
    expect(options.bodyOverride).toMatchObject({
      reason: "Rejected from operator review",
    });
  });

  it("rejects builder synthetic approvals locally", async () => {
    const session = await createBuilderSession({
      goal: "Reject a builder session from the operator approval surface.",
      task_class: "multi_file_implementation",
      sensitivity_class: "private_but_cloud_allowed",
      workspace_mode: "repo_worktree",
      needs_background: false,
      needs_github: false,
      acceptance_criteria: ["Operator rejection route should bridge locally"],
    });
    const approvalId = session.approvals[0]?.id;
    expect(approvalId).toBeTruthy();

    const response = await POST(
      new NextRequest(`http://localhost/api/operator/approvals/${approvalId}/reject`, {
        method: "POST",
        headers: { origin: "http://localhost" },
      }),
      { params: Promise.resolve({ approvalId: String(approvalId) }) }
    );

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      ok: true,
      approval_id: approvalId,
      session: {
        id: session.id,
        family: "builder",
        status: "cancelled",
      },
    });
    expect(proxyAgentOperatorJson).not.toHaveBeenCalled();
  });

  it("fails closed for bootstrap synthetic approval rejection", async () => {
    const approvalId =
      "bootstrap-approval:launch-readiness-bootstrap:persist-04-activation-cutover:db_schema_change";

    const response = await POST(
      new NextRequest(`http://localhost/api/operator/approvals/${approvalId}/reject`, {
        method: "POST",
        headers: { origin: "http://localhost" },
      }),
      { params: Promise.resolve({ approvalId }) }
    );

    expect(response.status).toBe(409);
    await expect(response.json()).resolves.toMatchObject({
      approval_id: approvalId,
      error: "Bootstrap synthetic reviews do not yet support reject through the shared execution review path.",
    });
    expect(proxyAgentOperatorJson).not.toHaveBeenCalled();
  });
});
