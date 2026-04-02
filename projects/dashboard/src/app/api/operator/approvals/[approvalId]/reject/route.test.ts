import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { POST } from "./route";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

describe("operator approval reject api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards rejection decisions through the operator action proxy", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/operator/approvals/approval-1/reject", {
        method: "POST",
        body: JSON.stringify({ reason: "Rejected from operator review" }),
      }),
      { params: Promise.resolve({ approvalId: "approval-1" }) }
    );

    expect(response.status).toBe(200);
    const [, path, errorMessage, options] = vi.mocked(proxyAgentOperatorJson).mock.calls[0]!;
    expect(path).toBe("/v1/operator/approvals/approval-1/reject");
    expect(errorMessage).toBe("Failed to reject operator approval request");
    expect(options).toMatchObject({
      privilegeClass: "admin",
      defaultReason: "Rejected operator approval approval-1 from dashboard",
    });
    expect(options.bodyOverride).toMatchObject({
      reason: "Rejected from operator review",
    });
  });
});
