import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi
    .fn()
    .mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { GET, POST } from "./route";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { proxyAgentJson } from "@/lib/server-agent";

describe("governor operator-tests api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards GET requests to the canonical operator-tests path", async () => {
    const response = await GET();

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/governor/operator-tests",
      undefined,
      "Failed to fetch operator-test snapshot"
    );
  });

  it("forwards POST requests through the shared operator envelope and preserves pilot flow ids", async () => {
    const request = new NextRequest("http://localhost/api/governor/operator-tests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        actor: "dashboard-operator",
        session_id: "sess-1",
        correlation_id: "corr-1",
        reason: "Manual pilot run",
        flow_ids: [
          "goose_operator_shell",
          "openhands_bounded_worker",
          "letta_memory_plane",
          "agt_policy_plane",
        ],
      }),
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    expect(proxyAgentOperatorJson).toHaveBeenCalledWith(
      request,
      "/v1/governor/operator-tests/run",
      "Failed to run synthetic operator tests",
      {
        privilegeClass: "admin",
        defaultReason: "Manual operator test run from dashboard",
      }
    );
  });
});
