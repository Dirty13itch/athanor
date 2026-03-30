import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { GET } from "./route";

describe("GET /api/digests/latest", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalFixtureMode = env.DASHBOARD_FIXTURE_MODE;

  beforeEach(() => {
    env.DASHBOARD_FIXTURE_MODE = "1";
  });

  afterEach(() => {
    if (originalFixtureMode === undefined) {
      delete env.DASHBOARD_FIXTURE_MODE;
    } else {
      env.DASHBOARD_FIXTURE_MODE = originalFixtureMode;
    }
  });

  it("returns the fixture-backed latest digest", async () => {
    const response = await GET();

    expect(response.status).toBe(200);
    const payload = await response.json();
    expect(payload).toMatchObject({
      type: "auto",
      generated_at: expect.any(String),
      period: "24h",
      task_count: expect.any(Number),
      completed_count: expect.any(Number),
      failed_count: expect.any(Number),
      recent_completions: expect.any(Array),
      recent_failures: expect.any(Array),
    });
  });
});
