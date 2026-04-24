import { randomUUID } from "node:crypto";
import { existsSync, createWriteStream, readFileSync } from "node:fs";
import { appendFile, copyFile, mkdir, readFile, rm, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import type {
  BuilderArtifact,
  BuilderExecutionSession,
  BuilderValidationRecord,
  BuilderVerificationState,
} from "@/lib/contracts";
import {
  createBuilderEvent,
  mutateBuilderSession,
  readBuilderSession,
  resolveBuilderStorePath,
} from "@/lib/builder-store";

type BuilderExecutionMode = "start" | "resume";

type ActiveBuilderRun = {
  child: ChildProcessWithoutNullStreams | null;
  timer: NodeJS.Timeout | null;
  runDir: string;
  storePath: string;
  worktreePath: string;
  mode: BuilderExecutionMode;
  cancelRequested: boolean;
};

type CommandResult = {
  ok: boolean;
  code: number | null;
  stdout: string;
  stderr: string;
  durationMs: number;
};

type VerificationOutcome = {
  records: BuilderValidationRecord[];
  completedChecks: string[];
  failedChecks: string[];
  status: BuilderVerificationState["status"];
};

type BuilderOutputEvent = {
  type?: string;
  thread_id?: string;
  item?: {
    id?: string;
    type?: string;
    text?: string;
  };
};

declare global {
  // eslint-disable-next-line no-var
  var __ATHANOR_BUILDER_ACTIVE_RUNS__: Map<string, ActiveBuilderRun> | undefined;
}

const activeRuns = globalThis.__ATHANOR_BUILDER_ACTIVE_RUNS__ ?? new Map<string, ActiveBuilderRun>();
globalThis.__ATHANOR_BUILDER_ACTIVE_RUNS__ = activeRuns;

const DEFAULT_TEST_DELAY_MS = 40;
const DEFAULT_EXECUTION_TIMEOUT_MS = 20 * 60_000;

function resolveRepoRoot(): string {
  const override = process.env.DASHBOARD_BUILDER_REPO_ROOT?.trim();
  if (override) {
    return override;
  }

  const cwd = process.cwd();
  const dashboardPackagePath = path.join(cwd, "package.json");
  const nestedDashboardPath = path.join(cwd, "projects", "dashboard", "package.json");

  if (existsSync(nestedDashboardPath)) {
    return cwd;
  }

  if (existsSync(dashboardPackagePath)) {
    try {
      const pkg = JSON.parse(readFileSync(dashboardPackagePath, "utf8")) as {
        name?: string;
      };
      if (pkg.name === "dashboard") {
        return path.resolve(cwd, "../..");
      }
    } catch {
      return path.resolve(cwd, "../..");
    }
  }

  return cwd;
}

function resolveRunsRoot(repoRoot: string): string {
  return process.env.DASHBOARD_BUILDER_RUNS_ROOT?.trim() || path.join(repoRoot, ".data", "builder-runs");
}

function resolveWorktreeRoot(repoRoot: string): string {
  return (
    process.env.DASHBOARD_BUILDER_WORKTREE_ROOT?.trim() ||
    path.join(path.dirname(repoRoot), `${path.basename(repoRoot)}_worktrees`, "builder")
  );
}

function resolveCodexBin(): string {
  return process.env.DASHBOARD_BUILDER_CODEX_BIN?.trim() || "codex";
}

function resolveSourceCodexHome(): string | null {
  return process.env.DASHBOARD_BUILDER_SOURCE_CODEX_HOME?.trim() || process.env.CODEX_HOME?.trim() || null;
}

function resolveCodexHome(runDir: string): string {
  const override = process.env.DASHBOARD_BUILDER_CODEX_HOME?.trim();
  if (override) {
    return override;
  }

  const sourceHome = resolveSourceCodexHome();
  if (sourceHome) {
    return path.join(sourceHome, "tmp", "builder-homes", path.basename(runDir));
  }

  return path.join(runDir, "codex-home");
}

function resolveExecutionTimeoutMs(): number {
  const raw = process.env.DASHBOARD_BUILDER_EXECUTION_TIMEOUT_MS?.trim();
  const parsed = raw ? Number.parseInt(raw, 10) : NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_EXECUTION_TIMEOUT_MS;
}

function syntheticExecutionMode(): "success" | "failure" | null {
  const mode = process.env.DASHBOARD_BUILDER_TEST_EXECUTION_MODE?.trim();
  return mode === "success" || mode === "failure" ? mode : null;
}

function normalizeText(value: string): string {
  return value.toLowerCase().replace(/\s+/g, " ").trim();
}

function buildPrompt(session: BuilderExecutionSession, worktreePath: string): string {
  const acceptanceCriteria = session.task_envelope.acceptance_criteria.map((criterion) => `- ${criterion}`).join("\n");
  const requiredChecks = session.verification_contract.required_checks.map((check) => `- ${check}`).join("\n");

  return [
    "You are executing the first live Athanor builder kernel route.",
    "Work only inside the provided git workspace and keep the change bounded to the stated goal.",
    "Run the smallest useful validation commands yourself before finishing.",
    "Do not ask for interactive input.",
    "",
    `Workspace: ${worktreePath}`,
    `Goal: ${session.task_envelope.goal}`,
    "",
    "Acceptance Criteria:",
    acceptanceCriteria,
    "",
    "Required Verification Checks:",
    requiredChecks,
    "",
    "Final response format:",
    "Summary:",
    "- One concise summary bullet.",
    "Acceptance Criteria:",
    "- Repeat each criterion exactly once and prefix it with PASS or FAIL.",
    "Validation:",
    "- One bullet per command or verification outcome.",
    "Remaining Risks:",
    "- Enumerate real remaining risks, or write None.",
  ].join("\n");
}

function buildArtifacts(runDir: string, worktreePath: string): BuilderArtifact[] {
  return [
    {
      id: `builder-artifact-${randomUUID()}`,
      label: "Builder prompt",
      kind: "prompt",
      href: null,
      local_path: path.join(runDir, "prompt.md"),
    },
    {
      id: `builder-artifact-${randomUUID()}`,
      label: "Codex JSON events",
      kind: "events_jsonl",
      href: null,
      local_path: path.join(runDir, "codex-events.jsonl"),
    },
    {
      id: `builder-artifact-${randomUUID()}`,
      label: "Codex stderr",
      kind: "stderr_log",
      href: null,
      local_path: path.join(runDir, "codex-stderr.log"),
    },
    {
      id: `builder-artifact-${randomUUID()}`,
      label: "Final response",
      kind: "last_message",
      href: null,
      local_path: path.join(runDir, "last-message.md"),
    },
    {
      id: `builder-artifact-${randomUUID()}`,
      label: "Validation log",
      kind: "validation_log",
      href: null,
      local_path: path.join(runDir, "validation.log"),
    },
    {
      id: `builder-artifact-${randomUUID()}`,
      label: "Workspace path",
      kind: "workspace",
      href: null,
      local_path: worktreePath,
    },
  ];
}

async function ensureDirectory(target: string): Promise<void> {
  await mkdir(target, { recursive: true });
}

async function seedCodexHome(codexHome: string): Promise<void> {
  await ensureDirectory(codexHome);
  await ensureDirectory(path.join(codexHome, "shell_snapshots"));

  const sourceHome = resolveSourceCodexHome();
  if (!sourceHome || path.resolve(sourceHome) === path.resolve(codexHome)) {
    return;
  }

  for (const relativePath of ["auth.json", "config.toml", "installation_id"]) {
    const sourcePath = path.join(sourceHome, relativePath);
    const targetPath = path.join(codexHome, relativePath);
    if (!existsSync(sourcePath) || existsSync(targetPath)) {
      continue;
    }
    await copyFile(sourcePath, targetPath);
  }
}

async function ensureWorkspace(session: BuilderExecutionSession, repoRoot: string): Promise<string> {
  if (session.task_envelope.workspace_mode !== "repo_worktree") {
    return repoRoot;
  }

  const worktreeRoot = resolveWorktreeRoot(repoRoot);
  const worktreePath = path.join(worktreeRoot, session.id);
  if (existsSync(path.join(worktreePath, ".git"))) {
    return worktreePath;
  }

  await ensureDirectory(worktreeRoot);
  const result = await runCommand(
    ["git", "-C", repoRoot, "worktree", "add", "--detach", worktreePath, "HEAD"],
    repoRoot,
    90_000,
  );
  if (!result.ok) {
    throw new Error(`Failed to create builder worktree: ${result.stderr || result.stdout || result.code}`);
  }

  return worktreePath;
}

async function runCommand(command: string[], cwd: string, timeoutMs: number): Promise<CommandResult> {
  const [bin, ...args] = command;
  return new Promise((resolve) => {
    const startedAt = Date.now();
    const child = spawn(bin, args, {
      cwd,
      env: process.env,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    let settled = false;
    const timeout = setTimeout(() => {
      if (settled) {
        return;
      }
      settled = true;
      child.kill("SIGTERM");
      resolve({
        ok: false,
        code: null,
        stdout,
        stderr: stderr ? `${stderr}\nTimed out after ${timeoutMs}ms.` : `Timed out after ${timeoutMs}ms.`,
        durationMs: Date.now() - startedAt,
      });
    }, timeoutMs);

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    child.on("close", (code) => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timeout);
      resolve({
        ok: code === 0,
        code,
        stdout,
        stderr,
        durationMs: Date.now() - startedAt,
      });
    });

    child.on("error", (error) => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timeout);
      resolve({
        ok: false,
        code: null,
        stdout,
        stderr: error.message,
        durationMs: Date.now() - startedAt,
      });
    });
  });
}

