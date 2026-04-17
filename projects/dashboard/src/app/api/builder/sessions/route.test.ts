import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { __resetBuilderStoreForTests } from "@/lib/builder-store";
import { POST } from "./route";

describe("POST /api/builder/sessions", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_BUILDER_STORE_PATH;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-builder-route-"));
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

  it("creates a builder session from a task envelope", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/builder/sessions", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          goal: "Implement the first builder route.",
          task_class: "multi_file_implementation",
          sensitivity_class: "private_but_cloud_allowed",
          workspace_mode: "repo_worktree",
          needs_background: false,
          needs_github: false,
          acceptance_criteria: ["Persist a builder session"],
        }),
      }),
    );

    expect(response.status).toBe(201);
    await expect(response.json()).resolves.toMatchObject({
      ok: true,
      session: {
        route_decision: {
          primary_adapter: "codex",
          execution_mode: "direct_cli",
        },
        status: "waiting_approval",
      },
    });
  });
});
