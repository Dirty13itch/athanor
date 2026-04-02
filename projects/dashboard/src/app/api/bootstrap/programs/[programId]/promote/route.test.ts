import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { POST } from "./route";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

describe("bootstrap program promote api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards POST requests to the bootstrap promote path", async () => {
    const response = await POST(
      new Request("http://localhost/api/bootstrap/programs/launch-readiness-bootstrap/promote", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ reason: "Promote internal builder", force: true }),
      }) as never,
      {
        params: Promise.resolve({ programId: "launch-readiness-bootstrap" }),
      }
    );

    expect(response.status).toBe(200);
    expect(proxyAgentOperatorJson).toHaveBeenCalledWith(
      expect.any(Request),
      "/v1/bootstrap/programs/launch-readiness-bootstrap/promote",
      "Failed to promote bootstrap program",
      expect.objectContaining({
        privilegeClass: "admin",
      })
    );
  });
});