async function readOptionalFile(filePath: string): Promise<string> {
  try {
    return await readFile(filePath, "utf8");
  } catch {
    return "";
  }
}

async function writeValidationLog(runDir: string, sections: string[]): Promise<void> {
  await writeFile(path.join(runDir, "validation.log"), `${sections.join("\n\n")}\n`, "utf8");
}

async function appendRunNote(runDir: string, message: string): Promise<void> {
  await appendFile(path.join(runDir, "validation.log"), `${message}\n`, "utf8");
}

async function getChangedFiles(worktreePath: string): Promise<string[]> {
  const result = await runCommand(["git", "-C", worktreePath, "status", "--porcelain", "--untracked-files=all"], worktreePath, 30_000);
  if (!result.stdout.trim()) {
    return [];
  }

  return result.stdout
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter(Boolean)
    .map((line) => {
      const pathPart = line.slice(3).trim();
      const renameParts = pathPart.split(" -> ");
      return renameParts[renameParts.length - 1] ?? pathPart;
    });
}

async function scrubOperationalArtifacts(worktreePath: string, filesChanged: string[]): Promise<string[]> {
  const operationalArtifacts = filesChanged.filter((file) => file === ".codex");
  if (operationalArtifacts.length === 0) {
    return filesChanged;
  }

  for (const relativePath of operationalArtifacts) {
    const tracked = await runCommand(["git", "-C", worktreePath, "ls-files", "--error-unmatch", relativePath], worktreePath, 30_000);
    if (tracked.ok) {
      continue;
    }

    const artifactPath = path.join(worktreePath, relativePath);
    try {
      const details = await stat(artifactPath);
      if (!details.isFile() || details.size !== 0) {
        continue;
      }
      await rm(artifactPath);
    } catch {
      continue;
    }
  }

  return getChangedFiles(worktreePath);
}

