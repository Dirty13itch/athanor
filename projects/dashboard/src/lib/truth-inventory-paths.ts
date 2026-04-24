import path from "node:path";

export type TruthInventorySourceKind = "configured_truth_inventory" | "workspace_report" | "repo_root_fallback";

export interface TruthInventoryCandidatePath<K extends string = TruthInventorySourceKind> {
  kind: K;
  path: string;
}

function resolveConfiguredTruthInventoryPath(configuredDir: string, fileName: string): string {
  if (configuredDir.startsWith("/")) {
    return `${configuredDir.replace(/\/+$/, "")}/${fileName}`;
  }
  return path.resolve(configuredDir, fileName);
}

export function candidateTruthInventoryPaths(
  fileName: string,
): TruthInventoryCandidatePath<TruthInventorySourceKind>[] {
  const cwd = process.cwd();
  const candidates: TruthInventoryCandidatePath<TruthInventorySourceKind>[] = [];
  const configuredTruthInventoryDir = process.env.ATHANOR_TRUTH_INVENTORY_DIR?.trim();

  if (configuredTruthInventoryDir) {
    candidates.push({
      kind: "configured_truth_inventory",
      path: resolveConfiguredTruthInventoryPath(configuredTruthInventoryDir, fileName),
    });
  }

  candidates.push(
    {
      kind: "workspace_report",
      path: path.resolve(cwd, "reports", "truth-inventory", fileName),
    },
    {
      kind: "repo_root_fallback",
      path: path.resolve(cwd, "..", "reports", "truth-inventory", fileName),
    },
    {
      kind: "repo_root_fallback",
      path: path.resolve(cwd, "..", "..", "reports", "truth-inventory", fileName),
    },
  );

  const seen = new Set<string>();
  return candidates.filter((candidate) => {
    if (seen.has(candidate.path)) {
      return false;
    }
    seen.add(candidate.path);
    return true;
  });
}
