import { beforeEach, describe, expect, it, vi } from "vitest";
import { getFixtureReviewSnapshot } from "@/lib/dashboard-fixtures";

const { getReviewSnapshot } = vi.hoisted(() => ({
  getReviewSnapshot: vi.fn(),
}));

vi.mock("@/lib/subpage-data", () => ({
  getReviewSnapshot,
}));

import { GET } from "./route";

describe("GET /api/review", () => {
  beforeEach(() => {
    getReviewSnapshot.mockReset();
    getReviewSnapshot.mockResolvedValue(getFixtureReviewSnapshot());
  });

  it("returns the dedicated kernel-backed review snapshot", async () => {
    const fixture = getFixtureReviewSnapshot();
    const response = await GET();
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload.reviewItems.map((item: { id: string }) => item.id)).toEqual(
      fixture.reviewItems.map((item) => item.id),
    );
  });
});
