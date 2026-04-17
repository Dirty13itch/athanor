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

describe("operator approvals api route", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalPath = env.DASHBOARD_BUILDER_STORE_PATH;
  let tempDir = "";

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-builder-approvals-"));
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

  it("forwards approvals GET requests to the canonical operator approvals path", async () => {
    const response = await GET(new NextRequest("http://localhost/api/operator/approvals?status=pending"));

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/approvals?status=pending",
      undefined,
      "Failed to fetch operator approvals"
    );
  });

  it("fails soft when the operator approvals upstream is unavailable", async () => {
    vi.mocked(proxyAgentJson).mockResolvedValueOnce(
      NextResponse.json({ error: "upstream down" }, { status: 502 }),
    );

    const response = await GET(new NextRequest("http://localhost/api/operator/approvals?status=pending"));

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      available: false,
      degraded: true,
      approvals: [],
      count: 0,
    });
  });

  it("merges builder approvals into the canonical approvals feed", async () => {
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
      NextResponse.json({ approvals: [], count: 0 }, { status: 200 }),
    );

    const response = await GET(new NextRequest("http://localhost/api/operator/approvals?status=pending"));

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      approvals: [
        expect.objectContaining({
          id: expect.stringMatching(/^builder-approval-/),
          task_agent_id: "codex",
          status: "pending",
        }),
      ],
      count: 1,
    });
  });
});
