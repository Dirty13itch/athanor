"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, Bot, Wrench, Brain, Search, Palette, Database, Home, Film, Shield } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { ChevronRight } from "lucide-react";

interface ActivityItem {
  agent: string;
  action_type: string;
  input_summary: string;
  output_summary?: string;
  status?: string;
  timestamp?: string;
  created_at?: string;
}

const agentIcon: Record<string, typeof Bot> = {
  "general-assistant": Bot,
  "media-agent": Film,
  "research-agent": Search,
  "creative-agent": Palette,
  "knowledge-agent": Brain,
  "home-agent": Home,
  "coding-agent": Wrench,
  "stash-agent": Shield,
  "data-curator": Database,
};

function timeAgo(ts: string | undefined): string {
  if (!ts) return "";
  const diff = Date.now() - new Date(ts).getTime();
  if (diff < 60_000) return "just now";
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86400_000) return `${Math.floor(diff / 3600_000)}h ago`;
  return `${Math.floor(diff / 86400_000)}d ago`;
}

export function LiveActivityPanel() {
  const { data } = useQuery<{ activity: ActivityItem[] }>({
    queryKey: ["live-activity"],
    queryFn: () => fetch("/api/activity").then((r) => r.json()),
    refetchInterval: 30_000,
  });

  const items = (data?.activity ?? []).slice(0, 8);

  return (
    <Card className="surface-panel">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            Live Agent Activity
          </CardTitle>
          <p className="text-xs text-muted-foreground mt-0.5">What agents are doing right now</p>
        </div>
        <Link href="/activity" className="text-xs text-primary hover:underline flex items-center gap-1">
          Full history <ChevronRight className="h-3 w-3" />
        </Link>
      </CardHeader>
      <CardContent className="space-y-1.5">
        {items.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-4">No recent activity.</p>
        )}
        {items.map((item, i) => {
          const Icon = agentIcon[item.agent] ?? Bot;
          const ts = item.timestamp || item.created_at;
          return (
            <div key={i} className="flex items-start gap-2.5 rounded-lg px-2 py-1.5 hover:bg-background/40 transition-colors">
              <Icon className="h-3.5 w-3.5 text-muted-foreground shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1">
                <p className="text-xs leading-snug">
                  <span className="font-medium text-foreground">{item.agent}</span>
                  <span className="text-muted-foreground"> · {item.action_type} · </span>
                  <span className="text-muted-foreground">{(item.input_summary || "").slice(0, 80)}</span>
                </p>
              </div>
              <span className="text-[10px] text-muted-foreground shrink-0">{timeAgo(ts)}</span>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
