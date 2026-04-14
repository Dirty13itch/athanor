import { NextRequest, NextResponse } from "next/server";
import { agentServerHeaders, config, joinUrl } from "@/lib/config";

function resolveRequestUrl(request: NextRequest | Request): URL {
  if ("nextUrl" in request && request.nextUrl instanceof URL) {
    return request.nextUrl;
  }

  return new URL(request.url);
}

export async function GET(request: NextRequest | Request) {
  const requestUrl = resolveRequestUrl(request);
  const limit = Math.max(
    Number.parseInt(requestUrl.searchParams.get("limit") ?? "12", 10) || 12,
    1
  );

  try {
    const response = await fetch(
      joinUrl(config.agentServer.url, `/v1/events/query?limit=${encodeURIComponent(String(limit))}`),
      {
        headers: agentServerHeaders(),
        signal: AbortSignal.timeout(5_000),
      }
    );

    if (!response.ok) {
      return NextResponse.json({ events: [] });
    }

    const text = await response.text();
    const payload = text ? (JSON.parse(text) as { events?: Array<Record<string, unknown>> }) : {};
    const events = Array.isArray(payload.events) ? payload.events : [];

    const normalized = events.map((event, index) => {
      const eventType = typeof event.event_type === "string" ? event.event_type : "event";
      const subject = typeof event.agent === "string" && event.agent.trim() ? event.agent : "system";
      const data = typeof event.data === "object" && event.data !== null ? (event.data as Record<string, unknown>) : {};
      const severity =
        eventType === "task_failed"
          ? "error"
          : eventType === "escalation_triggered"
            ? "warning"
            : eventType === "task_completed"
              ? "success"
              : "info";
      const subsystem =
        eventType.startsWith("task_")
          ? "tasks"
          : eventType.startsWith("schedule_")
            ? "agents"
            : eventType.includes("alert")
              ? "alerts"
              : typeof data.source === "string" && data.source.includes("provider")
                ? "provider-plane"
                : "system";
      const taskId = typeof data.task_id === "string" ? data.task_id : null;
      const summary =
        typeof event.description === "string" && event.description.trim()
          ? event.description
          : `Operator event: ${eventType.replace(/_/g, " ")}`;

      return {
        id:
          (typeof taskId === "string" && taskId) ||
          `${eventType}-${subject}-${typeof event.timestamp_unix === "number" ? event.timestamp_unix : index}`,
        timestamp: typeof event.timestamp === "string" ? event.timestamp : null,
        severity,
        subsystem,
        event_type: eventType,
        subject,
        summary,
        deep_link: taskId ? "/operator" : subsystem === "alerts" ? "/routing" : "/governor",
        related_run_id: typeof data.run_id === "string" ? data.run_id : null,
      };
    });

    return NextResponse.json({ events: normalized });
  } catch {
    return NextResponse.json({ events: [] });
  }
}
