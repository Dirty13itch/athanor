"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Sparkles, Star, ThumbsDown, ThumbsUp, Wrench } from "lucide-react";
import { Button } from "@/components/ui/button";
import { type GalleryRating } from "./use-gallery-ratings";

// ---------------------------------------------------------------------------

function StarRow({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (n: number) => void;
}) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          className="p-0.5 transition hover:scale-110"
        >
          <Star
            className={`h-5 w-5 ${
              value != null && n <= value
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

export function RatingControls({
  imageId,
  prompt,
  currentRating,
  onRate,
}: {
  imageId: string;
  prompt: string;
  currentRating: GalleryRating | undefined;
  onRate: (rating: GalleryRating) => void;
}) {
  const [showNotes, setShowNotes] = useState(
    () => !!currentRating?.flagged || (currentRating?.notes ?? "").length > 0,
  );
  const [refining, setRefining] = useState(false);

  const rating = currentRating ?? {
    rating: null,
    approved: false,
    flagged: false,
    notes: "",
    timestamp: new Date().toISOString(),
  };

  const isRejected = !rating.approved && !rating.flagged && rating.rating !== null;

  // Helpers ----------------------------------------------------------------

  function emit(patch: Partial<GalleryRating>) {
    onRate({ ...rating, ...patch, timestamp: new Date().toISOString() });
  }

  function handleApprove() {
    emit({ approved: !rating.approved, flagged: false });
  }

  function handleReject() {
    if (isRejected) {
      // Toggle off — clear rating entirely
      emit({ approved: false, flagged: false, rating: null });
    } else {
      emit({ approved: false, flagged: false });
    }
  }

  function handleFlag() {
    const next = !rating.flagged;
    emit({ flagged: next, approved: false });
    if (next) setShowNotes(true);
  }

  async function handleRefine() {
    setRefining(true);
    try {
      await fetch("/api/operator/backlog", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: `Refine gallery generation ${imageId}`,
          prompt: [
            `Refine gallery generation for image ${imageId}.`,
            `Original prompt: ${prompt}`,
            rating.notes ? `Operator notes: ${rating.notes}` : "",
          ]
            .filter(Boolean)
            .join("\n"),
          owner_agent: "creative-agent",
          scope_type: "domain",
          scope_id: "creative",
          work_class: "creative_refine",
          priority: rating.flagged || (rating.rating !== null && rating.rating <= 2) ? 4 : 3,
          approval_mode: "none",
          dispatch_policy: "planner_eligible",
          metadata: {
            imageId,
            prompt,
            notes: rating.notes,
            approved: rating.approved,
            flagged: rating.flagged,
            rating: rating.rating,
            source: "gallery_rating_controls",
          },
          reason: "Queued creative refinement from gallery rating controls",
        }),
      });
    } finally {
      setRefining(false);
    }
  }

  return (
    <div
      className="flex w-full flex-wrap items-center gap-3 rounded-xl bg-black/80 px-4 py-3 backdrop-blur"
      onClick={(e) => e.stopPropagation()}
    >
      {/* Stars */}
      <StarRow
        value={rating.rating}
        onChange={(n) => emit({ rating: n })}
      />

      {/* Approve / Reject / Flag */}
      <div className="flex items-center gap-1.5">
        <Button
          size="xs"
          variant="outline"
          onClick={handleApprove}
          className={
            rating.approved
              ? "border-emerald-500 bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30"
              : "border-zinc-700 text-zinc-400 hover:border-emerald-500/60 hover:text-emerald-400"
          }
        >
          <ThumbsUp className="h-3.5 w-3.5" />
        </Button>

        <Button
          size="xs"
          variant="outline"
          onClick={handleReject}
          className={
            isRejected
              ? "border-red-500 bg-red-500/20 text-red-400 hover:bg-red-500/30"
              : "border-zinc-700 text-zinc-400 hover:border-red-500/60 hover:text-red-400"
          }
        >
          <ThumbsDown className="h-3.5 w-3.5" />
        </Button>

        <Button
          size="xs"
          variant="outline"
          onClick={handleFlag}
          className={
            rating.flagged
              ? "border-amber-500 bg-amber-500/20 text-amber-400 hover:bg-amber-500/30"
              : "border-zinc-700 text-zinc-400 hover:border-amber-500/60 hover:text-amber-400"
          }
        >
          <Wrench className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Notes toggle */}
      <button
        type="button"
        onClick={() => setShowNotes((v) => !v)}
        className="ml-auto flex items-center gap-1 text-[11px] text-zinc-500 transition hover:text-zinc-300"
      >
        Notes
        {showNotes ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </button>

      {/* Refine button — only when flagged */}
      {rating.flagged && (
        <Button
          size="xs"
          variant="outline"
          onClick={() => void handleRefine()}
          disabled={refining}
          className="border-amber-500/50 text-amber-400 hover:bg-amber-500/20"
        >
          <Sparkles className="h-3.5 w-3.5" />
          {refining ? "Sending..." : "Refine"}
        </Button>
      )}

      {/* Notes textarea */}
      {showNotes && (
        <textarea
          value={rating.notes}
          onChange={(e) => emit({ notes: e.target.value })}
          placeholder="Notes for refinement..."
          rows={2}
          className="mt-1 w-full resize-none rounded-lg border border-zinc-700 bg-zinc-900/60 px-3 py-2 text-xs text-zinc-300 placeholder:text-zinc-600 focus:border-amber-500/50 focus:outline-none"
        />
      )}
    </div>
  );
}
