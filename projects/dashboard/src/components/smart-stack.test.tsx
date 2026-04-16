import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SmartStack } from "./smart-stack";

vi.mock("@/lib/operator-session", () => ({
  useOperatorSessionStatus: () => ({ locked: false }),
  isOperatorSessionLocked: () => false,
}));

describe("SmartStack", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders task residue from canonical operator task stats", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
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
          by_status: {
            completed: 138,
            failed: 153,
            pending_approval: 13,
            stale_lease: 21,
          },
        },
        patterns: {
          patterns: [],
          recommendations: [],
        },
      }),
    } as Response);

    render(<SmartStack />);

    await waitFor(() => {
      expect(screen.getByText("13 approval-held tasks")).toBeInTheDocument();
    });
    expect(screen.getByText("72 actionable failures")).toBeInTheDocument();
    expect(screen.getByText("21 stale leases")).toBeInTheDocument();
    expect(screen.getByText("81 repaired historical")).toBeInTheDocument();
  });
});
