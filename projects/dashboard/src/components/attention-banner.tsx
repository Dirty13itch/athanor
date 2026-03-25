"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle, Info, ShieldAlert, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types matching the proactive API response
// ---------------------------------------------------------------------------

interface AttentionItem {
  id: string;
  severity: "critical" | "warning" | "info";
  category: "capacity" | "quality" | "performance" | "security" | "cost";
  title: string;
  detail: string;
  action?: string;
  href?: string;
  source: string;
  timestamp: string;
}

interface ProactiveResponse {
  generated_at: string;
  total_items: number;
  severity_counts: { critical: number; warning: number; info: number };
  items: AttentionItem[];
}

// Also support the legacy shape from /api/attention
interface LegacyItem {
  type: string;
  priority: string;
  title: string;
  detail: string;
  action: string;
}
interface LegacyResponse {
  attention_count: number;
  total_items: number;
  items: LegacyItem[];
}

// ---------------------------------------------------------------------------
// Severity styling
// ---------------------------------------------------------------------------

const SEVERITY_STYLES: Record<
  string,
  { border: string; bg: string; icon: React.ReactNode }
> = {
  critical: {
    border: "border-red-500/40",
    bg: "bg-red-950/30",
    icon: <ShieldAlert className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />,
  },
  warning: {
    border: "border-amber-500/30",
    bg: "bg-amber-950/20",
    icon: <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />,
  },
  info: {
    border: "border-border/50",
    bg: "bg-background/40",
    icon: <Info className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />,
  },
};

const CATEGORY_LABELS: Record<string, { icon: React.ReactNode; label: string }> = {
  capacity: { icon: <Zap className="h-3 w-3" />, label: "Capacity" },
  quality: { icon: <ShieldAlert className="h-3 w-3" />, label: "Quality" },
  performance: { icon: <Zap className="h-3 w-3" />, label: "Performance" },
  security: { icon: <ShieldAlert className="h-3 w-3" />, label: "Security" },
  cost: { icon: <Info className="h-3 w-3" />, label: "Cost" },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AttentionBanner() {
  // Fetch from proactive endpoint (aggregates all sources)
  const proactive = useQuery<ProactiveResponse>({
    queryKey: ["attention", "proactive"],
    queryFn: () => fetch("/api/attention/proactive").then((r) => r.json()),
    refetchInterval: 30_000,
  });

  // Also keep the legacy governor-only attention as fallback
  const legacy = useQuery<LegacyResponse>({
    queryKey: ["attention"],
    queryFn: () => fetch("/api/attention").then((r) => r.json()),
    refetchInterval: 60_000,
  });

  // Merge: proactive items take priority, legacy items fill in
  const proactiveItems: AttentionItem[] = proactive.data?.items ?? [];
  const legacyMapped: AttentionItem[] = (legacy.data?.items ?? []).map((item, i) => ({
    id: `legacy-${i}`,
    severity:
      item.priority === "high"
        ? "warning"
        : item.priority === "medium"
          ? "info"
          : "info",
    category: "performance" as const,
    title: item.title,
    detail: item.detail,
    action: item.action || undefined,
    source: "governor",
    timestamp: new Date().toISOString(),
  }));

  // Deduplicate: if proactive has items, use those; otherwise fall back to legacy
  const items = proactiveItems.length > 0 ? proactiveItems : legacyMapped;

  if (items.length === 0) {
    return (
      <div className="surface-card rounded-2xl border border-border/50 px-4 py-3 flex items-center gap-3">
        <CheckCircle className="h-4 w-4 text-emerald-400 shrink-0" />
        <span className="text-sm text-muted-foreground">
          Nothing needs your attention right now.
        </span>
      </div>
    );
  }

  // Show summary header when there are critical items
  const criticalCount = proactive.data?.severity_counts?.critical ?? 0;
  const warningCount = proactive.data?.severity_counts?.warning ?? 0;

  return (
    <div className="space-y-2">
      {(criticalCount > 0 || warningCount > 0) && (
        <div
          className={cn(
            "rounded-2xl border px-4 py-2 flex items-center gap-3 text-sm",
            criticalCount > 0
              ? "border-red-500/40 bg-red-950/20 text-red-300"
              : "border-amber-500/30 bg-amber-950/15 text-amber-300",
          )}
        >
          {criticalCount > 0 ? (
            <ShieldAlert className="h-4 w-4 shrink-0" />
          ) : (
            <AlertTriangle className="h-4 w-4 shrink-0" />
          )}
          <span className="font-medium">
            {criticalCount > 0 && `${criticalCount} critical`}
            {criticalCount > 0 && warningCount > 0 && ", "}
            {warningCount > 0 && `${warningCount} warning${warningCount > 1 ? "s" : ""}`}
            {" \u2014 "}
            {items.length} total item{items.length > 1 ? "s" : ""} need attention
          </span>
        </div>
      )}

      {items.map((item) => {
        const style = SEVERITY_STYLES[item.severity] ?? SEVERITY_STYLES.info;
        const cat = CATEGORY_LABELS[item.category];

        const content = (
          <div
            className={cn(
              "rounded-2xl border px-4 py-3 flex items-start gap-3 transition",
              style.border,
              style.bg,
              item.href && "hover:bg-accent/60 cursor-pointer",
            )}
          >
            {style.icon}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium">{item.title}</p>
                {cat && (
                  <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider text-muted-foreground bg-muted/50 rounded-full px-2 py-0.5">
                    {cat.label}
                  </span>
                )}
              </div>
              {item.detail && (
                <p className="text-xs text-muted-foreground mt-0.5">{item.detail}</p>
              )}
              {item.action && (
                <p className="text-xs text-primary/70 mt-1">{item.action}</p>
              )}
              <p className="text-[10px] text-muted-foreground/50 mt-1">
                via {item.source}
              </p>
            </div>
          </div>
        );

        if (item.href) {
          return (
            <Link key={item.id} href={item.href}>
              {content}
            </Link>
          );
        }
        return <div key={item.id}>{content}</div>;
      })}
    </div>
  );
}
