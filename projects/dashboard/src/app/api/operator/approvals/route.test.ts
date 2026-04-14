import { NextRequest, NextResponse } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { GET } from "./route";
import { proxyAgentJson } from "@/lib/server-agent";

describe("operator approvals api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards approvals GET requests to the canonical operator approvals path", async () => {
    const response = await GET(new NextRequest("http://localhost/api/operator/approvals?status=pending"));

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/approvals?status=pending",
      undefined,
      "Failed to fetch operator approvals"
    );
  });

  it("fails soft when the operator approvals upstream is unavailable", async () => {
    vi.mocked(proxyAgentJson).mockResolvedValueOnce(
      NextResponse.json({ error: "upstream down" }, { status: 502 }),
    );

    const response = await GET(new NextRequest("http://localhost/api/operator/approvals?status=pending"));

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      available: false,
      degraded: true,
      approvals: [],
      count: 0,
    });
  });
});
