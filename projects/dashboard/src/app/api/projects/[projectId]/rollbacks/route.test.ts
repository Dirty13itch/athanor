import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { GET } from "./route";
import { proxyAgentJson } from "@/lib/server-agent";

describe("project rollbacks api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards rollback GET requests to the upstream path", async () => {
    const response = await GET(
      new NextRequest("http://localhost/api/projects/athanor/rollbacks?limit=5"),
      { params: Promise.resolve({ projectId: "athanor" }) }
    );

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/projects/athanor/rollbacks?limit=5",
      undefined,
      "Failed to fetch rollback events"
    );
  });
});
