import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { __resetBuilderStoreForTests, createBuilderSession } from "@/lib/builder-store";
import { GET } from "./route";

describe("GET /api/builder/sessions/[sessionId]/events", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_BUILDER_STORE_PATH;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-builder-events-"));
    env.DASHBOARD_BUILDER_STORE_PATH = path.join(tempDir, "builder-sessions.json");
    await __resetBuilderStoreForTests();
  });

  afterEach(async () => {
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

  it("returns the recorded builder session events", async () => {
    const session = await createBuilderSession({
      goal: "Implement the canonical builder route.",
      task_class: "multi_file_implementation",
      sensitivity_class: "private_but_cloud_allowed",
      workspace_mode: "repo_worktree",
      needs_background: false,
      needs_github: false,
      acceptance_criteria: ["Persist a builder session"],
    });

    const response = await GET(new Request(`http://localhost/api/builder/sessions/${session.id}/events`), {
      params: Promise.resolve({ sessionId: session.id }),
    });

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      session_id: session.id,
      count: 4,
      events: [
        expect.objectContaining({ event_type: "session_created" }),
        expect.objectContaining({ event_type: "route_selected" }),
        expect.objectContaining({ event_type: "verification_planned" }),
        expect.objectContaining({ event_type: "approval_requested" }),
      ],
    });
  });

  it("returns 404 when the builder session is missing", async () => {
    const response = await GET(new Request("http://localhost/api/builder/sessions/missing/events"), {
      params: Promise.resolve({ sessionId: "missing" }),
    });

    expect(response.status).toBe(404);
  });
});
