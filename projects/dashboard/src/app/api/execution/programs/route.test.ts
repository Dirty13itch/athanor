import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/executive-kernel", () => ({
  loadExecutionPrograms: vi.fn(async () => [
    {
      id: "daily-digest",
      family: "maintenance",
      source: "scheduled_job",
      title: "Daily Digest",
      cadence: "daily",
      trigger_mode: "scheduler",
      current_state: "running",
      last_outcome: "success",
      owner_agent: "scheduler",
      deep_link: "/runs?job=daily-digest",
      last_run: "2026-04-17T10:00:00.000Z",
      next_run: "2026-04-18T10:00:00.000Z",
      paused: false,
    },
  ]),
}));

import { GET } from "./route";
import { loadExecutionPrograms } from "@/lib/executive-kernel";

describe("execution programs api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("returns family-agnostic execution programs filtered by family", async () => {
    const response = await GET(new NextRequest("http://localhost/api/execution/programs?family=maintenance"));
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(loadExecutionPrograms).toHaveBeenCalledWith({
      status: null,
      family: "maintenance",
    });
    expect(payload).toMatchObject({
      count: 1,
      programs: [
        {
          id: "daily-digest",
          family: "maintenance",
          current_state: "running",
        },
      ],
    });
  });
});
