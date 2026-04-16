import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DailyDigest } from "./daily-digest";

describe("DailyDigest", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders canonical task residue instead of run failure totals", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        runs: {
          by_status: {
            completed: 999,
            failed: 999,
            running: 999,
          },
        },
        tasks: {
          total: 332,
          completed: 138,
          failed: 153,
          running: 0,
          pending: 0,
          pending_approval: 13,
          stale_lease: 21,
          failed_actionable: 72,
          failed_historical_repaired: 81,
          failed_missing_detail: 0,
        },
        approvals: {
          by_status: {
            pending: 13,
          },
        },
      }),
    } as Response);

    render(<DailyDigest />);

    await waitFor(() => {
      expect(screen.getByText("138 completed")).toBeInTheDocument();
    });
    expect(screen.getByText("72 actionable failures")).toBeInTheDocument();
    expect(screen.getByText("13 pending approvals")).toBeInTheDocument();
    expect(screen.getByText("21 stale leases")).toBeInTheDocument();
    expect(screen.queryByText("999 failed")).not.toBeInTheDocument();
  });
});
