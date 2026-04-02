import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { POST } from "./route";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

describe("project rollback api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards rollback requests through the operator action proxy", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/projects/athanor/rollback", {
        method: "POST",
        body: JSON.stringify({ candidate_id: "candidate-1" }),
      }),
      { params: Promise.resolve({ projectId: "athanor" }) }
    );

    expect(response.status).toBe(200);
    const [, path, errorMessage, options] = vi.mocked(proxyAgentOperatorJson).mock.calls[0]!;
    expect(path).toBe("/v1/projects/athanor/rollback");
    expect(errorMessage).toBe("Failed to roll back deploy candidate");
    expect(options).toMatchObject({
      privilegeClass: "destructive-admin",
      defaultReason: "Rolled back deploy candidate for athanor from dashboard",
    });
    expect(options.bodyOverride).toMatchObject({
      candidate_id: "candidate-1",
      protected_mode: true,
      reason: "Rolled back deploy candidate for athanor from dashboard",
    });
  });
});
