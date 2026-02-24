"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ProgressBar } from "@/components/progress-bar";

interface PlexSession {
  friendly_name?: string;
  full_title?: string;
  state?: string;
  progress_percent?: string;
  transcode_decision?: string;
  media_type?: string;
  year?: string;
  thumb?: string;
}

interface QueueItem {
  title?: string;
  sizeleft?: number;
  size?: number;
  status?: string;
  timeleft?: string;
  trackedDownloadStatus?: string;
  trackedDownloadState?: string;
}

interface CalendarItem {
  title?: string;
  seriesTitle?: string;
  seasonNumber?: number;
  episodeNumber?: number;
  airDateUtc?: string;
  hasFile?: boolean;
}

interface WatchItem {
  friendly_name?: string;
  full_title?: string;
  date?: string;
  duration?: string;
  watched_status?: number;
}

interface MediaData {
  plex_activity: {
    stream_count?: number;
    sessions?: PlexSession[];
  };
  sonarr_queue: QueueItem[];
  radarr_queue: QueueItem[];
  tv_upcoming: CalendarItem[];
  movie_upcoming: CalendarItem[];
  tv_library: { total?: number; monitored?: number; episodes?: number; size_gb?: number };
  movie_library: { total?: number; monitored?: number; has_file?: number; size_gb?: number };
  watch_history: WatchItem[];
}

interface StashStats {
  stats: {
    scene_count?: number;
    image_count?: number;
    performer_count?: number;
    studio_count?: number;
    tag_count?: number;
    scenes_size?: number;
    scenes_duration?: number;
  } | null;
}