function parseSectionBullets(message: string, heading: string): string[] {
  const lines = message.split(/\r?\n/);
  const collected: string[] = [];
  let inSection = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!inSection) {
      if (trimmed.toLowerCase() === heading.toLowerCase()) {
        inSection = true;
      }
      continue;
    }

    if (!trimmed) {
      if (collected.length > 0) {
        break;
      }
      continue;
    }

    if (/^[A-Za-z].*:$/.test(trimmed)) {
      break;
    }

    if (trimmed.startsWith("- ")) {
      collected.push(trimmed.slice(2).trim());
    }
  }

  return collected;
}

function buildSummaryFromMessage(message: string, fallback: string): string {
  const summaryBullets = parseSectionBullets(message, "Summary:");
  if (summaryBullets.length > 0) {
    return summaryBullets.join(" ");
  }

  const firstLine = message
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => Boolean(line) && !/^[A-Za-z].*:$/.test(line));
  return firstLine ?? fallback;
}

function extractRemainingRisks(message: string, validation: BuilderValidationRecord[]): string[] {
  const explicit = parseSectionBullets(message, "Remaining Risks:");
  if (explicit.length > 0 && normalizeText(explicit.join(" ")) !== "none.") {
    return explicit;
  }

  return validation.filter((record) => record.status === "failed").map((record) => record.detail);
}

