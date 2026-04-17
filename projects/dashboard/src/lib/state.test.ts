import { describe, expect, it } from "vitest";
import { shouldPersistComparisonKey } from "./state";

describe("state persistence helpers", () => {
  it("persists when the comparison key changes", () => {
    expect(
      shouldPersistComparisonKey(
        { comparisonKey: "front-door|no-action|cheap-bulk-cloud" },
        { comparisonKey: "front-door|needs-shaun|letta-memory-plane" },
      ),
    ).toBe(true);
  });

  it("does not persist when the comparison key is unchanged or missing", () => {
    expect(
      shouldPersistComparisonKey(
        { comparisonKey: "front-door|no-action|cheap-bulk-cloud" },
        { comparisonKey: "front-door|no-action|cheap-bulk-cloud" },
      ),
    ).toBe(false);
    expect(shouldPersistComparisonKey({ comparisonKey: "front-door" }, null)).toBe(false);
  });
});
