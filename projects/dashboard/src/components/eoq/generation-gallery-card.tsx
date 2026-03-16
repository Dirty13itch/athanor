"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ImageIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";

interface EoqGeneration {
  promptId: string;
  prompt: string;
  queenName: string;
  type: "portrait" | "scene";
  images: { filename: string; subfolder: string }[];
  timestamp: number;
}

export function GenerationGalleryCard() {
  const [selectedGen, setSelectedGen] = useState<EoqGeneration | null>(null);

  const { data, isLoading } = useQuery<{ generations: EoqGeneration[] }>({
    queryKey: ["eoq", "generations"],
    queryFn: async () => {
      const res = await fetch("/api/eoq/generations");
      if (!res.ok) throw new Error("Failed to fetch generations");
      return res.json();
    },
    staleTime: 30_000,
  });

  const generations = data?.generations ?? [];

  return (
    <>
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <ImageIcon className="h-5 w-5 text-primary" />
            <span style={{ fontFamily: "'Cormorant Garamond', serif" }}>Generations</span>
          </CardTitle>
          <CardDescription>Recent EoBQ visual outputs from ComfyUI.</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="grid grid-cols-2 gap-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="aspect-square animate-pulse rounded-xl bg-muted" />
              ))}
            </div>
          ) : generations.length === 0 ? (
            <EmptyState
              title="No generations yet"
              description="Portraits are created during gameplay."
              icon={<ImageIcon className="h-5 w-5" />}
            />
          ) : (
            <>
              <div className="grid grid-cols-2 gap-2">
                {generations.slice(0, 4).map((gen) => (
                  <button
                    key={gen.promptId}
                    onClick={() => setSelectedGen(gen)}
                    className="group relative aspect-square overflow-hidden rounded-xl border transition hover:ring-2 hover:ring-primary/50"
                  >
                    {gen.images[0] && (
                      <img
                        src={`/api/comfyui/image/${gen.images[0].subfolder}/${gen.images[0].filename}`}
                        alt={gen.queenName}
                        loading="lazy"
                        className="h-full w-full object-cover transition group-hover:scale-105"
                      />
                    )}
                    <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent px-2 py-1.5">
                      <p className="text-xs font-medium text-white">{gen.queenName}</p>
                      <Badge variant="secondary" className="mt-0.5 text-[10px]">
                        {gen.type}
                      </Badge>
                    </div>
                  </button>
                ))}
              </div>
              {generations.length > 4 && (
                <a
                  href="/gallery?source=eoq"
                  className="mt-3 block text-center text-xs text-muted-foreground hover:text-primary"
                >
                  View all {generations.length} generations
                </a>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <Sheet open={!!selectedGen} onOpenChange={(open) => !open && setSelectedGen(null)}>
        <SheetContent side="right" className="overflow-y-auto">
          {selectedGen && (
            <>
              <SheetHeader>
                <SheetTitle style={{ fontFamily: "'Cormorant Garamond', serif" }}>
                  {selectedGen.queenName}
                </SheetTitle>
                <SheetDescription>
                  {selectedGen.type === "portrait" ? "Character portrait" : "Scene illustration"}
                </SheetDescription>
              </SheetHeader>
              <div className="space-y-4 px-4 pb-4">
                {selectedGen.images[0] && (
                  <img
                    src={`/api/comfyui/image/${selectedGen.images[0].subfolder}/${selectedGen.images[0].filename}`}
                    alt={selectedGen.queenName}
                    className="w-full rounded-xl"
                  />
                )}
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Prompt</p>
                  <p className="mt-1 text-sm text-muted-foreground">{selectedGen.prompt || "No prompt extracted"}</p>
                </div>
                <div className="flex gap-4 text-sm">
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Type</p>
                    <p className="mt-1 capitalize">{selectedGen.type}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Generated</p>
                    <p className="mt-1">{new Date(selectedGen.timestamp * 1000).toLocaleString()}</p>
                  </div>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}
