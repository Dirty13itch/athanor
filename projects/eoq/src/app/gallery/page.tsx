"use client";

import { useEffect, useState, useCallback } from "react";
import type { GalleryImage } from "../api/gallery/route";
import Link from "next/link";

const CHARACTER_COLORS: Record<string, string> = {
  Isolde: "border-rose-400/40 hover:border-rose-400/70",
  Seraphine: "border-violet-400/40 hover:border-violet-400/70",
  Valeria: "border-amber-400/40 hover:border-amber-400/70",
  Lilith: "border-red-400/40 hover:border-red-400/70",
  Mireille: "border-emerald-400/40 hover:border-emerald-400/70",
};

const CHARACTER_TEXT: Record<string, string> = {
  Isolde: "text-rose-400",
  Seraphine: "text-violet-400",
  Valeria: "text-amber-400",
  Lilith: "text-red-400",
  Mireille: "text-emerald-400",
};

type FilterType = "all" | "portrait" | "scene" | "unknown";

export default function GalleryPage() {
  const [images, setImages] = useState<GalleryImage[]>([]);
  const [total, setTotal] = useState(0);
  const [characters] = useState(["Isolde", "Seraphine", "Valeria", "Lilith", "Mireille"]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCharacter, setSelectedCharacter] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<FilterType>("all");
  const [lightbox, setLightbox] = useState<GalleryImage | null>(null);

  const fetchGallery = useCallback(async () => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({ limit: "100" });
    if (selectedCharacter) params.set("character", selectedCharacter);
    if (selectedType !== "all") params.set("type", selectedType);

    try {
      const resp = await fetch(`/api/gallery?${params}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setImages(data.images ?? []);
      setTotal(data.total ?? 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [selectedCharacter, selectedType]);

  useEffect(() => {
    fetchGallery();
  }, [fetchGallery]);

  // Keyboard: Escape closes lightbox
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setLightbox(null);
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      {/* Header */}
      <div className="border-b border-white/5 bg-black/40 px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-amber-400">Portrait Gallery</h1>
            <p className="text-xs text-white/30">
              {loading ? "Loading..." : `${total} image${total !== 1 ? "s" : ""} generated`}
            </p>
          </div>
          <Link
            href="/"
            className="rounded border border-white/10 bg-black/40 px-4 py-2 text-sm text-white/50 transition-colors hover:border-amber-400/30 hover:text-amber-400/60"
          >
            ← Back to Game
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="border-b border-white/5 bg-black/20 px-6 py-3">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3">
          {/* Character filter */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-white/30">Character:</span>
            <button
              onClick={() => setSelectedCharacter(null)}
              className={`rounded px-3 py-1 text-xs transition-colors ${
                selectedCharacter === null
                  ? "bg-amber-400/20 text-amber-400"
                  : "text-white/40 hover:text-white/70"
              }`}
            >
              All
            </button>
            {characters.map((name) => (
              <button
                key={name}
                onClick={() => setSelectedCharacter(selectedCharacter === name ? null : name)}
                className={`rounded px-3 py-1 text-xs transition-colors ${
                  selectedCharacter === name
                    ? `${CHARACTER_TEXT[name] ?? "text-white"} bg-white/10`
                    : "text-white/40 hover:text-white/70"
                }`}
              >
                {name}
              </button>
            ))}
          </div>

          {/* Type filter */}
          <div className="flex items-center gap-2 border-l border-white/10 pl-3">
            <span className="text-xs text-white/30">Type:</span>
            {(["all", "portrait", "scene"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setSelectedType(t)}
                className={`rounded px-3 py-1 text-xs capitalize transition-colors ${
                  selectedType === t
                    ? "bg-amber-400/20 text-amber-400"
                    : "text-white/40 hover:text-white/70"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="mx-auto max-w-7xl px-6 py-8">
        {error && (
          <div className="rounded border border-red-400/30 bg-red-900/20 px-4 py-3 text-sm text-red-400">
            {error === "HTTP 502"
              ? "ComfyUI is not reachable — start it on WORKSHOP to browse generated images."
              : `Error: ${error}`}
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-24">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-amber-400/30 border-t-amber-400" />
          </div>
        )}

        {!loading && !error && images.length === 0 && (
          <div className="py-24 text-center">
            <p className="text-white/30">No images yet.</p>
            <p className="mt-2 text-xs text-white/20">
              Play the game and trigger character portrait generation to populate the gallery.
            </p>
          </div>
        )}

        {!loading && images.length > 0 && (
          <div className="columns-2 gap-4 sm:columns-3 lg:columns-4 xl:columns-5">
            {images.map((img) => (
              <div
                key={`${img.promptId}-${img.filename}`}
                className={`mb-4 break-inside-avoid cursor-pointer overflow-hidden rounded border ${
                  CHARACTER_COLORS[img.character ?? ""] ?? "border-white/10 hover:border-white/30"
                } bg-zinc-900 transition-all`}
                onClick={() => setLightbox(img)}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={img.imageUrl}
                  alt={img.character ?? "Generated image"}
                  className="w-full object-cover"
                  loading="lazy"
                />
                {img.character && (
                  <div className="px-2 py-1.5">
                    <span className={`text-xs ${CHARACTER_TEXT[img.character] ?? "text-white/50"}`}>
                      {img.character}
                    </span>
                    {img.type !== "unknown" && (
                      <span className="ml-1 text-[10px] capitalize text-white/20">{img.type}</span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Lightbox */}
      {lightbox && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm"
          onClick={() => setLightbox(null)}
        >
          <div
            className="relative max-h-[90vh] max-w-[90vw]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={lightbox.imageUrl}
              alt={lightbox.character ?? "Generated image"}
              className="max-h-[85vh] max-w-[85vw] rounded object-contain"
            />
            <div className="mt-2 flex items-center justify-between">
              {lightbox.character ? (
                <span className={`text-sm ${CHARACTER_TEXT[lightbox.character] ?? "text-white/50"}`}>
                  {lightbox.character}
                  {lightbox.type !== "unknown" && (
                    <span className="ml-1 text-xs capitalize text-white/30">— {lightbox.type}</span>
                  )}
                </span>
              ) : (
                <span className="text-sm text-white/30">Unidentified scene</span>
              )}
              <button
                onClick={() => setLightbox(null)}
                className="ml-4 text-sm text-white/30 hover:text-white/60"
              >
                Close (Esc)
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
