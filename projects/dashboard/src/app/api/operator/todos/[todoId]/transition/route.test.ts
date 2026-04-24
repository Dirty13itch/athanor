import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

vi.mock("@/lib/builder-store", () => ({
  isBuilderSyntheticTodoId: vi.fn((id: string) => id.startsWith("builder-todo-")),
  applyBuilderSyntheticTodoTransition: vi.fn(async (id: string, status: string, note?: string) => ({
    id,
    status,
    note,
  })),
}));

import { POST } from "./route";
import { applyBuilderSyntheticTodoTransition } from "@/lib/builder-store";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

describe("operator todo transition route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("transitions local builder todos without proxying upstream", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/operator/todos/builder-todo-1/transition", {
        method: "POST",
        body: JSON.stringify({
          status: "done",
          note: "Handled locally.",
        }),
      }),
      { params: Promise.resolve({ todoId: "builder-todo-1" }) },
    );

    await expect(response.json()).resolves.toMatchObject({
      ok: true,
      todo: {
        id: "builder-todo-1",
        status: "done",
      },
    });
    expect(applyBuilderSyntheticTodoTransition).toHaveBeenCalledWith("builder-todo-1", "done", "Handled locally.");
    expect(proxyAgentOperatorJson).not.toHaveBeenCalled();
  });

  it("proxies non-builder todo transitions upstream", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/operator/todos/agent-todo-1/transition", {
        method: "POST",
        body: JSON.stringify({
          status: "done",
        }),
      }),
      { params: Promise.resolve({ todoId: "agent-todo-1" }) },
    );

    expect(response.status).toBe(200);
    expect(proxyAgentOperatorJson).toHaveBeenCalledOnce();
  });
});
