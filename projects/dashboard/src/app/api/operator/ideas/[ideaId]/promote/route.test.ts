import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { POST } from "./route";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

describe("operator idea promote api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards idea promotion through the operator action proxy", async () => {
    const request = new NextRequest("http://localhost/api/operator/ideas/idea-1/promote", {
      method: "POST",
      body: JSON.stringify({ target: "backlog", owner_agent: "coding-agent" }),
    });

    const response = await POST(request, { params: Promise.resolve({ ideaId: "idea-1" }) });

    expect(response.status).toBe(200);
    const [, path, errorMessage, options] = vi.mocked(proxyAgentOperatorJson).mock.calls[0]!;
    expect(path).toBe("/v1/operator/ideas/idea-1/promote");
    expect(errorMessage).toBe("Failed to promote operator idea");
    expect(options).toMatchObject({ privilegeClass: "operator" });
  });
});
