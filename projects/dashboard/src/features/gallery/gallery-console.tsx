"use client";

import Link from "next/link";
import { type CSSProperties, useCallback, useDeferredValue, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowUpRight,
  Check,
  ChevronDown,
  ChevronUp,
  Film,
  MessageSquare,
  Play,
  RefreshCcw,
  Star,
  Wrench,
  X,
} from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StatCard } from "@/components/stat-card";
import { getGalleryOverview } from "@/lib/api";
import { config } from "@/lib/config";
import { type GallerySnapshot } from "@/lib/contracts";
import { formatRelativeTime } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import { useUrlState } from "@/lib/url-state";

// ---------------------------------------------------------------------------
// Rating types & localStorage persistence
// ---------------------------------------------------------------------------

interface ImageRating {
  rating: number; // 0-5 (0 = unrated)
  approved: boolean;
  flagged: boolean;
  notes: string;
  timestamp: string;
}

type RatingStatus = "approved" | "flagged" | "rejected" | "unrated";

type RatingsMap = Record<string, ImageRating>;

const RATINGS_STORAGE_KEY = "athanor-gallery-ratings";

function loadRatings(): RatingsMap {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(RATINGS_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as RatingsMap) : {};
  } catch {
    return {};
  }
}

function saveRatings(ratings: RatingsMap): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(RATINGS_STORAGE_KEY, JSON.stringify(ratings));
}

function imageId(image: { subfolder: string; filename: string }): string {
  return image.subfolder ? `${image.subfolder}/${image.filename}` : image.filename;
}

function itemImageId(item: GallerySnapshot["items"][number]): string {
  const img = item.outputImages[0];
  return img ? imageId(img) : item.id;
}

