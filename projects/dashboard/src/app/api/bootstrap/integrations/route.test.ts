import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { GET } from "./route";
import { proxyAgentJson } from "@/lib/server-agent";

describe("bootstrap integrations api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards GET requests to the bootstrap integrations path", async () => {
    const response = await GET(new Request("http://localhost/api/bootstrap/integrations?status=queued"));

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/bootstrap/integrations?status=queued",
      undefined,
      "Failed to fetch bootstrap integrations"
    );
  });
});