async function runVerification(
  session: BuilderExecutionSession,
  repoRoot: string,
  worktreePath: string,
  runDir: string,
  filesChanged: string[],
  lastMessage: string,
): Promise<VerificationOutcome> {
  const sections: string[] = [];
  const diffCheck = await runCommand(["git", "-C", worktreePath, "diff", "--check"], worktreePath, 30_000);
  sections.push([
    "$ git diff --check",
    diffCheck.stdout.trim(),
    diffCheck.stderr.trim(),
  ].filter(Boolean).join("\n"));

  let targetedResult: CommandResult | null = null;
  let targetedDetail = "No targeted validation command selected for this change set.";

  if (filesChanged.some((file) => file.startsWith("projects/dashboard/"))) {
    targetedDetail = "Type-check dashboard changes.";
    targetedResult = await runCommand(
      [
        "corepack",
        "pnpm",
        "--dir",
        "projects/dashboard",
        "exec",
        "tsc",
        "--project",
        "tsconfig.typecheck.json",
        "--noEmit",
        "--pretty",
        "false",
      ],
      repoRoot,
      180_000,
    );
  } else {
    const pythonFiles = filesChanged.filter((file) => file.endsWith(".py"));
    if (pythonFiles.length > 0) {
      targetedDetail = "Compile changed Python files.";
      targetedResult = await runCommand(["python3", "-m", "py_compile", ...pythonFiles], worktreePath, 120_000);
    } else if (filesChanged.some((file) => file.startsWith("scripts/") || file.startsWith("config/") || file.startsWith("docs/"))) {
      targetedDetail = "Validate the broader platform contract after control-plane changes.";
      targetedResult = await runCommand(["python3", "scripts/validate_platform_contract.py"], repoRoot, 180_000);
    }
  }

  if (targetedResult) {
    sections.push(
      [
        `$ ${targetedDetail}`,
        targetedResult.stdout.trim(),
        targetedResult.stderr.trim(),
      ]
        .filter(Boolean)
        .join("\n"),
    );
  }

  const normalizedMessage = normalizeText(lastMessage);
  const criteriaMissing = session.task_envelope.acceptance_criteria.filter(
    (criterion) => !normalizedMessage.includes(normalizeText(criterion)),
  );

  const records: BuilderValidationRecord[] = [
    {
      id: "targeted_tests_or_build",
      label: "targeted tests or build",
      status: targetedResult ? (targetedResult.ok ? "passed" : "failed") : "passed",
      detail: targetedResult
        ? targetedResult.ok
          ? `${targetedDetail} Passed in ${(targetedResult.durationMs / 1000).toFixed(1)}s.`
          : `${targetedDetail} Failed: ${targetedResult.stderr || targetedResult.stdout || targetedResult.code}`
        : `${targetedDetail} Diff-only verification path accepted.`,
    },
    {
      id: "diff_review",
      label: "diff review",
      status: filesChanged.length === 0 || !diffCheck.ok ? "failed" : "passed",
      detail:
        filesChanged.length === 0
          ? "No files changed in the builder workspace."
          : diffCheck.ok
            ? `${filesChanged.length} file(s) changed with a clean diff check.`
            : `git diff --check failed: ${diffCheck.stderr || diffCheck.stdout || "unknown diff failure"}`,
    },
    {
      id: "acceptance_criteria_match",
      label: "acceptance criteria match",
      status: criteriaMissing.length === 0 ? "passed" : "failed",
      detail:
        criteriaMissing.length === 0
          ? "Final response covered every acceptance criterion."
          : `Missing criteria evidence for: ${criteriaMissing.join(", ")}`,
    },
  ];

  await writeValidationLog(runDir, sections);

  const failedChecks = records.filter((record) => record.status === "failed").map((record) => record.id);
  return {
    records,
    completedChecks: records.filter((record) => record.status === "passed").map((record) => record.id),
    failedChecks,
    status: failedChecks.length === 0 ? "passed" : "failed",
  };
}

