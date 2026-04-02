import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { GET } from "./route";
import { proxyAgentJson } from "@/lib/server-agent";

describe("bootstrap handoffs api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards GET requests to the handoffs path", async () => {
    const request = new Request("http://localhost/api/bootstrap/handoffs?slice_id=slice-1");
    const response = await GET(request as never);

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/bootstrap/handoffs?slice_id=slice-1",
      undefined,
      "Failed to fetch bootstrap handoffs"
    );
  });
});
