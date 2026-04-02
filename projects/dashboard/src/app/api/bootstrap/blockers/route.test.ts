import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { GET } from "./route";
import { proxyAgentJson } from "@/lib/server-agent";

describe("bootstrap blockers api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards GET requests to the blockers path", async () => {
    const request = new Request("http://localhost/api/bootstrap/blockers?family=compatibility_retirement");
    const response = await GET(request as never);

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/bootstrap/blockers?family=compatibility_retirement",
      undefined,
      "Failed to fetch bootstrap blockers"
    );
  });
});
