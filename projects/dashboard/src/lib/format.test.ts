import { describe, expect, it } from "vitest";
import { average, formatLatency, formatMiB, formatPercent, formatWatts } from "./format";

describe("format helpers", () => {
  it("formats latency across milliseconds and seconds", () => {
    expect(formatLatency(null)).toBe("--");
    expect(formatLatency(245)).toBe("245ms");
    expect(formatLatency(1830)).toBe("1.8s");
  });

  it("formats percentages and numbers safely", () => {
    expect(formatPercent(null)).toBe("--");
    expect(formatPercent(37.4, 1)).toBe("37.4%");
  });

  it("formats MiB and GiB values", () => {
    expect(formatMiB(null)).toBe("--");
    expect(formatMiB(768)).toBe("768 MiB");
    expect(formatMiB(2048)).toBe("2.0 GiB");
  });

  it("formats watts and averages", () => {
    expect(formatWatts(null)).toBe("--");
    expect(formatWatts(287.3)).toBe("287W");
    expect(average([])).toBeNull();
    expect(average([10, 20, 30])).toBe(20);
  });
});