function ratingStatus(r: ImageRating | undefined): RatingStatus {
  if (!r) return "unrated";
  if (r.approved) return "approved";
  if (r.flagged) return "flagged";
  // Rated but not approved/flagged = rejected (explicit negative decision)
  if (r.rating > 0 && !r.approved && !r.flagged) return "rejected";
  return "unrated";
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

function useRatings() {
  const [ratings, setRatings] = useState<RatingsMap>({});

  useEffect(() => {
    setRatings(loadRatings());
  }, []);

  const update = useCallback((id: string, partial: Partial<ImageRating>) => {
    setRatings((prev) => {
      const existing = prev[id] ?? { rating: 0, approved: false, flagged: false, notes: "", timestamp: "" };
      const next: RatingsMap = {
        ...prev,
        [id]: {
          ...existing,
          ...partial,
          timestamp: new Date().toISOString(),
        },
      };
      saveRatings(next);
      return next;
    });
  }, []);

  const setApproved = useCallback(
    (id: string) => update(id, { approved: true, flagged: false }),
    [update]
  );

  const setRejected = useCallback(
    (id: string) => update(id, { approved: false, flagged: false, rating: (loadRatings()[id]?.rating || 1) }),
    [update]
  );

  const setFlagged = useCallback(
    (id: string) => update(id, { flagged: true, approved: false }),
    [update]
  );

  const setStarRating = useCallback(
    (id: string, stars: number) => update(id, { rating: stars }),
    [update]
  );

  const setNotes = useCallback(
    (id: string, notes: string) => update(id, { notes }),
    [update]
  );

  return { ratings, setApproved, setRejected, setFlagged, setStarRating, setNotes };
}

// ---------------------------------------------------------------------------
// Media type helpers (unchanged)
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Rating status badge for grid items
// ---------------------------------------------------------------------------

function RatingBadge({ status }: { status: RatingStatus }) {
  switch (status) {
    case "approved":
      return (
        <span className="absolute right-2 top-2 z-10 flex items-center gap-1 rounded-full bg-emerald-500/80 px-2 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm">
          <Check className="h-3 w-3" />
        </span>
      );
    case "rejected":
      return (
        <span className="absolute right-2 top-2 z-10 flex items-center gap-1 rounded-full bg-red-500/80 px-2 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm">
          <X className="h-3 w-3" />
        </span>
      );
    case "flagged":
      return (
        <span className="absolute right-2 top-2 z-10 flex items-center gap-1 rounded-full bg-amber-500/80 px-2 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm">
          <Wrench className="h-3 w-3" />
        </span>
      );
    default:
      return null;
  }
}

// ---------------------------------------------------------------------------
// Star rating component
// ---------------------------------------------------------------------------

function StarRating({
  value,
  onChange,
  size = "md",
}: {
  value: number;
  onChange: (stars: number) => void;
  size?: "sm" | "md";
}) {
  const [hover, setHover] = useState(0);
  const iconSize = size === "sm" ? "h-4 w-4" : "h-5 w-5";

  return (
    <div className="flex items-center gap-0.5" onMouseLeave={() => setHover(0)}>
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          className="p-0.5 transition-transform hover:scale-110"
          onMouseEnter={() => setHover(star)}
          onClick={(e) => {
            e.stopPropagation();
            onChange(star === value ? 0 : star);
          }}
        >
          <Star
            className={`${iconSize} transition-colors ${
              star <= (hover || value)
                ? "fill-amber-400 text-amber-400"
                : "fill-transparent text-zinc-600"
            }`}
          />
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// GalleryMedia (unchanged)
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Lightbox rating controls
// ---------------------------------------------------------------------------

function LightboxRatingControls({
  id,
  rating,
  onApprove,
  onReject,
  onFlag,
  onRate,
  onNotesChange,
}: {
  id: string;
  rating: ImageRating | undefined;
  onApprove: () => void;
  onReject: () => void;
  onFlag: () => void;
  onRate: (stars: number) => void;
  onNotesChange: (notes: string) => void;
}) {
  const [notesOpen, setNotesOpen] = useState(false);
  const status = ratingStatus(rating);

  return (
    <div
      className="flex flex-col items-center gap-3 rounded-xl bg-zinc-900/70 px-4 py-3 backdrop-blur-md"
      onClick={(e) => e.stopPropagation()}
    >
      {/* Star rating */}
      <StarRating value={rating?.rating ?? 0} onChange={onRate} />

      {/* Action buttons */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onApprove}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
            status === "approved"
              ? "bg-emerald-500/30 text-emerald-300 ring-1 ring-emerald-500/50"
              : "bg-white/5 text-white/60 hover:bg-emerald-500/20 hover:text-emerald-300"
          }`}
        >
          <Check className="h-3.5 w-3.5" />
          Approve
        </button>

        <button
          type="button"
          onClick={onReject}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
            status === "rejected"
              ? "bg-red-500/30 text-red-300 ring-1 ring-red-500/50"
              : "bg-white/5 text-white/60 hover:bg-red-500/20 hover:text-red-300"
          }`}
        >
          <X className="h-3.5 w-3.5" />
          Reject
        </button>

        <button
          type="button"
          onClick={onFlag}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
            status === "flagged"
              ? "bg-amber-500/30 text-amber-300 ring-1 ring-amber-500/50"
              : "bg-white/5 text-white/60 hover:bg-amber-500/20 hover:text-amber-300"
          }`}
        >
          <Wrench className="h-3.5 w-3.5" />
          Flag
        </button>

        <button
          type="button"
          onClick={() => setNotesOpen((v) => !v)}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
            rating?.notes
              ? "bg-sky-500/20 text-sky-300 ring-1 ring-sky-500/40"
              : "bg-white/5 text-white/60 hover:bg-white/10 hover:text-white/80"
          }`}
        >
          <MessageSquare className="h-3.5 w-3.5" />
          Notes
          {notesOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        </button>
      </div>

      {/* Collapsible notes textarea */}
      {notesOpen && (
        <textarea
          value={rating?.notes ?? ""}
          onChange={(e) => onNotesChange(e.target.value)}
          placeholder="Add notes for refinement..."
          rows={3}
          className="w-full max-w-md resize-none rounded-lg border border-zinc-700/60 bg-zinc-800/80 px-3 py-2 text-xs text-zinc-200 placeholder:text-zinc-500 focus:border-amber-500/50 focus:outline-none focus:ring-1 focus:ring-amber-500/30"
        />
      )}

      {/* Refine button for flagged images */}
      {status === "flagged" && (
        <button
          type="button"
          onClick={() => {
            // TODO: Queue a new generation with same prompt + notes via agent server
            // POST foundry:9000/v1/gallery/refine { imageId, notes }
            alert(`Refinement queued for ${id}\nNotes: ${rating?.notes ?? "(none)"}`);
          }}
          className="flex items-center gap-1.5 rounded-lg bg-amber-500/20 px-3 py-1.5 text-xs font-medium text-amber-300 ring-1 ring-amber-500/40 transition hover:bg-amber-500/30"
        >
          <RefreshCcw className="h-3.5 w-3.5" />
          Refine with Notes
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

type RatingFilter = "all" | "approved" | "flagged" | "rejected" | "unrated";

export function GalleryConsole({ initialSnapshot }: { initialSnapshot: GallerySnapshot }) {
  const { getSearchValue, setSearchValue, setSearchValues } = useUrlState();
  const source = getSearchValue("source", "all");
  const query = getSearchValue("query", "");
  const ratingFilter = getSearchValue("status", "all") as RatingFilter;
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());
  const [lightbox, setLightbox] = useState<GallerySnapshot["items"][number] | null>(null);

  const { ratings, setApproved, setRejected, setFlagged, setStarRating, setNotes } = useRatings();

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
  const ratingFilters: RatingFilter[] = ["all", "approved", "flagged", "rejected", "unrated"];

  const ratingFilterLabels: Record<RatingFilter, string> = {
    all: "All",
    approved: "Approved",
    flagged: "Flagged",
    rejected: "Rejected",
    unrated: "Unrated",
  };

  const ratingFilterIcons: Record<RatingFilter, typeof Check | null> = {
    all: null,
    approved: Check,
    flagged: Wrench,
    rejected: X,
    unrated: null,
  };

  const visibleItems = itemsWithType.filter((item) => {
    const matchesSource = source === "all" || item.mediaType === source;
    const matchesQuery =
      !deferredQuery || `${item.prompt} ${item.outputPrefix}`.toLowerCase().includes(deferredQuery);

    // Rating filter
    let matchesRating = true;
    if (ratingFilter !== "all") {
      const iid = itemImageId(item);
      const status = ratingStatus(ratings[iid]);
      matchesRating = status === ratingFilter;
    }

    return matchesSource && matchesQuery && matchesRating;
  });

  const counts = {
    pulid: itemsWithType.filter((i) => i.mediaType === "pulid").length,
    scene: itemsWithType.filter((i) => i.mediaType === "scene").length,
    video: itemsWithType.filter((i) => i.mediaType === "video").length,
    portrait: itemsWithType.filter((i) => i.mediaType === "portrait").length,
  };

  // Rating counts
  const ratingCounts = {
    approved: itemsWithType.filter((i) => ratingStatus(ratings[itemImageId(i)]) === "approved").length,
    flagged: itemsWithType.filter((i) => ratingStatus(ratings[itemImageId(i)]) === "flagged").length,
    rejected: itemsWithType.filter((i) => ratingStatus(ratings[itemImageId(i)]) === "rejected").length,
    unrated: itemsWithType.filter((i) => ratingStatus(ratings[itemImageId(i)]) === "unrated").length,
  };

  const lightboxType = lightbox
    ? prefixToType(lightbox.outputPrefix, lightbox.outputImages[0]?.filename)
    : "unknown";

  const lightboxId = lightbox ? itemImageId(lightbox) : "";

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

      {/* Compact filter bar — media type */}
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

        {/* Separator */}
        <div className="mx-1 h-5 w-px bg-zinc-700/50" />

        {/* Rating status filter */}
        {ratingFilters.map((rf) => {
          const Icon = ratingFilterIcons[rf];
          const isActive = ratingFilter === rf;
          return (
            <Button
              key={rf}
              size="sm"
              variant={isActive ? "default" : "outline"}
              onClick={() => setSearchValue("status", rf === "all" ? null : rf)}
              className={
                rf === "approved" && isActive ? "bg-emerald-600 hover:bg-emerald-700" :
                rf === "flagged" && isActive ? "bg-amber-600 hover:bg-amber-700" :
                rf === "rejected" && isActive ? "bg-red-600 hover:bg-red-700" :
                ""
              }
            >
              {Icon && <Icon className="mr-1 h-3 w-3" />}
              {ratingFilterLabels[rf]}
              {rf !== "all" && (
                <span className="ml-1.5 text-[10px] opacity-50">
                  {ratingCounts[rf as keyof typeof ratingCounts] ?? 0}
                </span>
              )}
            </Button>
          );
        })}

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
          {visibleItems.map((item) => {
            const iid = itemImageId(item);
            const r = ratings[iid];
            const status = ratingStatus(r);

            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setLightbox(item)}
                className="relative mb-4 block w-full break-inside-avoid overflow-hidden rounded-2xl border border-border/60 bg-card transition hover:border-border hover:shadow-lg hover:shadow-black/20"
              >
                {/* Rating badge overlay */}
                <div className="relative">
                  <RatingBadge status={status} />
                  <GalleryMedia images={item.outputImages} alt={item.prompt || "Generated media"} />
                </div>
                <div className="space-y-1.5 p-3">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={typeBadgeStyle(item.mediaType)}>
                      {item.mediaType === "video" && <Film className="mr-1 h-3 w-3" />}
                      {typeLabel(item.mediaType)}
                    </Badge>
                    {/* Mini star display */}
                    {r && r.rating > 0 && (
                      <span className="flex items-center gap-0.5">
                        {[1, 2, 3, 4, 5].map((s) => (
                          <Star
                            key={s}
                            className={`h-3 w-3 ${
                              s <= r.rating ? "fill-amber-400 text-amber-400" : "fill-transparent text-zinc-600"
                            }`}
                          />
                        ))}
                      </span>
                    )}
                    <span className="ml-auto text-[10px] text-muted-foreground">
                      {formatRelativeTime(new Date(item.timestamp * 1000).toISOString())}
                    </span>
                  </div>
                  {item.prompt && (
                    <p className="line-clamp-2 text-left text-xs text-muted-foreground/80">{item.prompt}</p>
                  )}
                </div>
              </button>
            );
          })}
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

      {/* Fullscreen lightbox — supports both image and video, with rating controls */}
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
              className="max-h-[70vh] w-auto rounded-2xl object-contain"
              autoPlay
            />

            {/* Rating controls */}
            <LightboxRatingControls
              id={lightboxId}
              rating={ratings[lightboxId]}
              onApprove={() => setApproved(lightboxId)}
              onReject={() => setRejected(lightboxId)}
              onFlag={() => setFlagged(lightboxId)}
              onRate={(stars) => setStarRating(lightboxId, stars)}
              onNotesChange={(notes) => setNotes(lightboxId, notes)}
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
