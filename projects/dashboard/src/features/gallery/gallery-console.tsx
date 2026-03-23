"use client";

import Link from "next/link";
import { type CSSProperties, useDeferredValue, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Film, Play, RefreshCcw, X } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StatCard } from "@/components/stat-card";
import { ComfyUILivePanel } from "@/components/comfyui-live";
import { getGalleryOverview } from "@/lib/api";
import { config } from "@/lib/config";
import { type GallerySnapshot } from "@/lib/contracts";
import { formatRelativeTime } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import { useUrlState } from "@/lib/url-state";

type MediaType = "portrait" | "scene" | "pulid" | "video" | "unknown";

function isVideoFile(filename: string): boolean {
  return /\.(mp4|webm|mov|avi|mkv)$/i.test(filename);
}

function prefixToType(prefix: string, filename?: string): MediaType {
  if (filename && isVideoFile(filename)) return "video";
  const p = prefix.toLowerCase();
  if (p.includes("video")) return "video";
  if (p.includes("pulid")) return "pulid";
  if (p.includes("scene")) return "scene";
  if (p.includes("character") || p.includes("portrait") || p.includes("hq")) return "portrait";
  return "unknown";
}

function typeBadgeStyle(type: string): string {
  switch (type) {
    case "pulid": return "bg-rose-500/20 text-rose-400 border-rose-500/30";
    case "portrait": return "bg-amber-500/20 text-amber-400 border-amber-500/30";
    case "scene": return "bg-sky-500/20 text-sky-400 border-sky-500/30";
    case "video": return "bg-violet-500/20 text-violet-400 border-violet-500/30";
    default: return "bg-zinc-500/20 text-zinc-400 border-zinc-500/30";
  }
}

function typeLabel(type: MediaType): string {
  switch (type) {
    case "pulid": return "PuLID";
    case "video": return "Video";
    default: return type;
  }
}

const previewSurfaceStyle: CSSProperties = {
  background:
    "radial-gradient(circle at top left, color-mix(in oklab, var(--domain-media) 24%, transparent) 0%, transparent 48%), linear-gradient(135deg, color-mix(in oklab, var(--accent-structural) 18%, transparent) 0%, color-mix(in oklab, var(--surface-panel) 84%, black) 100%)",
};

function mediaSrc(image: { subfolder: string; filename: string }): string {
  return `/api/comfyui/image/${image.subfolder ? `${image.subfolder}/` : ""}${image.filename}`;
}

