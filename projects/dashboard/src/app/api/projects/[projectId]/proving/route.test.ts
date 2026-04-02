import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { POST } from "./route";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

describe("project proving api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards proving POST requests through the operator action proxy", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/projects/athanor/proving", {
        method: "POST",
        body: JSON.stringify({ stage: "slice_execution" }),
      }),
      { params: Promise.resolve({ projectId: "athanor" }) }
    );

    expect(response.status).toBe(200);
    const [, path, errorMessage, options] = vi.mocked(proxyAgentOperatorJson).mock.calls[0]!;
    expect(path).toBe("/v1/projects/athanor/proving");
    expect(errorMessage).toBe("Failed to materialize project proving stage");
    expect(options).toMatchObject({
      privilegeClass: "admin",
      defaultReason: "Materialized proving stage for athanor from dashboard",
    });
  });
});
