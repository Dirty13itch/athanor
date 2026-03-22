"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle, Info } from "lucide-react";
import { cn } from "@/lib/utils";

interface AttentionItem {
  type: string;
  priority: string;
  title: string;
  detail: string;
  action: string;
}

interface AttentionData {
  attention_count: number;
  total_items: number;
  items: AttentionItem[];
}

export function AttentionBanner() {
  const { data } = useQuery<AttentionData>({
    queryKey: ["attention"],
    queryFn: () => fetch("/api/attention").then((r) => r.json()),
    refetchInterval: 60_000,
  });

  if (!data || data.total_items === 0) {
    return (
      <div className="surface-card rounded-2xl border border-border/50 px-4 py-3 flex items-center gap-3">
        <CheckCircle className="h-4 w-4 text-emerald-400 shrink-0" />
        <span className="text-sm text-muted-foreground">Nothing needs your attention right now.</span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {data.items.map((item, i) => (
        <div
          key={i}
          className={cn(
            "rounded-2xl border px-4 py-3 flex items-start gap-3",
            item.priority === "high"
              ? "border-red-500/30 bg-red-950/20"
              : item.priority === "medium"
              ? "border-amber-500/30 bg-amber-950/20"
              : "border-border/50 bg-background/40"
          )}
        >
          {item.priority === "high" ? (
            <AlertTriangle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
          ) : item.priority === "medium" ? (
            <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
          ) : (
            <Info className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
          )}
          <div className="min-w-0">
            <p className="text-sm font-medium">{item.title}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{item.detail}</p>
            <p className="text-xs text-primary/70 mt-1">{item.action}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