async function finalizeRun(
  sessionId: string,
  run: ActiveBuilderRun,
  exitCode: number | null,
  repoRoot: string,
): Promise<void> {
  if (run.timer) {
    clearTimeout(run.timer);
    run.timer = null;
  }
  const session = await readBuilderSession(sessionId, run.storePath);
  if (!session) {
    activeRuns.delete(sessionId);
    return;
  }

  const lastMessagePath = path.join(run.runDir, "last-message.md");
  const lastMessage = await readOptionalFile(lastMessagePath);
  const filesChanged = await scrubOperationalArtifacts(run.worktreePath, await getChangedFiles(run.worktreePath));
  const artifacts = buildArtifacts(run.runDir, run.worktreePath);

  if (run.cancelRequested) {
    await mutateBuilderSession(sessionId, (draft, events) => {
      draft.status = "cancelled";
      draft.fallback_state = "operator_cancelled";
      draft.shadow_mode = false;
      draft.current_route = draft.route_decision.route_label;
      draft.verification_state = {
        status: "blocked",
        summary: "Builder execution was cancelled before verification completed.",
        completed_checks: [],
        failed_checks: [],
        last_updated_at: new Date().toISOString(),
      };
      draft.latest_result_packet = {
        outcome: "cancelled",
        summary: "Builder execution was cancelled before verification completed.",
        artifacts,
        files_changed: filesChanged,
        validation: [],
        remaining_risks: filesChanged.length > 0 ? ["Workspace contains partial changes after cancellation."] : [],
        resumable_handle: draft.latest_result_packet?.resumable_handle ?? null,
        recovery_gate: "resume_required",
      };
      events.push(
        createBuilderEvent(
          "execution_cancelled",
          "Execution cancelled",
          "Builder execution stopped after an operator cancellation request.",
          "warning",
        ),
      );
    }, run.storePath);
    activeRuns.delete(sessionId);
    return;
  }

  const verification = await runVerification(session, repoRoot, run.worktreePath, run.runDir, filesChanged, lastMessage);
  const failed = exitCode !== 0 || verification.status === "failed";
  const summary = buildSummaryFromMessage(
    lastMessage,
    failed ? "Builder execution finished with validation failures." : "Builder execution completed successfully.",
  );
  const remainingRisks = extractRemainingRisks(lastMessage, verification.records).filter(
    (risk) => !risk.includes("`.codex`") || filesChanged.includes(".codex"),
  );

  await mutateBuilderSession(sessionId, (draft, events) => {
    draft.status = failed ? "failed" : "completed";
    draft.fallback_state = failed ? "verification_failed" : null;
    draft.shadow_mode = false;
    draft.current_worker = draft.route_decision.primary_adapter;
    draft.current_route = draft.route_decision.route_label;
    draft.verification_state = {
      status: verification.status,
      summary: failed
        ? "Execution finished, but verification found blocking failures."
        : "Execution finished and verification passed.",
      completed_checks: verification.completedChecks,
      failed_checks: verification.failedChecks,
      last_updated_at: new Date().toISOString(),
    };
    draft.latest_result_packet = {
      outcome: failed ? "failed" : "succeeded",
      summary,
      artifacts,
      files_changed: filesChanged,
      validation: verification.records,
      remaining_risks: remainingRisks,
      resumable_handle: draft.latest_result_packet?.resumable_handle ?? null,
      recovery_gate: failed ? "resume_available" : null,
    };
    events.push(
      createBuilderEvent(
        "verification_completed",
        failed ? "Verification failed" : "Verification passed",
        draft.verification_state.summary,
        failed ? "danger" : "success",
      ),
    );
    events.push(
      createBuilderEvent(
        "execution_completed",
        failed ? "Execution completed with issues" : "Execution completed",
        failed ? `Codex exit code: ${exitCode ?? "unknown"}.` : "Codex finished and produced a result packet.",
        failed ? "danger" : "success",
      ),
    );
  }, run.storePath);

  activeRuns.delete(sessionId);
}

