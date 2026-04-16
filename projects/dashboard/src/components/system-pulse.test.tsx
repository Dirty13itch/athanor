import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SystemPulse } from "./system-pulse";

vi.mock("@/hooks/use-lens", () => ({
  useLens: () => ({
    config: {
      accentHue: 65,
    },
  }),
}));

vi.mock("@/hooks/use-system-stream", () => ({
  useSystemStream: () => ({
    connected: true,
    data: {
      gpus: [],
      agents: { online: true, count: 9, names: ["coding-agent"] },
      services: { up: 6, total: 6, down: [] },
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
        currently_running: 0,
        worker_running: false,
        by_status: {
          completed: 138,
          running: 0,
          failed: 153,
          pending: 0,
          pending_approval: 13,
          stale_lease: 21,
        },
      },
      media: null,
      timestamp: "2026-04-03T00:00:00.000Z",
    },
  }),
}));

describe("SystemPulse", () => {
  it("surfaces canonical task residue signals", () => {
    render(<SystemPulse />);

    expect(screen.getByText("13 approval-held, 21 stale, 72 actionable")).toBeInTheDocument();
  });
});
