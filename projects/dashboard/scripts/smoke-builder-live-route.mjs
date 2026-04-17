#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";

const baseUrl = process.env.ATHANOR_DASHBOARD_URL?.trim() || "http://127.0.0.1:3100";
const outputPath = process.env.ATHANOR_BUILDER_SMOKE_OUTPUT?.trim() || "";

function requestHeaders() {
  return {
    "content-type": "application/json",
    origin: baseUrl,
    referer: `${baseUrl}/builder`,
    "x-athanor-request-origin": baseUrl,
  };
}

async function requestJson(url, init = {}) {
  const response = await fetch(url, init);
  const bodyText = await response.text();
  let body;
  try {
    body = bodyText ? JSON.parse(bodyText) : null;
  } catch {
    body = bodyText;
  }

  if (!response.ok) {
    throw new Error(`${init.method || "GET"} ${url} failed: ${response.status} ${JSON.stringify(body)}`);
  }

  return body;
}

async function pollSession(sessionId, timeoutMs = 180_000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const session = await requestJson(`${baseUrl}/api/builder/sessions/${encodeURIComponent(sessionId)}`);
    if (["completed", "failed", "cancelled"].includes(session.status)) {
      return session;
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }

  throw new Error(`Timed out waiting for builder session ${sessionId} to finish.`);
}

async function main() {
  const suffix = new Date().toISOString().replace(/[:.]/g, "-");
  const fileName = `LIVE_SMOKE_${suffix}.md`;
  const createPayload = {
    goal: `Create ${fileName} in the builder workspace root with exactly one sentence: Builder live smoke succeeded.`,
    task_class: "multi_file_implementation",
    sensitivity_class: "private_but_cloud_allowed",
    workspace_mode: "repo_worktree",
    needs_background: false,
    needs_github: false,
    acceptance_criteria: [
      `Create ${fileName} in the workspace root.`,
      "Write the sentence Builder live smoke succeeded.",
      "Leave the rest of the workspace untouched.",
    ],
  };

  const created = await requestJson(`${baseUrl}/api/builder/sessions`, {
    method: "POST",
    headers: requestHeaders(),
    body: JSON.stringify(createPayload),
  });
  const session = created.session;
  const approvalId = session.approvals?.find((entry) => entry.status === "pending")?.id;
  if (!approvalId) {
    throw new Error(`No pending approval found on builder session ${session.id}.`);
  }

  const approved = await requestJson(`${baseUrl}/api/builder/sessions/${encodeURIComponent(session.id)}/control`, {
    method: "POST",
    headers: requestHeaders(),
    body: JSON.stringify({ action: "approve", approval_id: approvalId }),
  });

  const finished = await pollSession(session.id);
  const events = await requestJson(`${baseUrl}/api/builder/sessions/${encodeURIComponent(session.id)}/events`);

  const workspaceArtifact = finished.latest_result_packet?.artifacts?.find((artifact) => artifact.kind === "workspace");
  if (!workspaceArtifact?.local_path) {
    throw new Error(`No workspace artifact path published for builder session ${session.id}.`);
  }

  const targetPath = path.join(workspaceArtifact.local_path, fileName);
  const targetBody = await fs.readFile(targetPath, "utf8");

  const output = {
    baseUrl,
    session_id: session.id,
    initial_status: approved.session?.status ?? null,
    final_status: finished.status,
    verification_status: finished.verification_state?.status ?? null,
    resumable_handle: finished.latest_result_packet?.resumable_handle ?? null,
    workspace_path: workspaceArtifact.local_path,
    target_file: targetPath,
    target_body: targetBody.trim(),
    files_changed: finished.latest_result_packet?.files_changed ?? [],
    validation: finished.latest_result_packet?.validation ?? [],
    remaining_risks: finished.latest_result_packet?.remaining_risks ?? [],
    event_count: events.count,
    event_types: events.events.map((event) => event.event_type),
  };

  if (output.final_status !== "completed" || output.verification_status !== "passed") {
    throw new Error(`Builder live smoke did not pass: ${JSON.stringify(output, null, 2)}`);
  }

  if (output.target_body !== "Builder live smoke succeeded.") {
    throw new Error(`Unexpected target file content: ${output.target_body}`);
  }

  const outputJson = `${JSON.stringify(output, null, 2)}\n`;
  if (outputPath) {
    await fs.mkdir(path.dirname(outputPath), { recursive: true });
    await fs.writeFile(outputPath, outputJson, "utf8");
  }

  process.stdout.write(outputJson);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
