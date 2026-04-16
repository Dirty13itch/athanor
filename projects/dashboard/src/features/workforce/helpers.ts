import type { WorkforceSnapshot, WorkforceTask } from "@/lib/contracts";

export function getTaskLabel(status: WorkforceTask["status"]) {
  switch (status) {
    case "pending_approval":
      return "Needs approval";
    case "running":
      return "Running";
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
    case "cancelled":
      return "Cancelled";
    default:
      return "Queued";
  }
}

export function getProjectName(snapshot: WorkforceSnapshot, projectId: string | null) {
  if (!projectId) {
    return "Unscoped";
  }

  return snapshot.projects.find((project) => project.id === projectId)?.name ?? projectId;
}

export function getAgentName(snapshot: WorkforceSnapshot, agentId: string) {
  return snapshot.agents.find((agent) => agent.id === agentId)?.name ?? agentId;
}

export async function requestJson(path: string, init?: RequestInit) {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }

  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

export async function postJson(path: string, body: Record<string, unknown>) {
  await requestJson(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function postWithoutBody(path: string) {
  await requestJson(path, { method: "POST" });
}

export async function deleteRequest(path: string) {
  await requestJson(path, { method: "DELETE" });
}
