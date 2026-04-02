import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { GET } from "./route";
import { proxyAgentJson } from "@/lib/server-agent";

describe("operator summary api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards summary GET requests to the canonical operator summary path", async () => {
    const response = await GET();

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/summary",
      undefined,
      "Failed to fetch operator work summary"
    );
  });
});