export default function MediaPage() {
  const [media, setMedia] = useState<MediaData | null>(null);
  const [stash, setStash] = useState<StashStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [mediaRes, stashRes] = await Promise.all([
        fetch("/api/media"),
        fetch("/api/stash/stats"),
      ]);

      if (mediaRes.ok) {
        setMedia(await mediaRes.json());
      }
      if (stashRes.ok) {
        setStash(await stashRes.json());
      }
      setLastUpdated(new Date());
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 15000);
    return () => clearInterval(id);
  }, [fetchData]);

  const sessions = media?.plex_activity?.sessions ?? [];
  const streamCount = media?.plex_activity?.stream_count ?? 0;
  const downloads = [
    ...(media?.sonarr_queue ?? []).map((d) => ({ ...d, source: "Sonarr" as const })),
    ...(media?.radarr_queue ?? []).map((d) => ({ ...d, source: "Radarr" as const })),
  ];
  const tvUpcoming = media?.tv_upcoming ?? [];
  const movieUpcoming = media?.movie_upcoming ?? [];
  const watchHistory = media?.watch_history ?? [];
  const stashData = stash?.stats;

  const tvLib = media?.tv_library;
  const movieLib = media?.movie_library;
  const totalSizeGB = (tvLib?.size_gb ?? 0) + (movieLib?.size_gb ?? 0);

  function formatBytes(gb: number): string {
    if (gb >= 1000) return `${(gb / 1000).toFixed(1)} TB`;
    return `${gb.toFixed(1)} GB`;
  }

  function formatDuration(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    if (hours >= 24) return `${Math.floor(hours / 24)}d ${hours % 24}h`;
    return `${hours}h`;
  }

  function formatCalendarDate(utc?: string): string {
    if (!utc) return "";
    const d = new Date(utc);
    const now = new Date();
    const diff = Math.floor((d.getTime() - now.getTime()) / 86400000);
    if (diff === 0) return "Today";
    if (diff === 1) return "Tomorrow";
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  function watchTimeAgo(date?: string): string {
    if (!date) return "";
    const ts = parseInt(date);
    if (isNaN(ts)) return "";
    const diff = Date.now() / 1000 - ts;
    const hours = Math.floor(diff / 3600);
    if (hours < 1) return "Just now";
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days === 1) return "Yesterday";
    return `${days}d ago`;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Media</h1>
          <p className="text-muted-foreground">
            Plex, Sonarr, Radarr, Stash — all on VAULT
          </p>
        </div>
        <div className="flex items-center gap-2">
          {lastUpdated && (
            <span className="text-xs text-muted-foreground">
              {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <Button size="sm" variant="outline" onClick={fetchData}>Refresh</Button>
        </div>
      </div>

      {loading && (
        <Card>
          <CardContent className="py-6">
            <p className="text-sm text-muted-foreground">Loading media status...</p>
          </CardContent>
        </Card>
      )}

      {/* Now Playing + Library */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Now Playing */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Now Playing</CardTitle>
              {streamCount > 0 && (
                <Badge className="text-xs">{streamCount} stream{streamCount > 1 ? "s" : ""}</Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {sessions.length > 0 ? (
              <div className="space-y-3">
                {sessions.map((s, i) => {
                  const progress = parseInt(s.progress_percent ?? "0");
                  return (
                    <div key={i} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium truncate max-w-[200px]">{s.full_title}</span>
                        <span className="text-muted-foreground text-xs">{s.friendly_name}</span>
                      </div>
                      <ProgressBar
                        value={progress}
                        showValue
                        colorStops={[
                          { threshold: 0, color: "bg-primary" },
                        ]}
                      />
                      <p className="text-xs text-muted-foreground">
                        {s.transcode_decision === "direct play" ? "Direct Play" : s.transcode_decision ?? ""}
                      </p>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-2">Nothing playing</p>
            )}
          </CardContent>
        </Card>

        {/* Library */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Library</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {tvLib && (
                <div className="flex items-center justify-between text-sm">
                  <span>TV Shows</span>
                  <span className="font-mono text-xs text-muted-foreground">
                    {tvLib.total} shows, {tvLib.episodes?.toLocaleString()} episodes — {formatBytes(tvLib.size_gb ?? 0)}
                  </span>
                </div>
              )}
              {movieLib && (
                <div className="flex items-center justify-between text-sm">
                  <span>Movies</span>
                  <span className="font-mono text-xs text-muted-foreground">
                    {movieLib.total} films ({movieLib.has_file} downloaded) — {formatBytes(movieLib.size_gb ?? 0)}
                  </span>
                </div>
              )}
              {(tvLib || movieLib) && (
                <div className="flex items-center justify-between text-xs border-t border-border pt-2">
                  <span className="text-muted-foreground">Total Media</span>
                  <span className="font-mono font-medium">{formatBytes(totalSizeGB)}</span>
                </div>
              )}

              {stashData && (
                <div className="border-t border-border pt-2 space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span>Stash</span>
                    <span className="font-mono text-xs text-muted-foreground">
                      {stashData.scene_count?.toLocaleString()} scenes, {stashData.performer_count} performers
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>
                      {stashData.studio_count} studios, {stashData.tag_count} tags
                    </span>
                    <span className="font-mono">
                      {stashData.scenes_size ? formatBytes(stashData.scenes_size / (1024 ** 3)) : ""}
                      {stashData.scenes_duration ? ` / ${formatDuration(stashData.scenes_duration)}` : ""}
                    </span>
                  </div>
                </div>
              )}

              {!tvLib && !movieLib && !stashData && (
                <p className="text-sm text-muted-foreground">Library data unavailable</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Download Queue */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Download Queue</CardTitle>
            {downloads.length > 0 && (
              <Badge variant="outline" className="text-xs">{downloads.length} active</Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {downloads.length > 0 ? (
            <div className="space-y-3">
              {downloads.map((d, i) => {
                const pct = d.size ? ((d.size - (d.sizeleft ?? 0)) / d.size) * 100 : 0;
                return (
                  <div key={i} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <Badge variant="outline" className="text-xs shrink-0">{d.source}</Badge>
                        <span className="truncate">{d.title}</span>
                      </div>
                      <span className="text-xs font-mono text-muted-foreground ml-2">
                        {pct.toFixed(0)}%{d.timeleft ? ` — ${d.timeleft}` : ""}
                      </span>
                    </div>
                    <ProgressBar value={pct} />
                  </div>
                );
              })}
            </div>
          ) : media ? (
            <p className="text-sm text-muted-foreground py-2">No active downloads</p>
          ) : (
            <p className="text-sm text-muted-foreground py-2">Loading...</p>
          )}
        </CardContent>
      </Card>

      {/* Upcoming */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* TV Upcoming */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">TV Upcoming (7 days)</CardTitle>
          </CardHeader>
          <CardContent>
            {tvUpcoming.length > 0 ? (
              <div className="space-y-2">
                {tvUpcoming.slice(0, 10).map((ep, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <div className="min-w-0 flex-1">
                      <span className="font-medium">{ep.seriesTitle ?? ep.title}</span>
                      {ep.seasonNumber !== undefined && ep.episodeNumber !== undefined && (
                        <span className="text-muted-foreground ml-1">
                          S{String(ep.seasonNumber).padStart(2, "0")}E{String(ep.episodeNumber).padStart(2, "0")}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {ep.hasFile && <Badge variant="default" className="text-xs">Downloaded</Badge>}
                      <span className="text-xs text-muted-foreground font-mono">
                        {formatCalendarDate(ep.airDateUtc)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : media ? (
              <p className="text-sm text-muted-foreground py-2">Nothing upcoming this week</p>
            ) : null}
          </CardContent>
        </Card>

        {/* Movie Upcoming */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Movies Upcoming (30 days)</CardTitle>
          </CardHeader>
          <CardContent>
            {movieUpcoming.length > 0 ? (
              <div className="space-y-2">
                {movieUpcoming.slice(0, 10).map((m, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="truncate">{m.title}</span>
                    <span className="text-xs text-muted-foreground font-mono shrink-0 ml-2">
                      {formatCalendarDate(m.airDateUtc)}
                    </span>
                  </div>
                ))}
              </div>
            ) : media ? (
              <p className="text-sm text-muted-foreground py-2">No upcoming movies</p>
            ) : null}
          </CardContent>
        </Card>
      </div>

      {/* Watch History */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Recent Watches</CardTitle>
        </CardHeader>
        <CardContent>
          {watchHistory.length > 0 ? (
            <div className="space-y-2">
              {watchHistory.slice(0, 10).map((w, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className="truncate">{w.full_title}</span>
                    {w.watched_status === 1 && (
                      <Badge variant="outline" className="text-xs shrink-0">Completed</Badge>
                    )}
                  </div>
                  <span className="text-xs text-muted-foreground font-mono shrink-0 ml-2">
                    {watchTimeAgo(w.date)}
                  </span>
                </div>
              ))}
            </div>
          ) : media ? (
            <p className="text-sm text-muted-foreground py-2">No recent watches</p>
          ) : null}
        </CardContent>
      </Card>

      {/* Quick Links */}
      <Card>
        <CardContent className="py-3">
          <div className="flex flex-wrap gap-2">
            {[
              { name: "Plex", url: "http://192.168.1.203:32400/web" },
              { name: "Sonarr", url: "http://192.168.1.203:8989" },
              { name: "Radarr", url: "http://192.168.1.203:7878" },
              { name: "Tautulli", url: "http://192.168.1.203:8181" },
              { name: "Prowlarr", url: "http://192.168.1.203:9696" },
              { name: "SABnzbd", url: "http://192.168.1.203:8080" },
              { name: "Stash", url: "http://192.168.1.203:9999" },
            ].map((link) => (
              <a
                key={link.name}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent transition-colors"
              >
                {link.name}
              </a>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function Button({
  children,
  size,
  variant,
  onClick,
  disabled,
}: {
  children: React.ReactNode;
  size?: string;
  variant?: string;
  onClick?: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`rounded-md border border-border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50 ${
        size === "sm" ? "px-2 py-1" : ""
      } ${variant === "outline" ? "bg-transparent" : ""}`}
    >
      {children}
    </button>
  );
}
