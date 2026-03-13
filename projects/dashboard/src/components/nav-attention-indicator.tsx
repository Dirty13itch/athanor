"use client";

import { cn } from "@/lib/utils";
import type { NavAttentionPresentation } from "@/lib/nav-attention";

function formatCount(count: number | null) {
  if (typeof count !== "number" || count <= 0) {
    return null;
  }
  return count > 99 ? "99+" : String(count);
}

export function NavAttentionIndicator({
  attention,
  className,
}: {
  attention: NavAttentionPresentation;
  className?: string;
}) {
  if (attention.displayTier === "none" || attention.activeSurface) {
    return null;
  }

  const countLabel = formatCount(attention.count);

  if (attention.displayTier === "watch" && !countLabel) {
    return (
      <span
        aria-hidden="true"
        className={cn("nav-attention-marker", className)}
        data-tier="watch"
      />
    );
  }

  return (
    <span
      className={cn(
        "nav-attention-indicator",
        attention.pulseIndicator && "nav-attention-indicator--pulse",
        attention.settled && "nav-attention-indicator--settled",
        className
      )}
      data-tier={attention.displayTier}
      title={attention.reason ?? undefined}
    >
      {countLabel ?? "!"}
    </span>
  );
}
