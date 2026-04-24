import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/executive-kernel", () => ({
  loadExecutionSessions: vi.fn(async () => [
    {
      id: "builder-1",
      family: "builder",
      source: "builder_front_door",
      title: "Implement the bounded Codex route",
      status: "waiting_approval",
      primary_adapter: "codex",
      current_route: "Codex direct implementation",
      verification_status: "planned",
      pending_approval_count: 1,
      artifact_count: 3,
      resumable_handle: null,
      shadow_mode: false,
      fallback_state: "approval_pending",
      updated_at: "2026-04-17T23:10:00.000Z",
    },
  ]),
}));

import { GET } from "./route";
import { loadExecutionSessions } from "@/lib/executive-kernel";

describe("execution sessions api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("returns family-agnostic execution sessions filtered by status", async () => {
    const response = await GET(new NextRequest("http://localhost/api/execution/sessions?status=waiting_approval"));
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(loadExecutionSessions).toHaveBeenCalledWith({
      status: "waiting_approval",
      family: null,
    });
    expect(payload).toMatchObject({
      count: 1,
      sessions: [
        {
          id: "builder-1",
          family: "builder",
          status: "waiting_approval",
        },
      ],
    });
  });
});
