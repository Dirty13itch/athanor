"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { FeedbackButtons } from "@/components/gen-ui/feedback-buttons";

interface StreamEvent {
  type: "task" | "agent" | "media" | "system";
  source: string;
  title: string;
  detail?: string;
  timestamp: string;
  status?: "completed" | "running" | "failed" | "pending";
  link?: string;
}

function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

function statusDot(status?: string) {
  switch (status) {
    case "completed": return "bg-green-500";
    case "running": return "bg-amber animate-pulse";
    case "failed": return "bg-red-500";
    case "pending": return "bg-muted-foreground/50";
    default: return "bg-muted-foreground/30";
  }
}

function typeIcon(type: StreamEvent["type"]) {
  switch (type) {
    case "task": return TaskIcon;
    case "agent": return AgentIcon;
    case "media": return MediaIcon;
    case "system": return SystemIcon;
  }
}

export function UnifiedStream({ limit = 12, filterTypes }: { limit?: number; filterTypes?: string[] }) {
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    async function fetchEvents() {
      try {
        // Fetch tasks and activity in parallel
        const [tasksRes, activityRes] = await Promise.all([
          fetch("/api/workforce/tasks?limit=20", { signal: AbortSignal.timeout(5000) }).catch(() => null),
          fetch("/api/activity?limit=20", { signal: AbortSignal.timeout(5000) }).catch(() => null),
        ]);

        const merged: StreamEvent[] = [];

        // Parse tasks
        if (tasksRes?.ok) {
          const data = await tasksRes.json();
          const tasks = data.tasks ?? data ?? [];
          for (const t of Array.isArray(tasks) ? tasks : []) {
            // Handle epoch float timestamps (e.g. 1740000000.123)
            const rawTs = t.updated_at ?? t.created_at;
            const timestamp = typeof rawTs === "number"
              ? new Date(rawTs * 1000).toISOString()
              : rawTs ?? new Date().toISOString();
            merged.push({
              type: "task",
              source: t.agent ?? "system",
              title: t.description ?? t.title ?? t.prompt?.substring(0, 60) ?? "Task",
              detail: t.result?.substring(0, 80),
              timestamp,
              status: t.status,
              link: `/tasks`,
            });
          }
        }

        // Parse activity
        if (activityRes?.ok) {
          const data = await activityRes.json();
          const items = data.activity ?? data.items ?? data ?? [];
          for (const a of Array.isArray(items) ? items : []) {
            merged.push({
              type: "agent",
              source: a.agent ?? a.source ?? "system",
              title: a.input_summary ?? a.summary ?? a.action ?? "Activity",
              detail: a.output_summary ?? a.detail,
              timestamp: a.timestamp ?? new Date().toISOString(),
            });
          }
        }

        // Sort by timestamp descending
        merged.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

        // Apply type filter if provided
        const filtered = filterTypes && filterTypes.length > 0
          ? merged.filter((e) => filterTypes.includes(e.type))
          : merged;

        if (mounted) {
          setEvents(filtered.slice(0, limit));
          setLoading(false);
        }
      } catch {
        if (mounted) setLoading(false);
      }
    }

    fetchEvents();
    const interval = setInterval(fetchEvents, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [limit, filterTypes]);

  if (loading) {
    return (
      <div className="space-y-2 py-2">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="h-3 w-3 animate-pulse rounded bg-muted" />
            <div className="h-3 flex-1 animate-pulse rounded bg-muted" />
          </div>
        ))}
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <p className="py-2 text-xs text-muted-foreground">No recent activity.</p>
    );
  }

  return (
    <div className="space-y-1">
      {events.map((event, i) => {
        const Icon = typeIcon(event.type);
        return (
          <div key={i} className="group/stream flex items-start gap-2 py-1 text-xs">
            <div className="relative mt-0.5 shrink-0">
              <Icon className="h-3.5 w-3.5 text-muted-foreground" />
              {event.status && (
                <span className={cn("absolute -right-0.5 -bottom-0.5 h-1.5 w-1.5 rounded-full", statusDot(event.status))} />
              )}
            </div>
            <span className="shrink-0 w-8 font-mono text-muted-foreground">{timeAgo(event.timestamp)}</span>
            <div className="min-w-0 flex-1">
              <span className="font-medium text-foreground/80">{event.source}</span>
              {" "}
              {event.link ? (
                <a href={event.link} className="text-foreground hover:text-primary transition-colors">
                  {event.title}
                </a>
              ) : (
                <span className="text-foreground/70">{event.title}</span>
              )}
              {event.detail && (
                <span className="text-muted-foreground"> — {event.detail}</span>
              )}
            </div>
            <div className="shrink-0 opacity-0 group-hover/stream:opacity-100 transition-opacity">
              <FeedbackButtons
                messageContent={`${event.source}: ${event.title}${event.detail ? ` — ${event.detail}` : ""}`}
                agent={event.source}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Inline icons
function TaskIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="m3 17 2 2 4-4" /><path d="m3 7 2 2 4-4" />
      <path d="M13 6h8" /><path d="M13 12h8" /><path d="M13 18h8" />
    </svg>
  );
}

function AgentIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z" />
    </svg>
  );
}

function MediaIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <rect width="18" height="18" x="3" y="3" rx="2" />
      <path d="M7 3v18" /><path d="M17 3v18" />
      <path d="M3 7.5h4" /><path d="M17 7.5h4" /><path d="M3 12h18" />
      <path d="M3 16.5h4" /><path d="M17 16.5h4" />
    </svg>
  );
}

function SystemIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  );
}
