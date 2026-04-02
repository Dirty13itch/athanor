import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { POST } from "./route";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

describe("project promote api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards promote requests through the operator action proxy", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/projects/athanor/promote", {
        method: "POST",
        body: JSON.stringify({ candidate_id: "candidate-1", channel: "public_staging" }),
      }),
      { params: Promise.resolve({ projectId: "athanor" }) }
    );

    expect(response.status).toBe(200);
    const [, path, errorMessage, options] = vi.mocked(proxyAgentOperatorJson).mock.calls[0]!;
    expect(path).toBe("/v1/projects/athanor/promote");
    expect(errorMessage).toBe("Failed to promote deploy candidate");
    expect(options).toMatchObject({
      privilegeClass: "admin",
      defaultReason: "Promoted deploy candidate for athanor from dashboard",
    });
  });
});
