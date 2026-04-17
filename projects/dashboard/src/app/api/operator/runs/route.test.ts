import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { NextRequest, NextResponse } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { __resetBuilderStoreForTests, createBuilderSession } from "@/lib/builder-store";

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { GET } from "./route";
import { proxyAgentJson } from "@/lib/server-agent";

describe("operator runs api route", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_BUILDER_STORE_PATH;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-builder-runs-"));
    env.DASHBOARD_BUILDER_STORE_PATH = path.join(tempDir, "builder-sessions.json");
    await __resetBuilderStoreForTests();
  });

  afterEach(() => {
    if (originalPath === undefined) {
      delete env.DASHBOARD_BUILDER_STORE_PATH;
    } else {
      env.DASHBOARD_BUILDER_STORE_PATH = originalPath;
    }
    if (tempDir) {
      void rm(tempDir, { recursive: true, force: true });
      tempDir = "";
    }
    vi.clearAllMocks();
  });

  it("forwards runs GET requests to the canonical operator runs path", async () => {
    const response = await GET(new NextRequest("http://localhost/api/operator/runs?status=running"));

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/runs?status=running",
      undefined,
      "Failed to fetch operator runs"
    );
  });

  it("fails soft when the operator runs upstream is unavailable", async () => {
    vi.mocked(proxyAgentJson).mockResolvedValueOnce(
      NextResponse.json({ error: "upstream down" }, { status: 502 }),
    );

    const response = await GET(new NextRequest("http://localhost/api/operator/runs?status=running"));

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      available: false,
      degraded: true,
      runs: [],
      count: 0,
    });
  });

  it("merges builder sessions into the canonical runs feed", async () => {
    await createBuilderSession({
      goal: "Implement the first builder route.",
      task_class: "multi_file_implementation",
      sensitivity_class: "private_but_cloud_allowed",
      workspace_mode: "repo_worktree",
      needs_background: false,
      needs_github: false,
      acceptance_criteria: ["Persist a builder session"],
    });

    vi.mocked(proxyAgentJson).mockResolvedValueOnce(
      NextResponse.json({ runs: [], count: 0 }, { status: 200 }),
    );

    const response = await GET(new NextRequest("http://localhost/api/operator/runs?status=waiting_approval"));

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      runs: [
        expect.objectContaining({
          id: expect.stringMatching(/^builder-run-/),
          agent_id: "codex",
          status: "waiting_approval",
          approval_pending: true,
        }),
      ],
      count: 1,
    });
  });
});