async function markExecutionRunning(
  sessionId: string,
  runDir: string,
  storePath: string,
  worktreePath: string,
  mode: BuilderExecutionMode,
): Promise<void> {
  await mutateBuilderSession(sessionId, (session, events) => {
    session.status = "running";
    session.shadow_mode = false;
    session.current_worker = session.route_decision.primary_adapter;
    session.current_route = session.route_decision.route_label;
    session.fallback_state = null;
    session.verification_state = {
      status: "running",
      summary: "Codex direct execution is running. Verification will begin after the worker finishes.",
      completed_checks: [],
      failed_checks: [],
      last_updated_at: new Date().toISOString(),
    };
    session.latest_result_packet = {
      outcome: "running",
      summary:
        mode === "resume"
          ? "Resumed live Codex execution in the builder workspace."
          : "Started live Codex execution in the builder workspace.",
      artifacts: buildArtifacts(runDir, worktreePath),
      files_changed: session.latest_result_packet?.files_changed ?? [],
      validation: session.verification_contract.required_checks.map((check) => ({
        id: check,
        label: check.replaceAll("_", " "),
        status: "pending",
        detail: "Waiting for execution to finish before verification runs.",
      })),
      remaining_risks: [],
      resumable_handle: session.latest_result_packet?.resumable_handle ?? null,
      recovery_gate: "in_progress",
    };
    events.push(
      createBuilderEvent(
        mode === "resume" ? "execution_resumed" : "execution_started",
        mode === "resume" ? "Execution resumed" : "Execution started",
        `${session.route_decision.route_label} is running in ${worktreePath}.`,
        "info",
      ),
    );
  }, storePath);
}

async function handleCodexLine(sessionId: string, line: string, storePath: string): Promise<void> {
  if (!line.trim()) {
    return;
  }

  let parsed: BuilderOutputEvent | null = null;
  try {
    parsed = JSON.parse(line) as BuilderOutputEvent;
  } catch {
    return;
  }

  if (parsed?.type === "thread.started" && parsed.thread_id) {
    await mutateBuilderSession(sessionId, (session, events) => {
      if (session.latest_result_packet?.resumable_handle === parsed.thread_id) {
        return;
      }
      session.latest_result_packet = session.latest_result_packet
        ? {
            ...session.latest_result_packet,
            resumable_handle: parsed.thread_id ?? null,
          }
        : {
            outcome: "running",
            summary: "Builder route attached to a live Codex thread.",
            artifacts: [],
            files_changed: [],
            validation: [],
            remaining_risks: [],
            resumable_handle: parsed.thread_id ?? null,
            recovery_gate: "in_progress",
          };
      events.push(
        createBuilderEvent(
          "thread_attached",
          "Resumable handle recorded",
          `Codex thread ${parsed.thread_id} is now attached to this builder session.`,
          "success",
        ),
      );
    }, storePath);
  }
}

