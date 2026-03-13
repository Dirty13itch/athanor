import { Badge } from "@/components/ui/badge";
import { formatRelativeTime } from "@/lib/format";
import { formatRefreshCadence } from "@/lib/live-updates";

export function LiveBadge({
  updatedAt,
  intervalMs,
}: {
  updatedAt: string | null | undefined;
  intervalMs: number;
}) {
  const recency = updatedAt ? formatRelativeTime(updatedAt) : "syncing";

  return (
    <Badge variant="outline" className="status-badge gap-2 border-white/15 bg-white/5 text-foreground" data-tone="success">
      <span className="inline-flex h-2 w-2 rounded-full bg-[color:var(--signal-success)] shadow-[0_0_12px_color-mix(in_oklab,var(--signal-success)_55%,transparent)]" />
      <span>Live</span>
      <span className="text-muted-foreground">/{formatRefreshCadence(intervalMs)}</span>
      <span className="text-muted-foreground">{recency}</span>
    </Badge>
  );
}
