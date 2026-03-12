"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { FeedbackButtons } from "@/components/gen-ui/feedback-buttons";

interface StreamEvent {
  id: string;
  timestamp: string;
  severity: "info" | "success" | "warning" | "error";
  subsystem: string;
  event_type: string;
  subject: string;
  summary: string;
  deep_link?: string | null;
  related_run_id?: string | null;
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

function severityDot(severity: StreamEvent["severity"]) {
  switch (severity) {
    case "success":
      return "bg-green-500";
    case "warning":
      return "bg-amber-500";
    case "error":
      return "bg-red-500";
    default:
      return "bg-sky-500";
  }
}

function subsystemIcon(subsystem: string) {
  switch (subsystem) {
    case "alerts":
      return AlertIcon;
    case "provider-plane":
      return AgentIcon;
    case "tasks":
      return TaskIcon;
    default:
      return SystemIcon;
  }
}

export function UnifiedStream({ limit = 12 }: { limit?: number; filterTypes?: string[] }) {
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    async function fetchEvents() {
      try {
        const response = await fetch(`/api/activity/operator-stream?limit=${limit}`, {
          signal: AbortSignal.timeout(5000),
        }).catch(() => null);
        const data = response?.ok ? await response.json() : null;
        const nextEvents = Array.isArray(data?.events) ? (data.events as StreamEvent[]) : [];
        if (mounted) {
          setEvents(nextEvents);
          setLoading(false);
        }
      } catch {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    void fetchEvents();
    const interval = setInterval(() => void fetchEvents(), 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [limit]);

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
    return <p className="py-2 text-xs text-muted-foreground">No recent operator events.</p>;
  }

  return (
    <div className="space-y-1">
      {events.map((event) => {
        const Icon = subsystemIcon(event.subsystem);
        return (
          <div key={event.id} className="group/stream flex items-start gap-2 py-1 text-xs">
            <div className="relative mt-0.5 shrink-0">
              <Icon className="h-3.5 w-3.5 text-muted-foreground" />
              <span
                className={cn("absolute -right-0.5 -bottom-0.5 h-1.5 w-1.5 rounded-full", severityDot(event.severity))}
              />
            </div>
            <span className="w-8 shrink-0 font-mono text-muted-foreground">{timeAgo(event.timestamp)}</span>
            <div className="min-w-0 flex-1">
              <span className="font-medium text-foreground/80">{event.subject}</span>{" "}
              {event.deep_link ? (
                <a href={event.deep_link} className="text-foreground hover:text-primary transition-colors">
                  {event.summary}
                </a>
              ) : (
                <span className="text-foreground/70">{event.summary}</span>
              )}
              <span className="text-muted-foreground"> · {event.subsystem}</span>
            </div>
            <div className="shrink-0 opacity-0 transition-opacity group-hover/stream:opacity-100">
              <FeedbackButtons
                messageContent={`${event.subject}: ${event.summary}`}
                agent={event.subject}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

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
      <path d="M12 3v4" /><path d="M8 5h8" /><rect x="5" y="9" width="14" height="10" rx="2" />
      <path d="M9 13h.01" /><path d="M15 13h.01" /><path d="M9 17h6" />
    </svg>
  );
}

function AlertIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <path d="M12 9v4" /><path d="M12 17h.01" />
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
