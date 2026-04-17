import { NextResponse } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

vi.mock("@/lib/operator-frontdoor", () => ({
  loadSteadyStateFrontDoor: vi.fn(async () => ({
    snapshot: null,
    status: {
      available: false,
      degraded: true,
      detail: "Steady-state front door unavailable.",
      sourceKind: null,
      sourcePath: null,
    },
  })),
}));

vi.mock("@/lib/builder-store", () => ({
  readBuilderSummary: vi.fn(async () => ({
    available: true,
    degraded: false,
    detail: null,
    updated_at: "2026-04-17T00:00:00.000Z",
    session_count: 1,
    active_count: 1,
    pending_approval_count: 1,
    recent_artifact_count: 0,
    current_session: {
      id: "builder-1",
      title: "Implement the first builder route",
      status: "waiting_approval",
      primary_adapter: "codex",
      current_route: "Codex direct implementation",
      verification_status: "planned",
      pending_approval_count: 1,
      artifact_count: 0,
      resumable_handle: null,
      shadow_mode: false,
      fallback_state: "approval_pending",
      updated_at: "2026-04-17T00:00:00.000Z",
    },
    sessions: [],
  })),
}));

import { GET } from "./route";
import { readBuilderSummary } from "@/lib/builder-store";
import { loadSteadyStateFrontDoor } from "@/lib/operator-frontdoor";
import { proxyAgentJson } from "@/lib/server-agent";

describe("operator summary api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards summary GET requests to the canonical operator summary path", async () => {
    const response = await GET();

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/summary",
      undefined,
      "Failed to fetch operator work summary",
      25_000,
    );
    expect(loadSteadyStateFrontDoor).toHaveBeenCalled();
    expect(readBuilderSummary).toHaveBeenCalled();
  });

  it("fails soft when the operator summary upstream is unavailable", async () => {
    vi.mocked(proxyAgentJson).mockResolvedValueOnce(
      NextResponse.json({ error: "upstream down" }, { status: 502 }),
    );

    const response = await GET();

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      available: false,
      degraded: true,
      tasks: {
        pending_approval: 0,
        failed_actionable: 0,
      },
      builderFrontDoor: {
        pending_approval_count: 1,
      },
      steadyStateStatus: {
        degraded: true,
      },
    });
  });
});
