"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusDot } from "@/components/status-dot";

interface Session {
  title: string | null;
  state: string | null;
  progressPercent: number | null;
  product: string | null;
}

interface Download {
  title: string | null;
  source: string;
  progressPercent: number | null;
  status: string | null;
  timeLeft: string | null;
}

interface WatchItem {
  title: string | null;
  date: string | null;
  watchedStatus: number | null;
}

interface Library {
  total: number | null;
  episodes?: number | null;
  sizeGb: number | null;
}

interface StashStats {
  sceneCount: number | null;
  scenesSize: number | null;
}

interface MediaState {
  sessions: Session[];
  downloads: Download[];
  watchHistory: WatchItem[];
  tvLibrary: Library | null;
  movieLibrary: Library | null;
  stash: StashStats | null;
  loading: boolean;
  error: boolean;
}

async function fetchMedia(setState: (fn: (prev: MediaState) => MediaState) => void) {
  try {
    const res = await fetch("/api/media/overview", { signal: AbortSignal.timeout(8000) });
    if (!res.ok) {
      setState((prev) => ({ ...prev, loading: false, error: true }));
      return;
    }
    const data = await res.json();
    setState(() => ({
      sessions: data.sessions ?? [],
      downloads: data.downloads ?? [],
      watchHistory: data.watchHistory ?? [],
      tvLibrary: data.tvLibrary ?? null,
      movieLibrary: data.movieLibrary ?? null,
      stash: data.stash ?? null,
      loading: false,
      error: false,
    }));
  } catch {
    setState((prev) => ({ ...prev, loading: false, error: true }));
  }
}

function formatSize(gb: number | null): string {
  if (gb === null) return "--";
  return gb >= 1000 ? `${(gb / 1000).toFixed(1)} TB` : `${Math.round(gb)} GB`;
}

function formatRelative(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function MediaGlance() {
  const [state, setState] = useState<MediaState>({
    sessions: [],
    downloads: [],
    watchHistory: [],
    tvLibrary: null,
    movieLibrary: null,
    stash: null,
    loading: true,
    error: false,
  });

  useEffect(() => {
    void fetchMedia(setState);
    const interval = setInterval(() => void fetchMedia(setState), 15000);
    return () => clearInterval(interval);
  }, []);

  if (state.loading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <MonitorIcon className="h-4 w-4 text-primary" />
            Media
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="h-3 w-3/4 animate-pulse rounded bg-muted" />
            <div className="h-3 w-1/2 animate-pulse rounded bg-muted" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (state.error) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <MonitorIcon className="h-4 w-4 text-primary" />
            Media
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">Unable to reach media services.</p>
        </CardContent>
      </Card>
    );
  }

  const activeSessions = state.sessions.filter((s) => s.state === "playing" || s.state === "paused");
  const activeDownloads = state.downloads.filter((d) => d.status !== "completed");
  const tvSize = state.tvLibrary?.sizeGb ?? 0;
  const movieSize = state.movieLibrary?.sizeGb ?? 0;
  const stashSize = state.stash?.scenesSize ? state.stash.scenesSize / (1024 * 1024 * 1024) : 0;
  const totalSize = tvSize + movieSize + stashSize;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm">
            <MonitorIcon className="h-4 w-4 text-primary" />
            Media
          </CardTitle>
          <Link href="/media" className="text-xs text-muted-foreground hover:text-foreground transition">
            View all &rarr;
          </Link>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Now Playing */}
        {activeSessions.length > 0 ? (
          <div className="space-y-2">
            {activeSessions.slice(0, 3).map((session, i) => (
              <div key={i} className="flex items-center gap-2">
                <StatusDot tone={session.state === "playing" ? "healthy" : "muted"} pulse={session.state === "playing"} />
                <span className="text-sm truncate flex-1">{session.title ?? "Unknown"}</span>
                {session.progressPercent !== null && (
                  <span className="text-xs text-muted-foreground">{Math.round(session.progressPercent)}%</span>
                )}
                <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                  {session.state === "playing" ? "Playing" : "Paused"}
                </Badge>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">Nothing playing</p>
        )}

        {/* Active Downloads */}
        {activeDownloads.length > 0 && (
          <div className="border-t border-border/50 pt-2 space-y-1.5">
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground">Downloads</p>
            {activeDownloads.slice(0, 3).map((dl, i) => (
              <div key={i} className="flex items-center gap-2">
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0">{dl.source}</Badge>
                <span className="text-xs truncate flex-1">{dl.title ?? "Unknown"}</span>
                {dl.progressPercent !== null && (
                  <span className="text-xs text-muted-foreground">{Math.round(dl.progressPercent)}%</span>
                )}
                {dl.timeLeft && <span className="text-[10px] text-muted-foreground">{dl.timeLeft}</span>}
              </div>
            ))}
          </div>
        )}

        {/* Recently Watched */}
        {state.watchHistory.length > 0 && activeSessions.length === 0 && (
          <div className="border-t border-border/50 pt-2 space-y-1">
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground">Recently watched</p>
            {state.watchHistory.slice(0, 3).map((item, i) => (
              <div key={i} className="flex items-center justify-between gap-2">
                <span className="text-xs truncate">{item.title ?? "Unknown"}</span>
                <span className="text-[10px] text-muted-foreground whitespace-nowrap">{formatRelative(item.date)}</span>
              </div>
            ))}
          </div>
        )}

        {/* Library Stats */}
        <div className="border-t border-border/50 pt-2">
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-sm font-medium font-mono">{state.tvLibrary?.total ?? "--"}</p>
              <p className="text-[10px] text-muted-foreground">Shows</p>
            </div>
            <div>
              <p className="text-sm font-medium font-mono">{state.movieLibrary?.total ?? "--"}</p>
              <p className="text-[10px] text-muted-foreground">Movies</p>
            </div>
            <div>
              <p className="text-sm font-medium font-mono">{formatSize(totalSize)}</p>
              <p className="text-[10px] text-muted-foreground">Total</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function MonitorIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <rect width="20" height="14" x="2" y="3" rx="2" />
      <line x1="8" x2="16" y1="21" y2="21" />
      <line x1="12" x2="12" y1="17" y2="21" />
    </svg>
  );
}
