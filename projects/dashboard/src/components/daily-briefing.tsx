"use client";

import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface BriefingTask {
  id: string;
  agent: string;
  status: string;
  description?: string;
  title?: string;
  prompt?: string;
  result?: string;
  created_at?: string | number;
  updated_at?: string | number;
}

interface BriefingState {
  content: string | null;
  timestamp: string | null;
  loading: boolean;
}

async function fetchLatestBriefing(
  setState: Dispatch<SetStateAction<BriefingState>>
) {
  try {
    const res = await fetch("/api/agents/proxy?path=/v1/tasks&limit=50", {
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) {
      setState((prev) => ({ ...prev, loading: false }));
      return;
    }

    const data = await res.json();
    const tasks: BriefingTask[] = data.tasks ?? data ?? [];
    if (!Array.isArray(tasks)) {
      setState((prev) => ({ ...prev, loading: false }));
      return;
    }

    const briefingTask = tasks
      .filter((t) => {
        if (t.status !== "completed") return false;
        const text = [t.description, t.title, t.prompt].filter(Boolean).join(" ").toLowerCase();
        return text.includes("digest") || text.includes("briefing") || text.includes("morning");
      })
      .sort((a, b) => {
        const aTime = parseTimestamp(a.updated_at ?? a.created_at);
        const bTime = parseTimestamp(b.updated_at ?? b.created_at);
        if (!aTime || !bTime) return 0;
        return new Date(bTime).getTime() - new Date(aTime).getTime();
      })[0];

    if (briefingTask?.result) {
      const ts = parseTimestamp(briefingTask.updated_at ?? briefingTask.created_at);
      setState({
        content: briefingTask.result,
        timestamp: ts,
        loading: false,
      });
    } else {
      setState({ content: null, timestamp: null, loading: false });
    }
  } catch {
    setState((prev) => ({ ...prev, loading: false }));
  }
}

function parseTimestamp(raw: string | number | undefined): string | null {
  if (!raw) return null;
  if (typeof raw === "number") return new Date(raw * 1000).toISOString();
  return raw;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  const today = new Date();
  if (d.toDateString() === today.toDateString()) return "Today";
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) return "Yesterday";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function DailyBriefing() {
  const [state, setState] = useState<BriefingState>({
    content: null,
    timestamp: null,
    loading: true,
  });

  useEffect(() => {
    void fetchLatestBriefing(setState);
    const interval = setInterval(() => {
      void fetchLatestBriefing(setState);
    }, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SunriseIcon className="h-4 w-4 text-amber-400" />
            <CardTitle className="text-sm">Morning Briefing</CardTitle>
            {state.timestamp && (
              <span className="text-xs text-muted-foreground">
                {formatDate(state.timestamp)} at {formatTime(state.timestamp)}
              </span>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs"
            onClick={() => {
              setState((prev) => ({ ...prev, loading: true }));
              void fetchLatestBriefing(setState);
            }}
          >
            <RefreshIcon className="h-3 w-3 mr-1" />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {state.loading ? (
          <div className="space-y-2 py-1">
            <div className="h-3 w-3/4 animate-pulse rounded bg-muted" />
            <div className="h-3 w-1/2 animate-pulse rounded bg-muted" />
            <div className="h-3 w-2/3 animate-pulse rounded bg-muted" />
          </div>
        ) : state.content ? (
          <div className="text-sm text-foreground/80 whitespace-pre-wrap leading-relaxed">
            {state.content}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground py-1">
            No briefing available yet. The daily digest runs at 6:55 AM.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function SunriseIcon({ className }: { className?: string }) {
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
      <path d="M12 2v4" />
      <path d="m4.93 10.93 1.41 1.41" />
      <path d="M2 18h2" />
      <path d="M20 18h2" />
      <path d="m19.07 10.93-1.41 1.41" />
      <path d="M22 22H2" />
      <path d="M16 18a4 4 0 0 0-8 0" />
      <path d="M12 10a6 6 0 0 0-6 6" />
      <path d="M12 10a6 6 0 0 1 6 6" />
    </svg>
  );
}

function RefreshIcon({ className }: { className?: string }) {
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
      <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
      <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
      <path d="M16 16h5v5" />
    </svg>
  );
}
