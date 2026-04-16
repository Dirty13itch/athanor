"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, RefreshCcw } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { StatCard } from "@/components/stat-card";
import { getMediaOverview } from "@/lib/api";
import { type MediaSnapshot } from "@/lib/contracts";
import { formatRelativeTime } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import { useUrlState } from "@/lib/url-state";

function formatSizeGb(value: number | null | undefined) {
  if (!value) {
    return "--";
  }
  return value > 1000 ? `${(value / 1000).toFixed(1)} TB` : `${value.toFixed(0)} GB`;
}

function relativeDate(value: string | null) {
  if (!value) {
    return "Unknown";
  }
  return formatRelativeTime(value);
}

function mediaStatusTone(status: string | null | undefined) {
  const normalized = (status ?? "").toLowerCase();
  if (normalized.includes("play") || normalized.includes("stream") || normalized.includes("downloaded")) {
    return "success";
  }
  if (normalized.includes("queue") || normalized.includes("downloading") || normalized.includes("transcod")) {
    return "warning";
  }
  if (normalized.includes("error") || normalized.includes("failed") || normalized.includes("offline")) {
    return "danger";
  }
  return "info";
}

export function MediaConsole({ initialSnapshot }: { initialSnapshot: MediaSnapshot }) {
  const { getSearchValue, setSearchValue } = useUrlState();
  const panel = getSearchValue("panel", "");

  const mediaQuery = useQuery({
    queryKey: queryKeys.mediaOverview,
    queryFn: getMediaOverview,
    initialData: initialSnapshot,
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });

  if (mediaQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Domain Console" title="Media" description="The media snapshot failed to load." />
        <ErrorPanel
          description={
            mediaQuery.error instanceof Error ? mediaQuery.error.message : "Failed to load media snapshot."
          }
        />
      </div>
    );
  }

  const snapshot = mediaQuery.data ?? initialSnapshot;
  const activeLink = snapshot.launchLinks.find((link) => link.id === panel) ?? null;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Domain Console"
        title="Media"
        description="VAULT media operations across playback, acquisition, catalog quality, and safe external launches."
        actions={
          <Button variant="outline" onClick={() => void mediaQuery.refetch()} disabled={mediaQuery.isFetching}>
            <RefreshCcw className={`mr-2 h-4 w-4 ${mediaQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Active streams" value={`${snapshot.streamCount}`} detail="Current Plex playback sessions." />
          <StatCard label="Downloads" value={`${snapshot.downloads.length}`} detail="Combined Sonarr and Radarr queue." tone={snapshot.downloads.length > 0 ? "warning" : "success"} />
          <StatCard label="TV library" value={`${snapshot.tvLibrary?.total ?? 0}`} detail={`${snapshot.tvLibrary?.episodes ?? 0} episodes`} />
          <StatCard label="Movie library" value={`${snapshot.movieLibrary?.total ?? 0}`} detail={`${snapshot.movieLibrary?.hasFile ?? 0} downloaded`} />
        </div>
      </PageHeader>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.9fr]">
        <Card className="surface-panel border">
          <CardHeader>
            <CardTitle className="text-lg">Playback and queue</CardTitle>
            <CardDescription>Live sessions and active acquisition work across the media plane.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {snapshot.sessions.length > 0 ? (
              snapshot.sessions.map((session) => (
                <div key={`${session.title}-${session.friendlyName}`} className="surface-instrument rounded-2xl border p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline" className="status-badge" data-tone={mediaStatusTone(session.state)}>
                      {session.state ?? "unknown"}
                    </Badge>
                    {session.mediaType ? <Badge variant="outline">{session.mediaType}</Badge> : null}
                    <span className="ml-auto text-xs text-muted-foreground">{session.friendlyName ?? "Unknown client"}</span>
                  </div>
                  <p className="mt-3 text-sm font-medium">{session.title ?? "Untitled session"}</p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {session.transcodeDecision ?? "Playback decision unavailable"} | {session.progressPercent?.toFixed(0) ?? "--"}%
                  </p>
                </div>
              ))
            ) : (
              <EmptyState title="No active playback" description="No Plex sessions are active right now." />
            )}

            {snapshot.downloads.length > 0 ? (
              <div className="space-y-3">
                {snapshot.downloads.map((download) => (
                  <div key={download.id} className="surface-tile rounded-2xl border p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline" className="status-badge" data-tone="info">{download.source}</Badge>
                      {download.status ? (
                        <Badge variant="outline" className="status-badge" data-tone={mediaStatusTone(download.status)}>
                          {download.status}
                        </Badge>
                      ) : null}
                    </div>
                    <p className="mt-3 text-sm font-medium">{download.title ?? "Untitled download"}</p>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {download.progressPercent?.toFixed(0) ?? "--"}% complete
                      {download.timeLeft ? ` | ${download.timeLeft} remaining` : ""}
                    </p>
                  </div>
                ))}
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card className="surface-panel border">
          <CardHeader>
            <CardTitle className="text-lg">Launch pads</CardTitle>
            <CardDescription>Drawer previews keep operator context in Athanor before opening the full tool.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {snapshot.launchLinks.map((link) => (
              <div key={link.id} className="surface-instrument flex items-center justify-between rounded-2xl border px-4 py-3">
                <div>
                  <p className="font-medium">{link.label}</p>
                  <p className="text-xs text-muted-foreground">{link.url}</p>
                </div>
                <Button size="sm" variant="outline" onClick={() => setSearchValue("panel", link.id)}>
                  Preview
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="surface-panel border">
          <CardHeader>
            <CardTitle className="text-lg">Upcoming releases</CardTitle>
            <CardDescription>TV and movie release lanes tracked by the acquisition stack.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {[...snapshot.tvUpcoming, ...snapshot.movieUpcoming].length > 0 ? (
              [...snapshot.tvUpcoming, ...snapshot.movieUpcoming].map((entry) => (
                <div key={entry.id} className="surface-tile rounded-2xl border p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    {entry.hasFile ? (
                      <Badge variant="outline" className="status-badge" data-tone="success">
                        Downloaded
                      </Badge>
                    ) : null}
                    <span className="ml-auto text-xs text-muted-foreground">{entry.airDateUtc ? relativeDate(entry.airDateUtc) : "Unknown"}</span>
                  </div>
                  <p className="mt-3 text-sm font-medium">{entry.seriesTitle ?? entry.title}</p>
                  {entry.seasonNumber !== null && entry.episodeNumber !== null ? (
                    <p className="mt-2 text-sm text-muted-foreground">
                      S{String(entry.seasonNumber).padStart(2, "0")}E{String(entry.episodeNumber).padStart(2, "0")}
                    </p>
                  ) : null}
                </div>
              ))
            ) : (
              <EmptyState title="No upcoming releases" description="Nothing is queued in the near-term release calendar." />
            )}
          </CardContent>
        </Card>

        <Card className="surface-panel border">
          <CardHeader>
            <CardTitle className="text-lg">Catalog posture</CardTitle>
            <CardDescription>Storage footprint and watch history across the media plane.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Metric label="TV size" value={formatSizeGb(snapshot.tvLibrary?.sizeGb)} />
            <Metric label="Movie size" value={formatSizeGb(snapshot.movieLibrary?.sizeGb)} />
            <Metric label="Stash scenes" value={`${snapshot.stash?.sceneCount ?? 0}`} />
            {snapshot.watchHistory.map((entry) => (
              <div key={entry.id} className="surface-tile rounded-2xl border p-4">
                <div className="flex flex-wrap items-center gap-2">
                  {entry.watchedStatus === 1 ? (
                    <Badge variant="outline" className="status-badge" data-tone="success">
                      Completed
                    </Badge>
                  ) : null}
                  <span className="ml-auto text-xs text-muted-foreground">{relativeDate(entry.date)}</span>
                </div>
                <p className="mt-3 text-sm font-medium">{entry.title ?? "Untitled"}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Sheet open={Boolean(activeLink)} onOpenChange={(open) => setSearchValue("panel", open ? panel : null)}>
        <SheetContent side="right" className="w-full max-w-xl overflow-y-auto border-l border-border/80 bg-background/95">
          {activeLink ? (
            <>
              <SheetHeader className="border-b border-border/80 px-6 py-5 text-left">
                <SheetTitle>{activeLink.label}</SheetTitle>
                <SheetDescription>{activeLink.url}</SheetDescription>
              </SheetHeader>
              <div className="space-y-6 p-6">
                <Card className="surface-instrument border">
                  <CardHeader>
                    <CardTitle className="text-lg">Drawer preview</CardTitle>
                    <CardDescription>Keep context in Athanor, then jump out to the full workflow when needed.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm text-muted-foreground">
                      Use the media console for summaries, queue state, and cross-links. Open the external tool for full browsing or editing workflows.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <Button asChild>
                        <a href={activeLink.url} target="_blank" rel="noopener noreferrer">
                          <ArrowUpRight className="mr-2 h-4 w-4" />
                          Open {activeLink.label}
                        </a>
                      </Button>
                      <Button asChild variant="outline">
                        <Link href="/monitoring">Open monitoring</Link>
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="surface-metric flex items-center justify-between rounded-xl border px-3 py-2 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
