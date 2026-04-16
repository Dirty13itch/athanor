import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const dashboardRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(dashboardRoot, "..", "..");
const inventoryDir = path.join(repoRoot, "reports", "completion-audit", "latest", "inventory");
const requiredArtifacts = [
  "dashboard-api-census.json",
  "dashboard-route-census.json",
  "dashboard-component-census.json",
  "dashboard-mount-graph.json",
  "dashboard-support-surface-census.json",
];
const censusScripts = [
  "scripts/census-dashboard-routes.py",
  "scripts/census-dashboard-api.py",
  "scripts/census-dashboard-components.py",
  "scripts/find-mounted-ui.py",
];

function resolvePythonCommand() {
  const candidates =
    process.platform === "win32"
      ? [
          ["py", ["-3"]],
          ["python", []],
        ]
      : [
          ["python3", []],
          ["python", []],
        ];

  for (const [command, prefixArgs] of candidates) {
    const probe = spawnSync(command, [...prefixArgs, "--version"], {
      cwd: repoRoot,
      encoding: "utf-8",
      stdio: "pipe",
    });
    if (probe.status === 0) {
      return { command, prefixArgs };
    }
  }
  throw new Error("Unable to find a Python runtime for completion-audit inventory generation.");
}

function runChecked(command, args) {
  const result = spawnSync(command, args, {
    cwd: repoRoot,
    encoding: "utf-8",
    stdio: "pipe",
    env: process.env,
  });
  if (result.status !== 0) {
    throw new Error(
      [
        `Command failed: ${[command, ...args].join(" ")}`,
        result.stdout?.trim() ? `stdout:\n${result.stdout.trim()}` : "",
        result.stderr?.trim() ? `stderr:\n${result.stderr.trim()}` : "",
      ]
        .filter(Boolean)
        .join("\n\n"),
    );
  }
}

const { command, prefixArgs } = resolvePythonCommand();

for (const script of censusScripts) {
  runChecked(command, [...prefixArgs, path.join(repoRoot, script)]);
}

const missingArtifacts = requiredArtifacts.filter(
  (artifact) => !existsSync(path.join(inventoryDir, artifact)),
);

if (missingArtifacts.length > 0) {
  throw new Error(
    `Completion-audit inventory generation did not produce required artifacts: ${missingArtifacts.join(", ")}`,
  );
}
