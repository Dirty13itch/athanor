"use client";

import { type CSSProperties, useCallback, useDeferredValue, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckSquare,
  Columns2,
  Columns3,
  Columns4,
  Film,
  GitCompare,
  Layers,
  Play,
  RefreshCcw,
  Square,
  TriangleAlert,
  X,
  ZoomIn,
  ZoomOut,
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
import { RatingBadge } from "./rating-badge";
import { RatingControls } from "./rating-controls";
import { useGalleryRatings, type GalleryRating } from "./use-gallery-ratings";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type MediaType = "portrait" | "scene" | "pulid" | "video" | "unknown";
type RatedFilter = "all" | "approved" | "flagged" | "rejected" | "unrated";
type SortMode = "newest" | "oldest" | "rating" | "name" | "type";
type GridSize = "small" | "medium" | "large";

type GalleryItem = GallerySnapshot["items"][number] & { mediaType: MediaType };

// ---------------------------------------------------------------------------
// Queen names for character filter
// ---------------------------------------------------------------------------

const QUEEN_NAMES = [
  "emilie", "jordan", "alanah", "nikki benz", "chloe", "nicolette", "peta",
  "sandee", "marisol", "trina", "nikki sexx", "madison", "amy", "puma",
  "ava", "brooklyn", "esperanza", "savannah", "shyla", "brianna", "clanddi",
] as const;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function ratingStatus(r: GalleryRating | undefined): "approved" | "flagged" | "rejected" | null {
  if (!r) return null;
  if (r.approved) return "approved";
  if (r.flagged) return "flagged";
  if (r.rating !== null) return "rejected";
  return null;
}

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

/** Detect queen names in prompt text */
function detectQueens(prompt: string): string[] {
  const lower = prompt.toLowerCase();
  return QUEEN_NAMES.filter((q) => lower.includes(q));
}

/** Get all unique queen names from all items */
function extractAllQueens(items: GalleryItem[]): string[] {
  const set = new Set<string>();
  for (const item of items) {
    if (item.prompt) {
      for (const q of detectQueens(item.prompt)) set.add(q);
    }
  }
  return Array.from(set).sort();
}

const previewSurfaceStyle: CSSProperties = {
  background:
    "radial-gradient(circle at top left, color-mix(in oklab, var(--domain-media) 24%, transparent) 0%, transparent 48%), linear-gradient(135deg, color-mix(in oklab, var(--accent-structural) 18%, transparent) 0%, color-mix(in oklab, var(--surface-panel) 84%, black) 100%)",
};

function mediaSrc(image: { subfolder: string; filename: string }): string {
  return `/api/comfyui/image/${image.subfolder ? `${image.subfolder}/` : ""}${image.filename}`;
}

// ---------------------------------------------------------------------------
// Grid size helper
// ---------------------------------------------------------------------------

function gridColsClass(size: GridSize): string {
  switch (size) {
    case "small": return "columns-2 gap-3 sm:columns-3 xl:columns-4";
    case "medium": return "columns-1 gap-4 sm:columns-2 xl:columns-3";
    case "large": return "columns-1 gap-4 sm:columns-1 xl:columns-2";
  }
}

// ---------------------------------------------------------------------------
// Sort
// ---------------------------------------------------------------------------

function sortItems(
  items: GalleryItem[],
  mode: SortMode,
  getRating: (id: string) => GalleryRating | undefined,
): GalleryItem[] {
  const sorted = [...items];
  switch (mode) {
    case "newest":
      sorted.sort((a, b) => b.timestamp - a.timestamp);
      break;
    case "oldest":
      sorted.sort((a, b) => a.timestamp - b.timestamp);
      break;
    case "rating": {
      sorted.sort((a, b) => {
        const ra = getRating(a.id)?.rating ?? 0;
        const rb = getRating(b.id)?.rating ?? 0;
        return rb - ra;
      });
      break;
    }
    case "name":
      sorted.sort((a, b) => {
        const fa = a.outputImages[0]?.filename ?? "";
        const fb = b.outputImages[0]?.filename ?? "";
        return fa.localeCompare(fb);
      });
      break;
    case "type": {
      const typeOrder: Record<MediaType, number> = { pulid: 0, portrait: 1, scene: 2, video: 3, unknown: 4 };
      sorted.sort((a, b) => {
        const diff = (typeOrder[a.mediaType] ?? 4) - (typeOrder[b.mediaType] ?? 4);
        if (diff !== 0) return diff;
        return b.timestamp - a.timestamp;
      });
      break;
    }
  }
  return sorted;
}

// ---------------------------------------------------------------------------
// GalleryMedia component
// ---------------------------------------------------------------------------

function GalleryMedia({
  images,
  alt,
  className,
  autoPlay,
  onClick,
}: {
  images: GallerySnapshot["items"][number]["outputImages"];
  alt: string;
  className?: string;
  autoPlay?: boolean;
  onClick?: () => void;
}) {
  const [failed, setFailed] = useState(false);
  const image = images[0];

  if (!image || failed) {
    return (
      <div
        className={`rounded-xl border border-border/60 ${className ?? ""}`}
        style={{ ...previewSurfaceStyle, aspectRatio: "3/4" }}
        onClick={onClick}
      />
    );
  }

  const src = mediaSrc(image);
  const isVideo = isVideoFile(image.filename);

  if (isVideo) {
    return (
      <div className={`relative ${className ?? ""}`} onClick={onClick}>
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
      onClick={onClick}
    />
  );
}

// ---------------------------------------------------------------------------
// Comparison panel
// ---------------------------------------------------------------------------

function ComparisonPanel({
  items,
  getRating,
  onClear,
}: {
  items: GalleryItem[];
  getRating: (id: string) => GalleryRating | undefined;
  onClear: () => void;
}) {
  if (items.length === 0) return null;

  return (
    <div className="rounded-2xl border border-amber-500/30 bg-zinc-950/80 p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-amber-400">
          Comparison ({items.length}/2)
        </span>
        <Button size="xs" variant="ghost" onClick={onClear} className="text-zinc-500 hover:text-zinc-300">
          Clear
          <X className="ml-1 h-3 w-3" />
        </Button>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {items.map((item) => (
          <div key={item.id} className="space-y-2">
            <GalleryMedia
              images={item.outputImages}
              alt={item.prompt || "Generated media"}
              className="max-h-[50vh] w-full object-contain"
              autoPlay={item.mediaType === "video"}
            />
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className={typeBadgeStyle(item.mediaType)}>
                  {item.mediaType === "video" && <Film className="mr-1 h-3 w-3" />}
                  {typeLabel(item.mediaType)}
                </Badge>
                <RatingBadge status={ratingStatus(getRating(item.id))} />
                <span className="ml-auto text-[10px] text-muted-foreground">
                  {formatRelativeTime(new Date(item.timestamp * 1000).toISOString())}
                </span>
              </div>
              {item.prompt && (
                <p className="text-xs text-muted-foreground/80">{item.prompt}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Enhanced Lightbox
// ---------------------------------------------------------------------------

function EnhancedLightbox({
  item,
  items,
  getRating,
  setRating,
  onClose,
  onNavigate,
}: {
  item: GalleryItem;
  items: GalleryItem[];
  getRating: (id: string) => GalleryRating | undefined;
  setRating: (id: string, r: GalleryRating) => void;
  onClose: () => void;
  onNavigate: (item: GalleryItem) => void;
}) {
  const [zoomed, setZoomed] = useState(false);
  const currentIndex = items.findIndex((i) => i.id === item.id);
  const total = items.length;
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < total - 1;

  const goPrev = useCallback(() => {
    if (hasPrev) onNavigate(items[currentIndex - 1]);
  }, [hasPrev, currentIndex, items, onNavigate]);

  const goNext = useCallback(() => {
    if (hasNext) onNavigate(items[currentIndex + 1]);
  }, [hasNext, currentIndex, items, onNavigate]);

  // Keyboard navigation
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowLeft") goPrev();
      else if (e.key === "ArrowRight") goNext();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose, goPrev, goNext]);

  const lightboxType = prefixToType(item.outputPrefix, item.outputImages[0]?.filename);
  const isVideo = item.outputImages[0] && isVideoFile(item.outputImages[0].filename);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/95 backdrop-blur-sm"
      onClick={() => onClose()}
    >
      {/* Close button */}
      <button
        className="absolute right-4 top-4 z-10 rounded-full bg-white/10 p-2 text-white/60 transition hover:bg-white/20 hover:text-white"
        onClick={() => onClose()}
      >
        <X className="h-5 w-5" />
      </button>

      {/* Position counter */}
      <div className="absolute left-4 top-4 z-10 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-white/60">
        {currentIndex + 1} / {total}
      </div>

      {/* Prev arrow */}
      {hasPrev && (
        <button
          className="absolute left-4 top-1/2 z-10 -translate-y-1/2 rounded-full bg-white/10 p-2 text-white/60 transition hover:bg-white/20 hover:text-white"
          onClick={(e) => { e.stopPropagation(); goPrev(); }}
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
      )}

      {/* Next arrow */}
      {hasNext && (
        <button
          className="absolute right-4 top-1/2 z-10 -translate-y-1/2 rounded-full bg-white/10 p-2 text-white/60 transition hover:bg-white/20 hover:text-white"
          onClick={(e) => { e.stopPropagation(); goNext(); }}
        >
          <ArrowRight className="h-5 w-5" />
        </button>
      )}

      <div
        className="flex max-h-[95vh] max-w-[95vw] flex-col items-center gap-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Media with zoom toggle */}
        <div className="relative">
          {!isVideo && (
            <button
              className="absolute right-2 top-2 z-10 rounded-full bg-black/60 p-1.5 text-white/60 transition hover:bg-black/80 hover:text-white"
              onClick={() => setZoomed((z) => !z)}
            >
              {zoomed ? <ZoomOut className="h-4 w-4" /> : <ZoomIn className="h-4 w-4" />}
            </button>
          )}
          <div
            className={zoomed ? "max-h-[85vh] cursor-zoom-out overflow-auto" : "cursor-zoom-in"}
            onClick={() => { if (!isVideo) setZoomed((z) => !z); }}
          >
            <GalleryMedia
              images={item.outputImages}
              alt={item.prompt || "Generated media"}
              className={zoomed ? "max-w-none rounded-2xl" : "max-h-[85vh] w-auto rounded-2xl object-contain"}
              autoPlay
            />
          </div>
        </div>

        {/* Info bar */}
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <Badge variant="outline" className={typeBadgeStyle(lightboxType)}>
            {lightboxType === "video" && <Film className="mr-1 h-3 w-3" />}
            {lightboxType === "pulid" ? "PuLID Face Injection" : typeLabel(lightboxType)}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {formatRelativeTime(new Date(item.timestamp * 1000).toISOString())}
          </span>
          <span className="text-xs text-muted-foreground">{item.outputImages[0]?.filename}</span>
        </div>

        {/* Full prompt (not truncated) */}
        {item.prompt && (
          <p className="max-w-3xl text-center text-xs leading-relaxed text-muted-foreground/70">
            {item.prompt}
          </p>
        )}

        {/* Rating controls */}
        <RatingControls
          imageId={item.id}
          prompt={item.prompt}
          currentRating={getRating(item.id)}
          onRate={(r) => setRating(item.id, r)}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Gallery Console
// ---------------------------------------------------------------------------

export function GalleryConsole({ initialSnapshot }: { initialSnapshot: GallerySnapshot }) {
  const { getSearchValue, setSearchValue } = useUrlState();

  // URL-persisted state
  const source = getSearchValue("source", "all");
  const query = getSearchValue("query", "");
  const ratedFilter = getSearchValue("rated", "all") as RatedFilter;
  const sortMode = getSearchValue("sort", "newest") as SortMode;
  const characterFilter = getSearchValue("character", "all");
  const gridSize = getSearchValue("grid", "medium") as GridSize;

  const deferredQuery = useDeferredValue(query.trim().toLowerCase());

  // Local state
  const [lightbox, setLightbox] = useState<GalleryItem | null>(null);
  const [compareMode, setCompareMode] = useState(false);
  const [compareItems, setCompareItems] = useState<GalleryItem[]>([]);
  const [batchMode, setBatchMode] = useState(false);
  const [batchSelected, setBatchSelected] = useState<Set<string>>(new Set());

  const { getRating, setRating } = useGalleryRatings();

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

  // Compute type for each item
  const itemsWithType: GalleryItem[] = snapshot.items.map((item) => ({
    ...item,
    mediaType: prefixToType(item.outputPrefix, item.outputImages[0]?.filename),
  }));

  // Extract all queens for the character filter dropdown
  const allQueens = extractAllQueens(itemsWithType);

  const typeFilters: Array<"all" | MediaType> = ["all", "pulid", "portrait", "scene", "video"];
  const ratedFilters: Array<{ key: RatedFilter; label: string; icon?: typeof Check }> = [
    { key: "all", label: "All" },
    { key: "approved", label: "Approved", icon: Check },
    { key: "flagged", label: "Flagged", icon: TriangleAlert },
    { key: "rejected", label: "Rejected", icon: X },
    { key: "unrated", label: "Unrated" },
  ];

  const sortOptions: Array<{ key: SortMode; label: string }> = [
    { key: "newest", label: "Newest" },
    { key: "oldest", label: "Oldest" },
    { key: "rating", label: "Rating" },
    { key: "name", label: "Name" },
    { key: "type", label: "Type" },
  ];

  // Filter items
  const filteredItems = itemsWithType.filter((item) => {
    const matchesSource = source === "all" || item.mediaType === source;
    const matchesQuery =
      !deferredQuery || `${item.prompt} ${item.outputPrefix}`.toLowerCase().includes(deferredQuery);
    if (!matchesSource || !matchesQuery) return false;

    // Character filter
    if (characterFilter !== "all") {
      const queens = item.prompt ? detectQueens(item.prompt) : [];
      if (!queens.includes(characterFilter)) return false;
    }

    // Rating filter
    if (ratedFilter === "all") return true;
    const status = ratingStatus(getRating(item.id));
    if (ratedFilter === "unrated") return status === null;
    return status === ratedFilter;
  });

  // Sort items
  const visibleItems = sortItems(filteredItems, sortMode, getRating);

  const counts = {
    pulid: itemsWithType.filter((i) => i.mediaType === "pulid").length,
    scene: itemsWithType.filter((i) => i.mediaType === "scene").length,
    video: itemsWithType.filter((i) => i.mediaType === "video").length,
    portrait: itemsWithType.filter((i) => i.mediaType === "portrait").length,
  };

  // Compare mode handlers
  function handleCompareToggle(item: GalleryItem) {
    setCompareItems((prev) => {
      const exists = prev.find((i) => i.id === item.id);
      if (exists) return prev.filter((i) => i.id !== item.id);
      if (prev.length >= 2) return [prev[1], item]; // replace oldest
      return [...prev, item];
    });
  }

  // Batch mode handlers
  function toggleBatchItem(id: string) {
    setBatchSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function batchSelectAll() {
    setBatchSelected(new Set(visibleItems.map((i) => i.id)));
  }

  function batchDeselectAll() {
    setBatchSelected(new Set());
  }

  function batchApprove() {
    for (const id of batchSelected) {
      const existing = getRating(id);
      setRating(id, {
        rating: existing?.rating ?? null,
        approved: true,
        flagged: false,
        notes: existing?.notes ?? "",
        timestamp: new Date().toISOString(),
      });
    }
    setBatchSelected(new Set());
  }

  function batchReject() {
    for (const id of batchSelected) {
      const existing = getRating(id);
      setRating(id, {
        rating: existing?.rating ?? 1,
        approved: false,
        flagged: false,
        notes: existing?.notes ?? "",
        timestamp: new Date().toISOString(),
      });
    }
    setBatchSelected(new Set());
  }

  // Card click handler — differs by mode
  function handleCardClick(item: GalleryItem) {
    if (batchMode) {
      toggleBatchItem(item.id);
    } else if (compareMode) {
      handleCompareToggle(item);
    } else {
      setLightbox(item);
    }
  }

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

      {/* ── Row 1: Type filters + Search ── */}
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

      {/* ── Row 2: Rating filter + Sort + Character + Grid size + Mode toggles ── */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        {/* Rating filter */}
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">Rating:</span>
          {ratedFilters.map((f) => (
            <Button
              key={f.key}
              size="xs"
              variant={ratedFilter === f.key ? "default" : "ghost"}
              onClick={() => setSearchValue("rated", f.key === "all" ? null : f.key)}
              className="gap-1"
            >
              {f.icon && <f.icon className="h-3 w-3" />}
              {f.label}
            </Button>
          ))}
        </div>

        {/* Sort control */}
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">Sort:</span>
          <select
            value={sortMode}
            onChange={(e) => setSearchValue("sort", e.target.value === "newest" ? null : e.target.value)}
            className="h-6 rounded-md border border-zinc-700 bg-zinc-900 px-2 text-xs text-zinc-300 focus:border-amber-500/50 focus:outline-none"
          >
            {sortOptions.map((o) => (
              <option key={o.key} value={o.key}>{o.label}</option>
            ))}
          </select>
        </div>

        {/* Character filter */}
        {allQueens.length > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">Queen:</span>
            <select
              value={characterFilter}
              onChange={(e) => setSearchValue("character", e.target.value === "all" ? null : e.target.value)}
              className="h-6 rounded-md border border-zinc-700 bg-zinc-900 px-2 text-xs capitalize text-zinc-300 focus:border-amber-500/50 focus:outline-none"
            >
              <option value="all">All Queens</option>
              {allQueens.map((q) => (
                <option key={q} value={q} className="capitalize">{q}</option>
              ))}
            </select>
          </div>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Grid size */}
        <div className="flex items-center gap-0.5">
          <Button
            size="icon-xs"
            variant={gridSize === "small" ? "default" : "ghost"}
            onClick={() => setSearchValue("grid", "small")}
            title="Small grid (4 columns)"
          >
            <Columns4 className="h-3 w-3" />
          </Button>
          <Button
            size="icon-xs"
            variant={gridSize === "medium" ? "default" : "ghost"}
            onClick={() => setSearchValue("grid", gridSize === "medium" ? null : "medium")}
            title="Medium grid (3 columns)"
          >
            <Columns3 className="h-3 w-3" />
          </Button>
          <Button
            size="icon-xs"
            variant={gridSize === "large" ? "default" : "ghost"}
            onClick={() => setSearchValue("grid", "large")}
            title="Large grid (2 columns)"
          >
            <Columns2 className="h-3 w-3" />
          </Button>
        </div>

        {/* Compare toggle */}
        <Button
          size="xs"
          variant={compareMode ? "default" : "outline"}
          onClick={() => {
            setCompareMode((v) => !v);
            if (compareMode) setCompareItems([]);
          }}
          className={compareMode ? "border-amber-500 bg-amber-500/20 text-amber-400" : ""}
        >
          <GitCompare className="h-3 w-3" />
          Compare
        </Button>

        {/* Batch toggle */}
        <Button
          size="xs"
          variant={batchMode ? "default" : "outline"}
          onClick={() => {
            setBatchMode((v) => !v);
            if (batchMode) setBatchSelected(new Set());
          }}
          className={batchMode ? "border-amber-500 bg-amber-500/20 text-amber-400" : ""}
        >
          <Layers className="h-3 w-3" />
          Batch
        </Button>
      </div>

      {/* ── Batch controls ── */}
      {batchMode && (
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-zinc-800 bg-zinc-950/60 px-3 py-2">
          <span className="text-xs text-zinc-400">
            {batchSelected.size} selected
          </span>
          <Button size="xs" variant="ghost" onClick={batchSelectAll}>Select All</Button>
          <Button size="xs" variant="ghost" onClick={batchDeselectAll}>Deselect All</Button>
          <div className="flex-1" />
          <Button
            size="xs"
            variant="outline"
            onClick={batchApprove}
            disabled={batchSelected.size === 0}
            className="border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/20"
          >
            <Check className="h-3 w-3" />
            Approve ({batchSelected.size})
          </Button>
          <Button
            size="xs"
            variant="outline"
            onClick={batchReject}
            disabled={batchSelected.size === 0}
            className="border-red-500/50 text-red-400 hover:bg-red-500/20"
          >
            <X className="h-3 w-3" />
            Reject ({batchSelected.size})
          </Button>
        </div>
      )}

      {/* ── Comparison panel ── */}
      {compareMode && compareItems.length > 0 && (
        <ComparisonPanel
          items={compareItems}
          getRating={getRating}
          onClear={() => setCompareItems([])}
        />
      )}

      {/* ── Masonry grid ── */}
      {visibleItems.length > 0 ? (
        <div className={gridColsClass(gridSize)}>
          {visibleItems.map((item) => {
            const isCompareSelected = compareMode && compareItems.some((c) => c.id === item.id);
            const isBatchSelected = batchMode && batchSelected.has(item.id);

            return (
              <button
                key={item.id}
                type="button"
                onClick={() => handleCardClick(item)}
                className={`relative mb-4 block w-full break-inside-avoid overflow-hidden rounded-2xl border transition hover:shadow-lg hover:shadow-black/20 ${
                  isCompareSelected
                    ? "border-amber-500 ring-2 ring-amber-500/30"
                    : isBatchSelected
                      ? "border-amber-500 ring-2 ring-amber-500/30"
                      : "border-border/60 hover:border-border"
                } bg-card`}
              >
                {/* Batch checkbox overlay */}
                {batchMode && (
                  <div className="absolute left-2 top-2 z-10">
                    {isBatchSelected ? (
                      <CheckSquare className="h-5 w-5 text-amber-400 drop-shadow-md" />
                    ) : (
                      <Square className="h-5 w-5 text-zinc-400/60 drop-shadow-md" />
                    )}
                  </div>
                )}

                {/* Compare indicator */}
                {compareMode && isCompareSelected && (
                  <div className="absolute left-2 top-2 z-10 rounded-full bg-amber-500 px-1.5 py-0.5 text-[10px] font-bold text-black">
                    {compareItems.findIndex((c) => c.id === item.id) + 1}
                  </div>
                )}

                <GalleryMedia images={item.outputImages} alt={item.prompt || "Generated media"} />
                <RatingBadge status={ratingStatus(getRating(item.id))} />
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

      {/* ── Enhanced Lightbox ── */}
      {lightbox && (
        <EnhancedLightbox
          item={lightbox}
          items={visibleItems}
          getRating={getRating}
          setRating={setRating}
          onClose={() => setLightbox(null)}
          onNavigate={(item) => setLightbox(item)}
        />
      )}
    </div>
  );
}
