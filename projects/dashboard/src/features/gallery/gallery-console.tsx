"use client";

import Link from "next/link";
import { useDeferredValue } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, RefreshCcw } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { StatCard } from "@/components/stat-card";
import { getGalleryOverview } from "@/lib/api";
import { config } from "@/lib/config";
import { type GallerySnapshot } from "@/lib/contracts";
import { formatRelativeTime } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import { useUrlState } from "@/lib/url-state";

function prefixToProject(prefix: string) {
  const normalized = prefix.toLowerCase();
  if (normalized.startsWith("eobq") || normalized.startsWith("eoq")) {
    return "eoq";
  }
  if (normalized.startsWith("kindred")) {
    return "kindred";
  }
  return "athanor";
}

function prefixToLabel(prefix: string) {
  return prefix || "unlabeled";
}

export function GalleryConsole({ initialSnapshot }: { initialSnapshot: GallerySnapshot }) {
  const { getSearchValue, setSearchValue } = useUrlState();
  const source = getSearchValue("source", "all");
  const selection = getSearchValue("selection", "");
  const query = getSearchValue("query", "");
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());

  const galleryQuery = useQuery({
    queryKey: queryKeys.galleryOverview,
    queryFn: getGalleryOverview,
    initialData: initialSnapshot,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  if (galleryQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Domain Console" title="Gallery" description="The gallery snapshot failed to load." />
        <ErrorPanel
          description={
            galleryQuery.error instanceof Error ? galleryQuery.error.message : "Failed to load gallery snapshot."
          }
        />
      </div>
    );
  }

  const snapshot = galleryQuery.data ?? initialSnapshot;
  const prefixes = Array.from(new Set(snapshot.items.map((item) => item.outputPrefix).filter(Boolean)));
  const visibleItems = snapshot.items.filter((item) => {
    const matchesSource = source === "all" || item.outputPrefix === source;
    const matchesQuery = !deferredQuery || `${item.prompt} ${item.outputPrefix}`.toLowerCase().includes(deferredQuery);
    return matchesSource && matchesQuery;
  });
  const activeItem = snapshot.items.find((item) => item.id === selection) ?? null;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Domain Console"
        title="Gallery"
        description="Creative production gallery with queue posture, generation context, and drawer-based preview flows."
        actions={
          <Button variant="outline" onClick={() => void galleryQuery.refetch()} disabled={galleryQuery.isFetching}>
            <RefreshCcw className={`mr-2 h-4 w-4 ${galleryQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Queue running" value={`${snapshot.queueRunning}`} detail={`${snapshot.queuePending} pending`} tone={snapshot.queueRunning > 0 || snapshot.queuePending > 0 ? "warning" : "success"} />
          <StatCard label="Device" value={snapshot.deviceName ?? "Unknown"} detail={`${snapshot.vramUsedGiB?.toFixed(1) ?? "--"} / ${snapshot.vramTotalGiB?.toFixed(1) ?? "--"} GiB`} />
          <StatCard label="Visible generations" value={`${visibleItems.length}`} detail="Filtered creative outputs." />
          <StatCard label="Featured project" value="EoBQ" detail="Primary tenant context for creative generation." />
        </div>
      </PageHeader>

      <Card className="border-border/70 bg-card/70">
        <CardHeader>
          <CardTitle className="text-lg">Source filters</CardTitle>
          <CardDescription>URL-backed filters preserve the exact gallery selection and browser history.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input value={query} onChange={(event) => setSearchValue("query", event.target.value || null)} placeholder="Search prompt or output prefix" />
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant={source === "all" ? "default" : "outline"} onClick={() => setSearchValue("source", null)}>
              All
            </Button>
            {prefixes.map((prefix) => (
              <Button
                key={prefix}
                size="sm"
                variant={source === prefix ? "default" : "outline"}
                onClick={() => setSearchValue("source", prefix)}
              >
                {prefixToLabel(prefix)}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {visibleItems.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {visibleItems.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setSearchValue("selection", item.id)}
              className="rounded-2xl border border-border/70 bg-card/70 p-4 text-left transition hover:bg-accent/40"
            >
              <div className="aspect-[4/3] rounded-2xl border border-border/60 bg-[radial-gradient(circle_at_top_left,_rgba(245,200,109,0.2),_transparent_45%),linear-gradient(135deg,_rgba(120,209,242,0.18),_rgba(25,25,32,0.6))]" />
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <Badge variant="secondary">{prefixToLabel(item.outputPrefix)}</Badge>
                <Badge variant="outline">{prefixToProject(item.outputPrefix)}</Badge>
                <span className="ml-auto text-xs text-muted-foreground">{formatRelativeTime(new Date(item.timestamp * 1000).toISOString())}</span>
              </div>
              <p className="mt-3 line-clamp-3 text-sm font-medium">{item.prompt || "No prompt captured"}</p>
            </button>
          ))}
        </div>
      ) : (
        <EmptyState title="No gallery items match the current filters" description="Clear the prefix filter or widen the search query." />
      )}

      <Sheet open={Boolean(activeItem)} onOpenChange={(open) => setSearchValue("selection", open ? selection : null)}>
        <SheetContent side="right" className="w-full max-w-xl overflow-y-auto border-l border-border/80 bg-background/95">
          {activeItem ? (
            <>
              <SheetHeader className="border-b border-border/80 px-6 py-5 text-left">
                <SheetTitle>{prefixToLabel(activeItem.outputPrefix)}</SheetTitle>
                <SheetDescription>{activeItem.outputImages.map((image) => image.filename).join(", ")}</SheetDescription>
              </SheetHeader>
              <div className="space-y-6 p-6">
                <div className="aspect-[4/3] rounded-2xl border border-border/60 bg-[radial-gradient(circle_at_top_left,_rgba(245,200,109,0.2),_transparent_45%),linear-gradient(135deg,_rgba(120,209,242,0.18),_rgba(25,25,32,0.6))]" />
                <Card className="border-border/70 bg-card/70">
                  <CardHeader>
                    <CardTitle className="text-lg">Generation context</CardTitle>
                    <CardDescription>Keep project and prompt context visible before jumping to ComfyUI.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="secondary">{prefixToLabel(activeItem.outputPrefix)}</Badge>
                      <Badge variant="outline">{prefixToProject(activeItem.outputPrefix)}</Badge>
                    </div>
                    <p className="text-sm">{activeItem.prompt || "No prompt captured."}</p>
                    <div className="flex flex-wrap gap-2">
                      <Button asChild>
                        <a href={config.comfyui.url} target="_blank" rel="noopener noreferrer">
                          <ArrowUpRight className="mr-2 h-4 w-4" />
                          Open ComfyUI
                        </a>
                      </Button>
                      <Button asChild variant="outline">
                        <Link href={`/workplanner?project=${prefixToProject(activeItem.outputPrefix)}`}>
                          Open project
                        </Link>
                      </Button>
                      <Button asChild variant="outline">
                        <Link href={`/outputs?project=${prefixToProject(activeItem.outputPrefix)}`}>
                          Open outputs
                        </Link>
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
