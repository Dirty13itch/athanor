import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { POST } from "./route";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

describe("bootstrap nudge api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards POST requests to the canonical bootstrap nudge path", async () => {
    const request = new Request("http://localhost/api/bootstrap/programs/launch-readiness-bootstrap/nudge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ execute: true, project_id: "athanor", owner_agent: "coding-agent" }),
    });

    const response = await POST(request as never, {
      params: Promise.resolve({ programId: "launch-readiness-bootstrap" }),
    });

    expect(response.status).toBe(200);
    expect(proxyAgentOperatorJson).toHaveBeenCalledWith(
      request,
      "/v1/bootstrap/programs/launch-readiness-bootstrap/nudge",
      "Failed to nudge bootstrap program",
      expect.objectContaining({
        privilegeClass: "admin",
        defaultReason: "Nudged bootstrap supervisor from dashboard",
        bodyOverride: expect.objectContaining({
          execute: true,
          retry_blockers: true,
          process_integrations: true,
          materialize_backlog: true,
          project_id: "athanor",
          owner_agent: "coding-agent",
        }),
      })
    );
  });
});
