import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { GET } from "./route";
import { proxyAgentJson } from "@/lib/server-agent";

describe("operator runs api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards runs GET requests to the operator runs upstream path", async () => {
    const response = await GET(new NextRequest("http://localhost/api/operator/runs?status=running"));

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/runs?status=running",
      undefined,
      "Failed to fetch operator runs"
    );
  });
});
