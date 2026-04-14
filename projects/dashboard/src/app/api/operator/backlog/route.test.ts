import { NextRequest, NextResponse } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { GET } from "./route";
import { proxyAgentJson } from "@/lib/server-agent";

describe("operator backlog api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards backlog GET requests to the canonical operator backlog path", async () => {
    const response = await GET(new NextRequest("http://localhost/api/operator/backlog?status=ready"));

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/backlog?status=ready",
      undefined,
      "Failed to fetch operator backlog"
    );
  });

  it("normalizes status=all so the upstream backlog path stays unfiltered", async () => {
    const response = await GET(
      new NextRequest("http://localhost/api/operator/backlog?status=all&limit=120"),
    );

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/backlog?limit=120",
      undefined,
      "Failed to fetch operator backlog"
    );
  });

  it("fails soft when the operator backlog upstream is unavailable", async () => {
    vi.mocked(proxyAgentJson).mockResolvedValueOnce(
      NextResponse.json({ error: "upstream down" }, { status: 502 }),
    );

    const response = await GET(new NextRequest("http://localhost/api/operator/backlog?status=ready"));

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      available: false,
      degraded: true,
      backlog: [],
      count: 0,
    });
  });
});
