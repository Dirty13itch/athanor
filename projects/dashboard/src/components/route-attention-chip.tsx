"use client";

import { useNavAttention } from "@/components/nav-attention-provider";

function getTone(displayTier: "none" | "watch" | "action" | "urgent") {
  switch (displayTier) {
    case "urgent":
      return "danger";
    case "action":
      return "warning";
    case "watch":
      return "info";
    default:
      return "info";
  }
}

export function RouteAttentionChip({ routeHref }: { routeHref: string }) {
  const attention = useNavAttention(routeHref, true);

  if (attention.displayTier === "none" || !attention.reason) {
    return null;
  }

  return (
    <span
      className="status-badge inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium"
      data-tone={getTone(attention.displayTier)}
      title={attention.reason}
    >
      {attention.reason}
    </span>
  );
}
