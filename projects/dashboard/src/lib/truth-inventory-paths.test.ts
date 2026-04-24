import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { candidateTruthInventoryPaths } from "./truth-inventory-paths";

const originalCwd = process.cwd();
const originalTruthInventoryDir = process.env.ATHANOR_TRUTH_INVENTORY_DIR;

afterEach(() => {
  process.chdir(originalCwd);
  if (originalTruthInventoryDir === undefined) {
    delete process.env.ATHANOR_TRUTH_INVENTORY_DIR;
  } else {
    process.env.ATHANOR_TRUTH_INVENTORY_DIR = originalTruthInventoryDir;
  }
});

describe("candidateTruthInventoryPaths", () => {
  it("prefers the configured truth-inventory dir when provided", () => {
    process.env.ATHANOR_TRUTH_INVENTORY_DIR = "/opt/athanor/reports/truth-inventory";
    process.chdir(mkdtempSync(path.join(tmpdir(), "athanor-truth-paths-")));

    const candidates = candidateTruthInventoryPaths("operator-mobile-summary.json");

    expect(candidates[0]).toEqual({
      kind: "configured_truth_inventory",
      path: "/opt/athanor/reports/truth-inventory/operator-mobile-summary.json",
    });
  });

  it("deduplicates repeated fallback paths", () => {
    delete process.env.ATHANOR_TRUTH_INVENTORY_DIR;
    process.chdir(path.parse(originalCwd).root);

    const candidates = candidateTruthInventoryPaths("operator-mobile-summary.json");
    const uniquePaths = new Set(candidates.map((candidate) => candidate.path));

    expect(candidates).toHaveLength(uniquePaths.size);
  });
});
