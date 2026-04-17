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

import { GET } from "./route";
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
      steadyStateStatus: {
        degraded: true,
      },
    });
  });
});
