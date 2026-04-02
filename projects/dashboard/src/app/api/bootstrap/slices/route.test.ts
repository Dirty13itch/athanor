import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { GET } from "./route";
import { proxyAgentJson } from "@/lib/server-agent";

describe("bootstrap slices api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards GET requests and preserves query parameters", async () => {
    const request = new Request("http://localhost/api/bootstrap/slices?status=claimed&host_id=codex_external");
    const response = await GET(request as never);

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/bootstrap/slices?status=claimed&host_id=codex_external",
      undefined,
      "Failed to fetch bootstrap slices"
    );
  });
});