async function finalizeSyntheticRun(
  sessionId: string,
  mode: "success" | "failure" | "cancelled",
  run: ActiveBuilderRun,
): Promise<void> {
  const existingSession = await readBuilderSession(sessionId, run.storePath);
  if (!existingSession) {
    activeRuns.delete(sessionId);
    return;
  }

  const artifacts = buildArtifacts(run.runDir, run.worktreePath);
  const syntheticSummary =
    mode === "success"
      ? "Synthetic builder run succeeded."
      : mode === "cancelled"
        ? "Synthetic builder run was cancelled."
        : "Synthetic builder run failed.";
  await writeFile(path.join(run.runDir, "last-message.md"), `Summary:\n- ${syntheticSummary}\n\nAcceptance Criteria:\n- PASS: Synthetic acceptance criterion\n\nValidation:\n- synthetic verification\n\nRemaining Risks:\n- None.\n`, "utf8");
  await writeFile(path.join(run.runDir, "validation.log"), "synthetic verification\n", "utf8");

  await mutateBuilderSession(sessionId, (session, events) => {
    session.status = mode === "success" ? "completed" : mode === "cancelled" ? "cancelled" : "failed";
    session.shadow_mode = false;
    session.fallback_state = mode === "success" ? null : mode === "cancelled" ? "operator_cancelled" : "verification_failed";
    session.verification_state = {
      status: mode === "success" ? "passed" : mode === "cancelled" ? "blocked" : "failed",
      summary:
        mode === "success"
          ? "Synthetic verification passed."
          : mode === "cancelled"
            ? "Synthetic execution was cancelled before verification completed."
            : "Synthetic verification failed.",
      completed_checks: mode === "success" ? session.verification_contract.required_checks : [],
      failed_checks:
        mode === "failure" ? [session.verification_contract.required_checks[0] ?? "synthetic_failure"] : [],
      last_updated_at: new Date().toISOString(),
    };
    session.latest_result_packet = {
      outcome: mode === "success" ? "succeeded" : mode === "cancelled" ? "cancelled" : "failed",
      summary:
        mode === "success"
          ? "Synthetic builder execution succeeded."
          : mode === "cancelled"
            ? "Synthetic builder execution was cancelled."
            : "Synthetic builder execution failed.",
      artifacts,
      files_changed: mode === "success" ? ["projects/dashboard/src/lib/builder-worker-bridge.ts"] : [],
      validation: session.verification_contract.required_checks.map((check) => ({
        id: check,
        label: check.replaceAll("_", " "),
        status: mode === "success" ? "passed" : mode === "cancelled" ? "blocked" : "failed",
        detail:
          mode === "success"
            ? "Synthetic pass."
            : mode === "cancelled"
              ? "Synthetic run was cancelled."
              : "Synthetic failure.",
      })),
      remaining_risks:
        mode === "success"
          ? []
          : mode === "cancelled"
            ? ["Synthetic run was cancelled before verification could finish."]
            : ["Synthetic failure mode enabled for this test run."],
      resumable_handle: session.latest_result_packet?.resumable_handle ?? `synthetic-${session.id}`,
      recovery_gate: mode === "success" ? null : mode === "cancelled" ? "resume_required" : "resume_available",
    };
    events.push(
      createBuilderEvent(
        "execution_completed",
        mode === "success" ? "Execution completed" : mode === "cancelled" ? "Execution cancelled" : "Execution failed",
        mode === "success"
          ? "Synthetic builder execution completed."
          : mode === "cancelled"
            ? "Synthetic builder execution was cancelled."
            : "Synthetic builder execution failed.",
        mode === "success" ? "success" : mode === "cancelled" ? "warning" : "danger",
      ),
    );
  }, run.storePath);

  activeRuns.delete(sessionId);
}

