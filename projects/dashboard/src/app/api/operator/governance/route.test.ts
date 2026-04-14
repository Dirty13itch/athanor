import { NextResponse } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { GET } from "./route";
import { proxyAgentJson } from "@/lib/server-agent";

describe("operator governance api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards governance GET requests to the canonical operator governance path", async () => {
    const response = await GET();

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/governance",
      undefined,
      "Failed to fetch operator governance"
    );
  });

  it("fails soft when the operator governance upstream is unavailable", async () => {
    vi.mocked(proxyAgentJson).mockResolvedValueOnce(
      NextResponse.json({ error: "upstream down" }, { status: 502 }),
    );

    const response = await GET();

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      available: false,
      degraded: true,
      current_mode: { mode: "feed_unavailable" },
      launch_blockers: ["operator_upstream_unavailable"],
    });
  });
});
