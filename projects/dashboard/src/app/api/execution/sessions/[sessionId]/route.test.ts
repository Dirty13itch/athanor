import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { __resetBuilderStoreForTests, createBuilderSession } from "@/lib/builder-store";
import { GET } from "./route";

describe("GET /api/execution/sessions/[sessionId]", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_BUILDER_STORE_PATH;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-execution-session-"));
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

  it("returns the generic execution session projection for a builder session", async () => {
    const session = await createBuilderSession({
      goal: "Implement the generic execution session detail route.",
      task_class: "multi_file_implementation",
      sensitivity_class: "private_but_cloud_allowed",
      workspace_mode: "repo_worktree",
      needs_background: false,
      needs_github: false,
      acceptance_criteria: ["Return a family-agnostic execution session"],
    });

    const response = await GET(new Request(`http://localhost/api/execution/sessions/${session.id}`), {
      params: Promise.resolve({ sessionId: session.id }),
    });

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      id: session.id,
      family: "builder",
      source: "builder_front_door",
      primary_adapter: "codex",
      status: "waiting_approval",
    });
  });

  it("returns 404 for an unknown execution session", async () => {
    const response = await GET(new Request("http://localhost/api/execution/sessions/missing"), {
      params: Promise.resolve({ sessionId: "missing" }),
    });

    expect(response.status).toBe(404);
  });

  it("returns the generic execution session projection for a bootstrap slice", async () => {
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

    const response = await GET(new Request("http://localhost/api/execution/sessions/persist-04-activation-cutover"), {
      params: Promise.resolve({ sessionId: "persist-04-activation-cutover" }),
    });

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      id: "persist-04-activation-cutover",
      family: "bootstrap_takeover",
      source: "bootstrap_slice",
      status: "waiting_approval",
      current_route: "durable_persistence_activation",
    });
  });
});