function GalleryMedia({
  images,
  alt,
  className,
  autoPlay,
}: {
  images: GallerySnapshot["items"][number]["outputImages"];
  alt: string;
  className?: string;
  autoPlay?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  const image = images[0];

  if (!image || failed) {
    return (
      <div
        className={`rounded-xl border border-border/60 ${className ?? ""}`}
        style={{ ...previewSurfaceStyle, aspectRatio: "3/4" }}
      />
    );
  }

  const src = mediaSrc(image);
  const isVideo = isVideoFile(image.filename);

  if (isVideo) {
    return (
      <div className={`relative ${className ?? ""}`}>
        <video
          src={src}
          className={`w-full rounded-xl border border-border/60 bg-black/20 ${className ?? ""}`}
          loop
          muted
          playsInline
          autoPlay={autoPlay}
          controls={autoPlay}
          onError={() => setFailed(true)}
        />
        {!autoPlay && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className="rounded-full bg-black/60 p-3">
              <Play className="h-6 w-6 text-white/80" fill="currentColor" />
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      className={`w-full rounded-xl border border-border/60 object-cover bg-black/20 ${className ?? ""}`}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}

export function GalleryConsole({ initialSnapshot }: { initialSnapshot: GallerySnapshot }) {
  const { getSearchValue, setSearchValue } = useUrlState();
  const source = getSearchValue("source", "all");
  const query = getSearchValue("query", "");
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());
  const [lightbox, setLightbox] = useState<GallerySnapshot["items"][number] | null>(null);

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

  // Compute type for each item (based on prefix AND filename)
  const itemsWithType = snapshot.items.map((item) => ({
    ...item,
    mediaType: prefixToType(item.outputPrefix, item.outputImages[0]?.filename),
  }));

  const typeFilters: Array<"all" | MediaType> = ["all", "pulid", "portrait", "scene", "video"];
  const visibleItems = itemsWithType.filter((item) => {
    const matchesSource = source === "all" || item.mediaType === source;
    const matchesQuery =
      !deferredQuery || `${item.prompt} ${item.outputPrefix}`.toLowerCase().includes(deferredQuery);
    return matchesSource && matchesQuery;
  });

  const counts = {
    pulid: itemsWithType.filter((i) => i.mediaType === "pulid").length,
    scene: itemsWithType.filter((i) => i.mediaType === "scene").length,
    video: itemsWithType.filter((i) => i.mediaType === "video").length,
    portrait: itemsWithType.filter((i) => i.mediaType === "portrait").length,
  };

  const lightboxType = lightbox
    ? prefixToType(lightbox.outputPrefix, lightbox.outputImages[0]?.filename)
    : "unknown";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Creative Pipeline"
        title="Gallery"
        description={`${snapshot.items.length} generation${snapshot.items.length !== 1 ? "s" : ""} · ${visibleItems.length} visible`}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => void galleryQuery.refetch()}
              disabled={galleryQuery.isFetching}
            >
              <RefreshCcw className={`mr-2 h-3.5 w-3.5 ${galleryQuery.isFetching ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button asChild variant="outline" size="sm">
              <a href={config.comfyui.url} target="_blank" rel="noopener noreferrer">
                <ArrowUpRight className="mr-2 h-3.5 w-3.5" />
                ComfyUI
              </a>
            </Button>
          </div>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Queue"
            value={snapshot.queueRunning > 0 ? `${snapshot.queueRunning} running` : "Idle"}
            detail={snapshot.queuePending > 0 ? `${snapshot.queuePending} pending` : "Ready to generate"}
            tone={snapshot.queueRunning > 0 ? "warning" : "success"}
          />
          <StatCard
            label="GPU"
            value={snapshot.deviceName?.replace("NVIDIA GeForce ", "") ?? "ComfyUI"}
            detail={
              snapshot.vramUsedGiB != null
                ? `${snapshot.vramUsedGiB.toFixed(1)} / ${snapshot.vramTotalGiB?.toFixed(1)} GiB`
                : "Connected"
            }
          />
          <StatCard label="Images" value={`${counts.pulid + counts.portrait}`} detail={`${counts.pulid} PuLID · ${counts.portrait} portrait`} />
          <StatCard label="Video + Scene" value={`${counts.video + counts.scene}`} detail={`${counts.video} video · ${counts.scene} scene`} />
        </div>
      </PageHeader>

      <ComfyUILivePanel />

      {/* Compact filter bar */}
      <div className="flex flex-wrap items-center gap-2">
        {typeFilters.map((t) => (
          <Button
            key={t}
            size="sm"
            variant={source === t ? "default" : "outline"}
            onClick={() => setSearchValue("source", t === "all" ? null : t)}
            className="capitalize"
          >
            {t === "all" ? "All" : typeLabel(t)}
            {t !== "all" && (
              <span className="ml-1.5 text-[10px] opacity-50">
                {counts[t as keyof typeof counts] ?? 0}
              </span>
            )}
          </Button>
        ))}
        <div className="ml-auto w-64">
          <Input
            value={query}
            onChange={(event) => setSearchValue("query", event.target.value || null)}
            placeholder="Search prompts..."
            className="surface-instrument h-8 text-sm"
          />
        </div>
      </div>

      {/* Masonry grid */}
      {visibleItems.length > 0 ? (
        <div className="columns-1 gap-4 sm:columns-2 xl:columns-3">
          {visibleItems.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setLightbox(item)}
              className="mb-4 block w-full break-inside-avoid overflow-hidden rounded-2xl border border-border/60 bg-card transition hover:border-border hover:shadow-lg hover:shadow-black/20"
            >
              <GalleryMedia images={item.outputImages} alt={item.prompt || "Generated media"} />
              <div className="space-y-1.5 p-3">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className={typeBadgeStyle(item.mediaType)}>
                    {item.mediaType === "video" && <Film className="mr-1 h-3 w-3" />}
                    {typeLabel(item.mediaType)}
                  </Badge>
                  <span className="ml-auto text-[10px] text-muted-foreground">
                    {formatRelativeTime(new Date(item.timestamp * 1000).toISOString())}
                  </span>
                </div>
                {item.prompt && (
                  <p className="line-clamp-2 text-left text-xs text-muted-foreground/80">{item.prompt}</p>
                )}
              </div>
            </button>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No items match"
          description={
            snapshot.items.length === 0
              ? "Generate portraits, scenes, and videos through EoBQ or ComfyUI to populate the gallery."
              : "Clear filters to see all generations."
          }
        />
      )}

      {/* Fullscreen lightbox — supports both image and video */}
      {lightbox && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/95 backdrop-blur-sm"
          onClick={() => setLightbox(null)}
        >
          <button
            className="absolute right-4 top-4 z-10 rounded-full bg-white/10 p-2 text-white/60 transition hover:bg-white/20 hover:text-white"
            onClick={() => setLightbox(null)}
          >
            <X className="h-5 w-5" />
          </button>
          <div
            className="flex max-h-[95vh] max-w-[95vw] flex-col items-center gap-4"
            onClick={(e) => e.stopPropagation()}
          >
            <GalleryMedia
              images={lightbox.outputImages}
              alt={lightbox.prompt || "Generated media"}
              className="max-h-[85vh] w-auto rounded-2xl object-contain"
              autoPlay
            />
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <Badge variant="outline" className={typeBadgeStyle(lightboxType)}>
                {lightboxType === "video" && <Film className="mr-1 h-3 w-3" />}
                {lightboxType === "pulid" ? "PuLID Face Injection" : typeLabel(lightboxType)}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {formatRelativeTime(new Date(lightbox.timestamp * 1000).toISOString())}
              </span>
              <span className="text-xs text-muted-foreground">{lightbox.outputImages[0]?.filename}</span>
            </div>
            {lightbox.prompt && (
              <p className="max-w-2xl text-center text-xs text-muted-foreground/70">{lightbox.prompt}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