async function launchBuilderExecution(sessionId: string, mode: BuilderExecutionMode): Promise<void> {
  if (activeRuns.has(sessionId)) {
    return;
  }

  const storePath = resolveBuilderStorePath();
  const session = await readBuilderSession(sessionId, storePath);
  if (!session) {
    throw new Error(`Unknown builder session: ${sessionId}`);
  }

  if (session.route_decision.route_id !== "builder:codex:direct_cli" || session.route_decision.activation_state !== "live_ready") {
    throw new Error(`Builder session ${sessionId} is not on the live Codex route.`);
  }

  const repoRoot = resolveRepoRoot();
  const runsRoot = resolveRunsRoot(repoRoot);
  const runDir = path.join(runsRoot, sessionId);
  await ensureDirectory(runDir);
  const syntheticMode = syntheticExecutionMode();
  const worktreePath = syntheticMode
    ? path.join(runDir, "synthetic-workspace")
    : await ensureWorkspace(session, repoRoot);
  if (syntheticMode) {
    await ensureDirectory(worktreePath);
  }
  const prompt = buildPrompt(session, worktreePath);
  await writeFile(path.join(runDir, "prompt.md"), `${prompt}\n`, "utf8");
  await appendFile(path.join(runDir, "codex-events.jsonl"), "", "utf8");
  await appendFile(path.join(runDir, "codex-stderr.log"), "", "utf8");
  const codexHome = resolveCodexHome(runDir);
  await seedCodexHome(codexHome);

  await markExecutionRunning(sessionId, runDir, storePath, worktreePath, mode);

  if (syntheticMode) {
    const activeRun: ActiveBuilderRun = {
      child: null,
      timer: null,
      runDir,
      storePath,
      worktreePath,
      mode,
      cancelRequested: false,
    };
    const timer = setTimeout(() => {
      void finalizeSyntheticRun(sessionId, syntheticMode, activeRuns.get(sessionId) ?? activeRun).catch(() => {
        activeRuns.delete(sessionId);
      });
    }, DEFAULT_TEST_DELAY_MS);
    activeRun.timer = timer;
    activeRuns.set(sessionId, activeRun);
    return;
  }

  const lastMessagePath = path.join(runDir, "last-message.md");
  const args =
    mode === "resume" && session.latest_result_packet?.resumable_handle
      ? [
          "exec",
          "resume",
          "--json",
          "--output-last-message",
          lastMessagePath,
          "--full-auto",
          session.latest_result_packet.resumable_handle,
          "-",
        ]
      : ["exec", "--json", "--output-last-message", lastMessagePath, "--full-auto", "-"];

  const child = spawn(resolveCodexBin(), args, {
    cwd: worktreePath,
    env: {
      ...process.env,
      CODEX_HOME: codexHome,
    },
    stdio: ["pipe", "pipe", "pipe"],
  });

  const activeRun: ActiveBuilderRun = {
    child,
    timer: setTimeout(() => {
      activeRun.cancelRequested = false;
      void appendRunNote(runDir, `Execution timed out after ${resolveExecutionTimeoutMs()}ms.`);
      child.kill("SIGTERM");
    }, resolveExecutionTimeoutMs()),
    runDir,
    storePath,
    worktreePath,
    mode,
    cancelRequested: false,
  };
  activeRuns.set(sessionId, activeRun);

  child.stdin.end(`${prompt}\n`);

  const stdoutStream = createWriteStream(path.join(runDir, "codex-events.jsonl"), { flags: "a" });
  const stderrStream = createWriteStream(path.join(runDir, "codex-stderr.log"), { flags: "a" });
  let buffer = "";
  let lineChain = Promise.resolve();
  let finalized = false;

  const finalizeOnce = async (code: number | null) => {
    if (finalized) {
      return;
    }
    finalized = true;
    if (buffer.trim()) {
      await handleCodexLine(sessionId, buffer.trim(), activeRun.storePath);
      buffer = "";
    }
    await lineChain;
    stdoutStream.end();
    stderrStream.end();
    await finalizeRun(sessionId, activeRun, code, repoRoot);
  };

  child.stdout.on("data", (chunk) => {
    const text = chunk.toString();
    stdoutStream.write(text);
    buffer += text;

    let newlineIndex = buffer.indexOf("\n");
    while (newlineIndex >= 0) {
      const line = buffer.slice(0, newlineIndex).trim();
      buffer = buffer.slice(newlineIndex + 1);
      if (line) {
        lineChain = lineChain.then(() => handleCodexLine(sessionId, line, activeRun.storePath));
      }
      newlineIndex = buffer.indexOf("\n");
    }
  });

  child.stderr.on("data", (chunk) => {
    stderrStream.write(chunk.toString());
  });

  child.on("error", async (error) => {
    stderrStream.write(`${error.message}\n`);
    await finalizeOnce(null);
  });

  child.on("close", async (code) => {
    await finalizeOnce(code);
  });
}

export async function startBuilderExecution(sessionId: string): Promise<void> {
  await launchBuilderExecution(sessionId, "start");
}

export async function resumeBuilderExecution(sessionId: string): Promise<void> {
  const session = await readBuilderSession(sessionId);
  if (!session) {
    throw new Error(`Unknown builder session: ${sessionId}`);
  }
  await launchBuilderExecution(sessionId, session.latest_result_packet?.resumable_handle ? "resume" : "start");
}

export async function cancelBuilderExecution(sessionId: string): Promise<void> {
  const activeRun = activeRuns.get(sessionId);
  if (!activeRun) {
    return;
  }

  activeRun.cancelRequested = true;
  if (activeRun.timer) {
    clearTimeout(activeRun.timer);
    activeRun.timer = null;
    await finalizeSyntheticRun(sessionId, "cancelled", activeRun);
    return;
  }

  activeRun.child?.kill("SIGTERM");
}

export async function collectBuilderResult(sessionId: string): Promise<BuilderExecutionSession | null> {
  return readBuilderSession(sessionId);
}
