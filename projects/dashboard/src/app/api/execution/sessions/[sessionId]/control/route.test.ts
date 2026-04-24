import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { __resetBuilderStoreForTests, createBuilderSession, readBuilderSession } from "@/lib/builder-store";
import { POST } from "./route";

async function waitForBuilderSessionStatus(sessionId: string, status: string) {
  const deadline = Date.now() + 2_000;
  let current = await readBuilderSession(sessionId);
  while (current?.status !== status && Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 25));
    current = await readBuilderSession(sessionId);
  }
  return current;
}

describe("POST /api/execution/sessions/[sessionId]/control", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_BUILDER_STORE_PATH;
  const originalRepoRoot = env.DASHBOARD_BUILDER_REPO_ROOT;
  const originalTestMode = env.DASHBOARD_BUILDER_TEST_EXECUTION_MODE;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-execution-control-"));
    env.DASHBOARD_BUILDER_STORE_PATH = path.join(tempDir, "builder-sessions.json");
    env.DASHBOARD_BUILDER_REPO_ROOT = "/mnt/c/Athanor";
    env.DASHBOARD_BUILDER_TEST_EXECUTION_MODE = "success";
    await __resetBuilderStoreForTests();
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

  it("controls a builder session through the generic execution control route", async () => {
    const session = await createBuilderSession({
      goal: "Approve the builder route through generic execution control.",
      task_class: "multi_file_implementation",
      sensitivity_class: "private_but_cloud_allowed",
      workspace_mode: "repo_worktree",
      needs_background: false,
      needs_github: false,
      acceptance_criteria: ["Expose generic session control"],
    });

    const approvalId = session.approvals[0]?.id;
    expect(approvalId).toBeTruthy();

    const response = await POST(
      new NextRequest(`http://localhost/api/execution/sessions/${session.id}/control`, {
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
        family: "builder",
        status: "running",
      },
    });

    const completed = await waitForBuilderSessionStatus(session.id, "completed");
    expect(completed?.status).toBe("completed");
    expect(completed?.latest_result_packet?.outcome).toBe("succeeded");
  });

  it("returns a conflict for non-builder execution sessions that exist but do not support generic control yet", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/v1/bootstrap/slices?limit=500")) {
        return new Response(
          JSON.stringify({
            slices: [
              {
                id: "persist-04-activation-cutover",
                program_id: "launch-readiness-bootstrap",
                family: "durable_persistence_activation",
                objective: "Cut configured Postgres runtimes over from fallback memory to durable persistence.",
                status: "waiting_approval",
                host_id: "",
                current_ref: "",
                worktree_path: "",
                files_touched: [],
                validation_status: "pending",
                open_risks: [],
                next_step: "Await DB schema/runtime approval packet execution.",
                stop_reason: "",
                resume_instructions: "",
                depth_level: 2,
                priority: 2,
                phase_scope: "software_core_phase_1",
                continuation_mode: "external_bootstrap",
                metadata: { blocking_packet_id: "db_schema_change" },
                catalog_slice_id: "persist-04",
                family_seed_slice_id: "persist-seed",
                execution_mode: "repo_worktree",
                completion_evidence_paths: [],
                blocking_packet_id: "db_schema_change",
                claimed_at: "",
                completed_at: "",
                created_at: "2026-04-16T20:00:00.000Z",
                updated_at: "2026-04-17T23:15:00.000Z",
              },
            ],
            count: 1,
          }),
          { status: 200 },
        );
      }

      return new Response("not found", { status: 404 });
    });

    const response = await POST(
      new NextRequest("http://localhost/api/execution/sessions/persist-04-activation-cutover/control", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ action: "cancel" }),
      }),
      { params: Promise.resolve({ sessionId: "persist-04-activation-cutover" }) },
    );

    expect(response.status).toBe(409);
    await expect(response.json()).resolves.toMatchObject({
      error: "Execution control is not yet available for bootstrap_takeover sessions",
    });
  });

  it("bridges generic approve control to the bootstrap program approval path", async () => {
    let bootstrapApproved = false;
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);

      if (url.includes("/v1/bootstrap/slices?limit=500")) {
        return new Response(
          JSON.stringify({
            slices: [
              {
                id: "persist-04-activation-cutover",
                program_id: "launch-readiness-bootstrap",
                family: "durable_persistence_activation",
                objective: "Cut configured Postgres runtimes over from fallback memory to durable persistence.",
                status: bootstrapApproved ? "queued" : "waiting_approval",
                host_id: "",
                current_ref: "",
                worktree_path: "C:\\Athanor_worktrees\\durable_persistence_activation\\persist-04-activation-cutover",
                files_touched: [],
                validation_status: "pending",
                open_risks: [],
                next_step: "Await DB schema/runtime approval packet execution.",
                stop_reason: "",
                resume_instructions: "",
                depth_level: 2,
                priority: 2,
                phase_scope: "software_core_phase_1",
                continuation_mode: "external_bootstrap",
                metadata: bootstrapApproved ? {} : { blocking_packet_id: "db_schema_change" },
                catalog_slice_id: "persist-04",
                family_seed_slice_id: "persist-seed",
                execution_mode: "repo_worktree",
                completion_evidence_paths: [],
                blocking_packet_id: bootstrapApproved ? "" : "db_schema_change",
                claimed_at: "",
                completed_at: "",
                created_at: "2026-04-16T20:00:00.000Z",
                updated_at: bootstrapApproved ? "2026-04-17T23:20:00.000Z" : "2026-04-17T23:15:00.000Z",
              },
            ],
            count: 1,
          }),
          { status: 200 },
        );
      }

      if (url.includes("/api/bootstrap/slices?limit=500")) {
        return new Response(
          JSON.stringify({
            slices: [
              {
                id: "persist-04-activation-cutover",
                program_id: "launch-readiness-bootstrap",
                metadata: { blocking_packet_id: "db_schema_change" },
                blocking_packet_id: "db_schema_change",
              },
            ],
          }),
          { status: 200 },
        );
      }

      if (url.includes("/api/bootstrap/programs/launch-readiness-bootstrap/approve")) {
        bootstrapApproved = true;
        return new Response(
          JSON.stringify({
            status: "approved",
            approved_packet_id: "db_schema_change",
          }),
          { status: 200 },
        );
      }

      return new Response("not found", { status: 404 });
    });

    const response = await POST(
      new NextRequest("http://localhost/api/execution/sessions/persist-04-activation-cutover/control", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ action: "approve" }),
      }),
      { params: Promise.resolve({ sessionId: "persist-04-activation-cutover" }) },
    );

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      ok: true,
      session: {
        id: "persist-04-activation-cutover",
        family: "bootstrap_takeover",
        status: "queued",
      },
    });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/bootstrap/programs/launch-readiness-bootstrap/approve"),
      expect.objectContaining({
        method: "POST",
      }),
    );
  });
});
