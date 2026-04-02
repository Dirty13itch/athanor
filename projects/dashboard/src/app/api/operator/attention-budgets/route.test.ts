import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { GET } from "./route";
import { proxyAgentJson } from "@/lib/server-agent";

describe("operator attention-budgets api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards attention-budget GET requests to the canonical operator path", async () => {
    const response = await GET(new NextRequest("http://localhost/api/operator/attention-budgets?status=active"));

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/attention-budgets?status=active",
      undefined,
      "Failed to fetch operator attention budgets"
    );
  });
});
