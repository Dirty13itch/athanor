"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { MessageSquare } from "lucide-react";
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
import { formatRelativeTime } from "@/lib/format";
import { LIVE_REFRESH_INTERVALS, liveQueryOptions } from "@/lib/live-updates";

interface Dialogue {
  id: string;
  queenName: string;
  queenId: string;
  playerInput: string;
  queenResponse: string;
  timestamp: string;
}

const ARCHETYPE_BADGE_COLORS: Record<string, string> = {
  warrior: "oklch(0.55 0.08 230)",
  defiant: "oklch(0.55 0.08 230)",
  priestess: "oklch(0.55 0.12 290)",
  seductress: "oklch(0.55 0.15 15)",
  ice: "oklch(0.7 0.08 230)",
  fire: "oklch(0.65 0.15 50)",
  shadow: "oklch(0.4 0.12 300)",
  sun: "oklch(0.75 0.12 80)",
  innocent: "oklch(0.7 0.1 350)",
};

function queenBadgeColor(queenName: string): string {
  // Simple hash to pick a consistent color per queen
  const hash = queenName.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0);
  const keys = Object.keys(ARCHETYPE_BADGE_COLORS);
  return ARCHETYPE_BADGE_COLORS[keys[hash % keys.length]];
}

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max) + "...";
}

export function RecentDialogueCard() {
  const [selectedDialogue, setSelectedDialogue] = useState<Dialogue | null>(null);

  const { data, isLoading } = useQuery<{ dialogues: Dialogue[] }>({
    queryKey: ["eoq", "conversations"],
    queryFn: async () => {
      const res = await fetch("/api/eoq/conversations");
      if (!res.ok) throw new Error("Failed to fetch conversations");
      return res.json();
    },
    ...liveQueryOptions(LIVE_REFRESH_INTERVALS.overview),
  });

  const dialogues = data?.dialogues ?? [];

  return (
    <>
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <MessageSquare className="h-5 w-5 text-primary" />
            <span style={{ fontFamily: "'Cormorant Garamond', serif" }}>Recent dialogues</span>
          </CardTitle>
          <CardDescription>Latest exchanges with the Council queens.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-16 animate-pulse rounded-2xl bg-muted" />
              ))}
            </div>
          ) : dialogues.length === 0 ? (
            <EmptyState
              title="No dialogues yet"
              description="Open EoBQ to start a session."
              icon={<MessageSquare className="h-5 w-5" />}
            />
          ) : (
            dialogues.slice(0, 5).map((d) => (
              <button
                key={d.id}
                onClick={() => setSelectedDialogue(d)}
                className="surface-tile block w-full rounded-2xl border p-4 text-left transition hover:bg-accent/60"
              >
                <div className="flex items-center justify-between gap-2">
                  <Badge
                    className="shrink-0"
                    style={{ backgroundColor: queenBadgeColor(d.queenName), color: "oklch(0.95 0.01 60)" }}
                  >
                    {d.queenName.split(" ")[0]}
                  </Badge>
                  <span className="text-xs text-muted-foreground" data-volatile="true">
                    {formatRelativeTime(d.timestamp)}
                  </span>
                </div>
                {d.playerInput && (
                  <p className="mt-2 text-sm">{truncate(d.playerInput, 100)}</p>
                )}
                {d.queenResponse && (
                  <p className="mt-1 text-sm italic text-muted-foreground">
                    {truncate(d.queenResponse, 120)}
                  </p>
                )}
              </button>
            ))
          )}
        </CardContent>
      </Card>

      <Sheet open={!!selectedDialogue} onOpenChange={(open) => !open && setSelectedDialogue(null)}>
        <SheetContent side="right" className="overflow-y-auto">
          {selectedDialogue && (
            <>
              <SheetHeader>
                <SheetTitle style={{ fontFamily: "'Cormorant Garamond', serif" }}>
                  {selectedDialogue.queenName}
                </SheetTitle>
                <SheetDescription>
                  {formatRelativeTime(selectedDialogue.timestamp)}
                </SheetDescription>
              </SheetHeader>
              <div className="space-y-4 px-4 pb-4">
                {selectedDialogue.playerInput && (
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Player</p>
                    <p className="mt-1 text-sm">{selectedDialogue.playerInput}</p>
                  </div>
                )}
                {selectedDialogue.queenResponse && (
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Queen</p>
                    <p className="mt-1 text-sm italic">{selectedDialogue.queenResponse}</p>
                  </div>
                )}
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}
