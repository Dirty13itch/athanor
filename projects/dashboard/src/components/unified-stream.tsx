"use client";

import { useEffect, useState } from "react";
import { FeedbackButtons } from "@/components/gen-ui/feedback-buttons";
import { cn } from "@/lib/utils";

interface StreamEvent {
  type: "tasks" | "agents" | "alerts" | "provider-plane" | "system";
  source: string;
  title: string;
  detail?: string;
  timestamp: string;
  severity?: "success" | "warning" | "error" | "info";
  link?: string;
}

function normalizeTimestamp(value: string | number | null | undefined): string {
  if (typeof value === "number") {
    return new Date(value * 1000).toISOString();
  }

  if (typeof value === "string" && value.trim().length > 0) {
    return value;
  }

  return new Date().toISOString();
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

function severityDot(severity?: StreamEvent["severity"]) {
  switch (severity) {
    case "success":
      return "bg-[color:var(--signal-success)]";
    case "warning":
      return "bg-[color:var(--signal-warning)] animate-pulse";
    case "error":
      return "bg-[color:var(--signal-danger)]";
    case "info":
    default:
      return "bg-[color:var(--signal-info)]";
  }
}

function typeIcon(type: StreamEvent["type"]) {
  switch (type) {
    case "tasks":
      return TaskIcon;
    case "agents":
      return AgentIcon;
    case "provider-plane":
      return MediaIcon;
    case "alerts":
    case "system":
      return SystemIcon;
  }
}

const FILTER_OPTIONS = [
  { label: "All", value: null },
  { label: "Tasks", value: "tasks" },
  { label: "Agents", value: "agents" },
  { label: "Alerts", value: "alerts" },
  { label: "System", value: "system" },
] as const;

export function UnifiedStream({ limit = 12, filterTypes, showFilters = false }: { limit?: number; filterTypes?: string[]; showFilters?: boolean }) {
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<string | null>(null);

  const effectiveFilter = activeFilter
    ? [activeFilter]
    : filterTypes;

  useEffect(() => {
    let mounted = true;

    async function fetchEvents() {
      try {
        const response = await fetch(`/api/activity/operator-stream?limit=${limit}`, {
          signal: AbortSignal.timeout(5000),
        }).catch(() => null);

        const merged: StreamEvent[] = [];
        if (response?.ok) {
          const data = await response.json();
          const operatorEvents = Array.isArray(data?.events) ? data.events : [];
          for (const event of operatorEvents) {
            const subsystem = typeof event?.subsystem === "string" ? event.subsystem : "system";
            const type =
              subsystem === "tasks" ||
              subsystem === "agents" ||
              subsystem === "alerts" ||
              subsystem === "provider-plane"
                ? subsystem
                : "system";
            merged.push({
              type,
              source: typeof event?.subject === "string" ? event.subject : "system",
              title: typeof event?.summary === "string" ? event.summary : "Operator event",
              detail:
                typeof event?.event_type === "string" && typeof event?.subsystem === "string"
                  ? `${event.subsystem} - ${event.event_type.replace(/_/g, " ")}`
                  : undefined,
              timestamp: normalizeTimestamp(event?.timestamp),
              severity:
                event?.severity === "success" ||
                event?.severity === "warning" ||
                event?.severity === "error" ||
                event?.severity === "info"
                  ? event.severity
                  : "info",
              link: typeof event?.deep_link === "string" ? event.deep_link : undefined,
            });
          }
        }

        merged.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

        const filtered =
          effectiveFilter && effectiveFilter.length > 0
            ? merged.filter((event) => effectiveFilter.includes(event.type))
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
  }, [limit, effectiveFilter]);

  if (loading) {
    return (
      <div className="space-y-2 py-2">
        {[...Array(3)].map((_, index) => (
          <div key={index} className="flex items-center gap-2">
            <div className="h-3 w-3 animate-pulse rounded bg-muted" />
            <div className="h-3 flex-1 animate-pulse rounded bg-muted" />
          </div>
        ))}
      </div>
    );
  }

  if (events.length === 0) {
    return <p className="py-2 text-xs text-muted-foreground">No recent activity.</p>;
  }

  return (
    <div className="space-y-1">
      {showFilters && (
        <div className="flex gap-1 pb-1.5 flex-wrap">
          {FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.label}
              onClick={() => setActiveFilter(opt.value)}
              className={cn(
                "rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider transition",
                (activeFilter === null && opt.value === null) || activeFilter === opt.value
                  ? "bg-primary/15 border-primary/30 text-primary"
                  : "border-border text-muted-foreground hover:text-foreground"
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
      {events.map((event, index) => {
        const Icon = typeIcon(event.type);
        return (
          <div key={index} className="group/stream flex items-start gap-2 py-1 text-xs">
            <div className="relative mt-0.5 shrink-0">
              <Icon className="h-3.5 w-3.5 text-muted-foreground" />
              {event.severity ? (
                <span
                  className={cn(
                    "absolute -right-0.5 -bottom-0.5 h-1.5 w-1.5 rounded-full",
                    severityDot(event.severity)
                  )}
                />
              ) : null}
            </div>
            <span className="w-8 shrink-0 font-mono text-muted-foreground">{timeAgo(event.timestamp)}</span>
            <div className="min-w-0 flex-1">
              <span className="font-medium text-foreground/80">{event.source}</span>{" "}
              {event.link ? (
                <a href={event.link} className="text-foreground transition-colors hover:text-primary">
                  {event.title}
                </a>
              ) : (
                <span className="text-foreground/70">{event.title}</span>
              )}
              {event.detail ? <span className="text-muted-foreground"> - {event.detail}</span> : null}
            </div>
            <div className="shrink-0 opacity-0 transition-opacity group-hover/stream:opacity-100">
              <FeedbackButtons
                messageContent={`${event.source}: ${event.title}${event.detail ? ` - ${event.detail}` : ""}`}
                agent={event.source}
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
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="m3 17 2 2 4-4" />
      <path d="m3 7 2 2 4-4" />
      <path d="M13 6h8" />
      <path d="M13 12h8" />
      <path d="M13 18h8" />
    </svg>
  );
}

function AgentIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z" />
    </svg>
  );
}

function MediaIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <rect width="18" height="18" x="3" y="3" rx="2" />
      <path d="M7 3v18" />
      <path d="M17 3v18" />
      <path d="M3 7.5h4" />
      <path d="M17 7.5h4" />
      <path d="M3 12h18" />
      <path d="M3 16.5h4" />
      <path d="M17 16.5h4" />
    </svg>
  );
}

function SystemIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v2" />
      <path d="M12 21v2" />
      <path d="M4.22 4.22l1.42 1.42" />
      <path d="M18.36 18.36l1.42 1.42" />
      <path d="M1 12h2" />
      <path d="M21 12h2" />
      <path d="M4.22 19.78l1.42-1.42" />
      <path d="M18.36 5.64l1.42-1.42" />
    </svg>
  );
}
