"use client";

import { cn } from "@/lib/utils";
import type { NavAttentionPresentation } from "@/lib/nav-attention";

function splitGraphemes(value: string) {
  if (typeof Intl !== "undefined" && "Segmenter" in Intl) {
    const segmenter = new Intl.Segmenter(undefined, { granularity: "grapheme" });
    return Array.from(segmenter.segment(value), (segment) => segment.segment);
  }

  return Array.from(value);
}

export function NavAttentionLabel({
  label,
  attention,
}: {
  label: string;
  attention: NavAttentionPresentation;
}) {
  if (attention.displayTier === "urgent" && attention.animateSweep) {
    const graphemes = splitGraphemes(label);
    return (
      <span
        aria-label={label}
        className={cn(
          "nav-attention-label nav-attention-label--urgent",
          attention.settled && "nav-attention-label--settled"
        )}
      >
        {graphemes.map((grapheme, index) => (
          <span
            key={`${grapheme}-${index}`}
            aria-hidden="true"
            className="nav-attention-char"
            style={{ ["--char-index" as string]: index }}
          >
            {grapheme === " " ? "\u00A0" : grapheme}
          </span>
        ))}
      </span>
    );
  }

  return (
    <span
      className={cn(
        "nav-attention-label",
        attention.displayTier === "action" && "nav-attention-label--action",
        attention.displayTier === "watch" && "nav-attention-label--watch"
      )}
    >
      {label}
    </span>
  );
}
