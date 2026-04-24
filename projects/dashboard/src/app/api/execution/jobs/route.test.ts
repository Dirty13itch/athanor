import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { __resetBuilderStoreForTests, createBuilderSession } from "@/lib/builder-store";
import { GET } from "./route";

describe("GET /api/execution/jobs", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_BUILDER_STORE_PATH;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-execution-jobs-"));
    env.DASHBOARD_BUILDER_STORE_PATH = path.join(tempDir, "builder-sessions.json");
    await __resetBuilderStoreForTests();
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

  it("returns generic execution job projections from builder attempts", async () => {
    const session = await createBuilderSession({
      goal: "Project the builder attempt into generic execution jobs.",
      task_class: "multi_file_implementation",
      sensitivity_class: "private_but_cloud_allowed",
      workspace_mode: "repo_worktree",
      needs_background: false,
      needs_github: false,
      acceptance_criteria: ["Expose generic jobs"],
    });

    const response = await GET(new NextRequest("http://localhost/api/execution/jobs?status=waiting_approval"));
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload.count).toBe(1);
    expect(payload.jobs[0]).toMatchObject({
      family: "builder",
      owner_kind: "session",
      owner_id: session.id,
      status: "waiting_approval",
      adapter_id: "codex",
    });
  });

  it("returns generic execution job projections from bootstrap slices", async () => {
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

    const response = await GET(new NextRequest("http://localhost/api/execution/jobs?family=bootstrap_takeover"));
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload.count).toBe(1);
    expect(payload.jobs[0]).toMatchObject({
      id: "persist-04-activation-cutover",
      family: "bootstrap_takeover",
      owner_kind: "program",
      owner_id: "launch-readiness-bootstrap",
      status: "waiting_approval",
      adapter_id: "repo_worktree",
    });
  });
});
