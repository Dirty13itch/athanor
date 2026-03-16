"use client";

import Link from "next/link";
import { type CSSProperties, useDeferredValue, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, RefreshCcw, X } from "lucide-react";
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

function prefixToType(prefix: string): "portrait" | "scene" | "pulid" | "unknown" {
  const p = prefix.toLowerCase();
  if (p.includes("pulid")) return "pulid";
  if (p.includes("scene")) return "scene";
  if (p.includes("character") || p.includes("portrait")) return "portrait";
  return "unknown";
}

function prefixToProject(prefix: string) {
  const normalized = prefix.toLowerCase();
  if (normalized.startsWith("eobq") || normalized.startsWith("eoq")) return "eoq";
  if (normalized.startsWith("kindred")) return "kindred";
  return "athanor";
}

function typeBadgeStyle(type: string): string {
  switch (type) {
    case "pulid": return "bg-rose-500/20 text-rose-400 border-rose-500/30";
    case "portrait": return "bg-amber-500/20 text-amber-400 border-amber-500/30";
    case "scene": return "bg-sky-500/20 text-sky-400 border-sky-500/30";
    default: return "bg-zinc-500/20 text-zinc-400 border-zinc-500/30";
  }
}

const previewSurfaceStyle: CSSProperties = {
  background:
    "radial-gradient(circle at top left, color-mix(in oklab, var(--domain-media) 24%, transparent) 0%, transparent 48%), linear-gradient(135deg, color-mix(in oklab, var(--accent-structural) 18%, transparent) 0%, color-mix(in oklab, var(--surface-panel) 84%, black) 100%)",
};

function GalleryImage({ images, alt, className }: { images: GallerySnapshot["items"][number]["outputImages"]; alt: string; className?: string }) {
  const [failed, setFailed] = useState(false);
  const image = images[0];

  if (!image || failed) {
    return <div className={`rounded-xl border border-border/60 ${className ?? ""}`} style={{ ...previewSurfaceStyle, aspectRatio: "3/4" }} />;
  }

  const src = `/api/comfyui/image/${image.subfolder ? `${image.subfolder}/` : ""}${image.filename}`;

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
  const typeFilters = ["all", "pulid", "portrait", "scene"] as const;
  const visibleItems = snapshot.items.filter((item) => {
    const type = prefixToType(item.outputPrefix);
    const matchesSource = source === "all" || type === source;
    const matchesQuery = !deferredQuery || `${item.prompt} ${item.outputPrefix}`.toLowerCase().includes(deferredQuery);
    return matchesSource && matchesQuery;
  });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Creative Pipeline"
        title="Gallery"
        description={`${snapshot.items.length} generation${snapshot.items.length !== 1 ? "s" : ""} · ${visibleItems.length} visible`}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => void galleryQuery.refetch()} disabled={galleryQuery.isFetching}>
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
          <StatCard label="Queue" value={snapshot.queueRunning > 0 ? `${snapshot.queueRunning} running` : "Idle"} detail={snapshot.queuePending > 0 ? `${snapshot.queuePending} pending` : "Ready to generate"} tone={snapshot.queueRunning > 0 ? "warning" : "success"} />
          <StatCard label="GPU" value={snapshot.deviceName?.replace("NVIDIA GeForce ", "") ?? "ComfyUI"} detail={snapshot.vramUsedGiB != null ? `${snapshot.vramUsedGiB.toFixed(1)} / ${snapshot.vramTotalGiB?.toFixed(1)} GiB` : "Connected"} />
          <StatCard label="PuLID" value={`${snapshot.items.filter(i => prefixToType(i.outputPrefix) === "pulid").length}`} detail="Face-injected portraits" />
          <StatCard label="Scenes" value={`${snapshot.items.filter(i => prefixToType(i.outputPrefix) === "scene").length}`} detail="Environment backgrounds" />
        </div>
      </PageHeader>

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
            {t === "all" ? "All" : t === "pulid" ? "PuLID" : t}
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
          {visibleItems.map((item) => {
            const type = prefixToType(item.outputPrefix);
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setLightbox(item)}
                className="mb-4 block w-full break-inside-avoid overflow-hidden rounded-2xl border border-border/60 bg-card transition hover:border-border hover:shadow-lg hover:shadow-black/20"
              >
                <GalleryImage images={item.outputImages} alt={item.prompt || "Generated image"} />
                <div className="space-y-1.5 p-3">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={typeBadgeStyle(type)}>
                      {type === "pulid" ? "PuLID" : type}
                    </Badge>
                    <span className="ml-auto text-[10px] text-muted-foreground">
                      {formatRelativeTime(new Date(item.timestamp * 1000).toISOString())}
                    </span>
                  </div>
                  {item.prompt && (
                    <p className="line-clamp-2 text-left text-xs text-muted-foreground/80">
                      {item.prompt}
                    </p>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      ) : (
        <EmptyState
          title="No images match"
          description={snapshot.items.length === 0
            ? "Generate portraits and scenes through EoBQ or ComfyUI to populate the gallery."
            : "Clear filters to see all generations."}
        />
      )}

      {/* Fullscreen lightbox */}
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
            <GalleryImage
              images={lightbox.outputImages}
              alt={lightbox.prompt || "Generated image"}
              className="max-h-[85vh] w-auto rounded-2xl object-contain"
            />
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <Badge variant="outline" className={typeBadgeStyle(prefixToType(lightbox.outputPrefix))}>
                {prefixToType(lightbox.outputPrefix) === "pulid" ? "PuLID Face Injection" : prefixToType(lightbox.outputPrefix)}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {formatRelativeTime(new Date(lightbox.timestamp * 1000).toISOString())}
              </span>
              <span className="text-xs text-muted-foreground">
                {lightbox.outputImages[0]?.filename}
              </span>
            </div>
            {lightbox.prompt && (
              <p className="max-w-2xl text-center text-xs text-muted-foreground/70">
                {lightbox.prompt}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
