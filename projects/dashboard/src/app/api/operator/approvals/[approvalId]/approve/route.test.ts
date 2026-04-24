import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { __resetBuilderStoreForTests, createBuilderSession, readBuilderSession } from "@/lib/builder-store";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { POST } from "./route";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

async function waitForBuilderSessionStatus(sessionId: string, status: string) {
  const deadline = Date.now() + 2_000;
  let current = await readBuilderSession(sessionId);
  while (current?.status !== status && Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 25));
    current = await readBuilderSession(sessionId);
  }
  return current;
}

describe("operator approval approve api route", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_BUILDER_STORE_PATH;
  const originalRepoRoot = env.DASHBOARD_BUILDER_REPO_ROOT;
  const originalTestMode = env.DASHBOARD_BUILDER_TEST_EXECUTION_MODE;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-operator-approval-"));
    env.DASHBOARD_BUILDER_STORE_PATH = path.join(tempDir, "builder-sessions.json");
    env.DASHBOARD_BUILDER_REPO_ROOT = "/mnt/c/Athanor";
    env.DASHBOARD_BUILDER_TEST_EXECUTION_MODE = "success";
    await __resetBuilderStoreForTests();
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

  it("forwards approval decisions through the operator action proxy", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/operator/approvals/approval-1/approve", {
        method: "POST",
        headers: { origin: "http://localhost" },
      }),
      { params: Promise.resolve({ approvalId: "approval-1" }) }
    );

    expect(response.status).toBe(200);
    const [, path, errorMessage, options] = vi.mocked(proxyAgentOperatorJson).mock.calls[0]!;
    expect(path).toBe("/v1/operator/approvals/approval-1/approve");
    expect(errorMessage).toBe("Failed to approve operator approval request");
    expect(options).toMatchObject({
      privilegeClass: "admin",
      defaultReason: "Approved operator approval approval-1 from dashboard",
    });
    expect(options.bodyOverride).toMatchObject({
      reason: "Approved operator approval approval-1 from dashboard",
    });
  });

  it("approves builder synthetic approvals locally", async () => {
    const session = await createBuilderSession({
      goal: "Approve a builder session from the operator approval surface.",
      task_class: "multi_file_implementation",
      sensitivity_class: "private_but_cloud_allowed",
      workspace_mode: "repo_worktree",
      needs_background: false,
      needs_github: false,
      acceptance_criteria: ["Operator approval route should bridge locally"],
    });
    const approvalId = session.approvals[0]?.id;
    expect(approvalId).toBeTruthy();

    const response = await POST(
      new NextRequest(`http://localhost/api/operator/approvals/${approvalId}/approve`, {
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
        status: "running",
      },
    });
    await expect(waitForBuilderSessionStatus(session.id, "completed")).resolves.toMatchObject({
      status: "completed",
    });
    expect(proxyAgentOperatorJson).not.toHaveBeenCalled();
  });

  it("approves bootstrap synthetic approvals locally", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);

      if (url.includes("/api/bootstrap/programs/launch-readiness-bootstrap/approve")) {
        return new Response(JSON.stringify({ status: "approved" }), { status: 200 });
      }

      if (url.includes("/v1/bootstrap/slices?limit=500")) {
        return new Response(
          JSON.stringify({
            slices: [
              {
                id: "persist-04-activation-cutover",
                program_id: "launch-readiness-bootstrap",
                family: "durable_persistence_activation",
                objective: "Cut configured Postgres runtimes over from fallback memory to durable persistence.",
                status: "queued",
                host_id: "",
                current_ref: "",
                worktree_path: "",
                files_touched: [],
                validation_status: "pending",
                open_risks: [],
                next_step: "Approval landed; continue the durable cutover lane.",
                stop_reason: "",
                resume_instructions: "",
                depth_level: 2,
                priority: 2,
                phase_scope: "software_core_phase_1",
                continuation_mode: "external_bootstrap",
                metadata: {},
                catalog_slice_id: "persist-04",
                family_seed_slice_id: "persist-seed",
                execution_mode: "repo_worktree",
                completion_evidence_paths: [],
                blocking_packet_id: "",
                claimed_at: "",
                completed_at: "",
                created_at: "2026-04-16T20:00:00.000Z",
                updated_at: "2026-04-17T23:20:00.000Z",
              },
            ],
            count: 1,
          }),
          { status: 200 },
        );
      }

      return new Response("not found", { status: 404 });
    });

    const approvalId =
      "bootstrap-approval:launch-readiness-bootstrap:persist-04-activation-cutover:db_schema_change";

    const response = await POST(
      new NextRequest(`http://localhost/api/operator/approvals/${approvalId}/approve`, {
        method: "POST",
        headers: { origin: "http://localhost" },
      }),
      { params: Promise.resolve({ approvalId }) }
    );

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      ok: true,
      approval_id: approvalId,
      session: {
        id: "persist-04-activation-cutover",
        family: "bootstrap_takeover",
        status: "queued",
      },
    });
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe(
      "http://localhost/api/bootstrap/programs/launch-readiness-bootstrap/approve",
    );
    expect(fetchMock.mock.calls[0]?.[1]).toEqual(expect.objectContaining({ method: "POST" }));
    expect(proxyAgentOperatorJson).not.toHaveBeenCalled();
  });
});
