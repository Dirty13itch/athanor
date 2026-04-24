import { NextRequest, NextResponse } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

vi.mock("@/lib/builder-store", () => ({
  listBuilderSyntheticTodos: vi.fn(async (status?: string | null) =>
    status && status !== "open"
      ? []
      : [
          {
            id: "builder-todo-1",
            title: "Follow up builder route",
            description: "Operator follow-up generated from builder inbox.",
            category: "approval",
            scope_type: "builder_session",
            scope_id: "builder-1",
            priority: 4,
            status: "open",
            energy_class: "focused",
            created_at: 200,
            updated_at: 200,
            completed_at: 0,
            metadata: { builder_session_id: "builder-1" },
          },
        ]),
}));

import { GET, POST } from "./route";
import { listBuilderSyntheticTodos } from "@/lib/builder-store";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { proxyAgentJson } from "@/lib/server-agent";

describe("operator todos api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards todos GET requests to the operator todos upstream path", async () => {
    vi.mocked(proxyAgentJson).mockResolvedValueOnce(
      NextResponse.json({ todos: [{ id: "agent-todo-1", status: "ready", updated_at: 150 }], count: 1 }, {
        status: 200,
      }),
    );
    const response = await GET(new NextRequest("http://localhost/api/operator/todos?status=ready"));
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/todos?status=ready",
      undefined,
      "Failed to fetch operator todos"
    );
    expect(listBuilderSyntheticTodos).toHaveBeenCalledWith("ready");
    expect(payload.count).toBe(1);
  });

  it("forwards todo POST requests through the operator action proxy", async () => {
    const request = new NextRequest("http://localhost/api/operator/todos", {
      method: "POST",
      body: JSON.stringify({
        title: "Follow up",
        description: "Capture detail",
      }),
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    expect(proxyAgentOperatorJson).toHaveBeenCalledOnce();
    const [, path, errorMessage, options] = vi.mocked(proxyAgentOperatorJson).mock.calls[0]!;
    expect(path).toBe("/v1/operator/todos");
    expect(errorMessage).toBe("Failed to create operator todo");
    expect(options).toMatchObject({
      privilegeClass: "operator",
      defaultReason: "Created operator todo from dashboard",
    });
  });
});
