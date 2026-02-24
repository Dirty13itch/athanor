"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface ComfyImage {
  filename: string;
  subfolder: string;
  type: string;
}

interface HistoryItem {
  promptId: string;
  prompt: string;
  outputImages: ComfyImage[];
  timestamp: number;
  outputPrefix: string;
}

interface ComfyStats {
  system?: {
    devices?: { name: string; vram_total: number; vram_free: number }[];
  };
}

type FilterMode = "all" | "EoBQ/character" | "EoBQ/scene" | "other";

export default function GalleryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [queueRunning, setQueueRunning] = useState(0);
  const [queuePending, setQueuePending] = useState(0);
  const [stats, setStats] = useState<ComfyStats | null>(null);
  const [filter, setFilter] = useState<FilterMode>("all");
  const [selectedItem, setSelectedItem] = useState<{ item: HistoryItem; image: ComfyImage } | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [historyRes, queueRes, statsRes] = await Promise.all([
        fetch("/api/comfyui/history?max_items=50"),
        fetch("/api/comfyui/queue"),
        fetch("/api/comfyui/stats"),
      ]);

      if (historyRes.ok) {
        const data = await historyRes.json();
        setItems(data.items ?? []);
      }
      if (queueRes.ok) {
        const data = await queueRes.json();
        setQueueRunning(data.queue_running?.length ?? 0);
        setQueuePending(data.queue_pending?.length ?? 0);
      }
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 30000);
    return () => clearInterval(id);
  }, [fetchData]);

  async function handleGenerate(workflow: "character" | "scene") {
    setGenerating(true);
    try {
      const defaultPrompt =
        workflow === "character"
          ? "Cinematic portrait of a beautiful woman with an intense, regal expression"
          : "Wide establishing shot of a dark medieval throne room";

      const res = await fetch("/api/comfyui/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workflow, prompt: defaultPrompt }),
      });

      if (res.ok) {
        // Refresh queue status
        setTimeout(fetchData, 1000);
      }
    } catch {
      // silent
    } finally {
      setGenerating(false);
    }
  }

  function imageUrl(img: ComfyImage): string {
    const path = img.subfolder ? `${img.subfolder}/${img.filename}` : img.filename;
    return `/api/comfyui/image/${encodeURIComponent(path)}`;
  }

  function timeAgo(ts: number): string {
    const diff = Date.now() / 1000 - ts;
    const mins = Math.floor(diff / 60);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  }

  // Flatten items to individual images for grid display
  const allImages = items.flatMap((item) =>
    item.outputImages.map((img) => ({ item, image: img }))
  );

  const filteredImages = allImages.filter(({ item }) => {
    if (filter === "all") return true;
    if (filter === "EoBQ/character") return item.outputPrefix.startsWith("EoBQ/character");
    if (filter === "EoBQ/scene") return item.outputPrefix.startsWith("EoBQ/scene");
    // "other" = anything not EoBQ
    return !item.outputPrefix.startsWith("EoBQ/");
  });

  const hasEoBQCharacter = allImages.some(({ item }) => item.outputPrefix.startsWith("EoBQ/character"));
  const hasEoBQScene = allImages.some(({ item }) => item.outputPrefix.startsWith("EoBQ/scene"));
  const hasOther = allImages.some(({ item }) => !item.outputPrefix.startsWith("EoBQ/"));

  const gpuDevice = stats?.system?.devices?.[0];
  const vramUsed = gpuDevice ? ((gpuDevice.vram_total - gpuDevice.vram_free) / (1024 ** 3)).toFixed(1) : null;
  const vramTotal = gpuDevice ? (gpuDevice.vram_total / (1024 ** 3)).toFixed(0) : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Gallery</h1>
          <p className="text-muted-foreground">
            ComfyUI on Workshop (RTX 5090{vramTotal ? `, ${vramTotal} GB` : ""})
            {vramUsed && vramTotal && (
              <span className="ml-2 font-mono text-xs">VRAM: {vramUsed}/{vramTotal} GB</span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {(queueRunning > 0 || queuePending > 0) && (
            <Badge variant="default" className="text-xs">
              {queueRunning > 0 ? `${queueRunning} generating` : ""}{queueRunning > 0 && queuePending > 0 ? ", " : ""}{queuePending > 0 ? `${queuePending} queued` : ""}
            </Badge>
          )}
          <div className="relative group">
            <Button size="sm" disabled={generating}>
              {generating ? "Queuing..." : "Generate"}
            </Button>
            <div className="absolute right-0 top-full mt-1 hidden group-hover:block z-10 bg-card border border-border rounded-md shadow-lg p-1 min-w-[180px]">
              <button
                onClick={() => handleGenerate("character")}
                disabled={generating}
                className="block w-full text-left px-3 py-1.5 text-sm hover:bg-accent rounded-sm"
              >
                EoBQ Character Portrait
              </button>
              <button
                onClick={() => handleGenerate("scene")}
                disabled={generating}
                className="block w-full text-left px-3 py-1.5 text-sm hover:bg-accent rounded-sm"
              >
                EoBQ Scene
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        <FilterButton active={filter === "all"} onClick={() => setFilter("all")}>All</FilterButton>
        {hasEoBQCharacter && (
          <FilterButton active={filter === "EoBQ/character"} onClick={() => setFilter("EoBQ/character")}>
            EoBQ/character
          </FilterButton>
        )}
        {hasEoBQScene && (
          <FilterButton active={filter === "EoBQ/scene"} onClick={() => setFilter("EoBQ/scene")}>
            EoBQ/scene
          </FilterButton>
        )}
        {hasOther && (
          <FilterButton active={filter === "other"} onClick={() => setFilter("other")}>Other</FilterButton>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <Card>
          <CardContent className="py-6">
            <p className="text-sm text-muted-foreground">Loading gallery...</p>
          </CardContent>
        </Card>
      )}

      {/* Empty state */}
      {!loading && filteredImages.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-sm text-muted-foreground">
              {items.length === 0
                ? "No generations yet. ComfyUI history is empty."
                : `No images matching "${filter}" filter.`}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Image Grid */}
      {filteredImages.length > 0 && (
        <div className="grid gap-4 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {filteredImages.map(({ item, image }, i) => (
            <button
              key={`${item.promptId}-${image.filename}-${i}`}
              onClick={() => setSelectedItem({ item, image })}
              className="group rounded-lg border border-border bg-card overflow-hidden text-left hover:ring-2 hover:ring-primary transition-all"
            >
              <div className="aspect-[3/4] relative bg-muted">
                <img
                  src={imageUrl(image)}
                  alt={item.prompt.slice(0, 60)}
                  className="absolute inset-0 w-full h-full object-cover"
                  loading="lazy"
                />
              </div>
              <div className="p-2 space-y-0.5">
                {item.outputPrefix && (
                  <Badge variant="outline" className="text-xs">
                    {item.outputPrefix}
                  </Badge>
                )}
                <p className="text-xs text-muted-foreground truncate">
                  {item.prompt.slice(0, 60) || "No prompt text"}
                </p>
                <p className="text-xs text-muted-foreground font-mono">
                  {timeAgo(item.timestamp)}
                </p>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Detail Sheet */}
      {selectedItem && (
        <div
          className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setSelectedItem(null)}
        >
          <div
            className="bg-card border border-border rounded-lg max-w-4xl w-full max-h-[90vh] overflow-auto shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex flex-col lg:flex-row">
              {/* Image */}
              <div className="lg:flex-1 bg-muted">
                <img
                  src={imageUrl(selectedItem.image)}
                  alt={selectedItem.item.prompt.slice(0, 100)}
                  className="w-full h-auto"
                />
              </div>

              {/* Metadata */}
              <div className="lg:w-80 p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold">Generation Details</h3>
                  <button
                    onClick={() => setSelectedItem(null)}
                    className="text-muted-foreground hover:text-foreground text-lg"
                  >
                    x
                  </button>
                </div>

                {selectedItem.item.outputPrefix && (
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Output Prefix</p>
                    <Badge variant="outline">{selectedItem.item.outputPrefix}</Badge>
                  </div>
                )}

                <div>
                  <p className="text-xs text-muted-foreground mb-1">Prompt</p>
                  <p className="text-sm whitespace-pre-wrap bg-muted rounded-md p-2 font-mono text-xs">
                    {selectedItem.item.prompt || "No prompt text extracted"}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <p className="text-muted-foreground">File</p>
                    <p className="font-mono">{selectedItem.image.filename}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Folder</p>
                    <p className="font-mono">{selectedItem.image.subfolder || "root"}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Generated</p>
                    <p className="font-mono">{timeAgo(selectedItem.item.timestamp)}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Images</p>
                    <p className="font-mono">{selectedItem.item.outputImages.length}</p>
                  </div>
                </div>

                <a
                  href={imageUrl(selectedItem.image)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-center rounded-md border border-border px-3 py-1.5 text-sm hover:bg-accent transition-colors"
                >
                  Open Full Size
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function FilterButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-md border px-3 py-1 text-xs transition-colors ${
        active
          ? "border-primary bg-primary text-primary-foreground"
          : "border-border hover:bg-accent"
      }`}
    >
      {children}
    </button>
  );
}
