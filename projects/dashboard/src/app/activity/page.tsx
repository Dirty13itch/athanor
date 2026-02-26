"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { config } from "@/lib/config";
import { FeedbackButtons } from "@/components/gen-ui/feedback-buttons";

interface ActivityItem {
  agent: string;
  action_type: string;
  input_summary: string;
  output_summary: string;
  tools_used: string[];
  duration_ms: number | null;
  timestamp: string;
}

const AGENT_COLORS: Record<string, string> = {
  "general-assistant": "bg-blue-500/20 text-blue-400",
  "media-agent": "bg-purple-500/20 text-purple-400",
  "research-agent": "bg-green-500/20 text-green-400",
  "creative-agent": "bg-pink-500/20 text-pink-400",
  "knowledge-agent": "bg-yellow-500/20 text-yellow-400",
  "home-agent": "bg-orange-500/20 text-orange-400",
  "coding-agent": "bg-cyan-500/20 text-cyan-400",
};

export default function ActivityPage() {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [filterAgent, setFilterAgent] = useState<string>("");
  const [limit, setLimit] = useState(50);

  const fetchActivity = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limit: limit.toString() });
      if (filterAgent) params.set("agent", filterAgent);
      const res = await fetch(
        `${config.agentServer.url}/v1/activity?${params}`
      );
      if (!res.ok) throw new Error(`Failed (${res.status})`);
      const data = await res.json();
      setItems(data.activity || []);
      setError(null);
      setLastUpdated(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch activity");
    } finally {
      setLoading(false);
    }
  }, [filterAgent, limit]);

  useEffect(() => {
    fetchActivity();
    const id = setInterval(fetchActivity, 15000);
    return () => clearInterval(id);
  }, [fetchActivity]);

  const agents = [...new Set(items.map((i) => i.agent))].sort();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Activity Feed</h1>
          <p className="text-muted-foreground">
            Every agent action, searchable and filterable
          </p>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <p className="text-xs text-muted-foreground">
              Updated {lastUpdated.toLocaleTimeString()}
            </p>
          )}
          <Badge variant="outline">{items.length} events</Badge>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <select
          value={filterAgent}
          onChange={(e) => setFilterAgent(e.target.value)}
          className="rounded-md border border-border bg-card px-3 py-1.5 text-sm text-foreground"
        >
          <option value="">All agents</option>
          {agents.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
        <select
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="rounded-md border border-border bg-card px-3 py-1.5 text-sm text-foreground"
        >
          <option value={20}>Last 20</option>
          <option value={50}>Last 50</option>
          <option value={100}>Last 100</option>
        </select>
      </div>

      {loading && (
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-muted-foreground">Loading activity...</p>
          </CardContent>
        </Card>
      )}

      {error && (
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {!loading && items.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-sm text-muted-foreground">
              No activity recorded yet. Start chatting with an agent.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Activity timeline */}
      <div className="space-y-2">
        {items.map((item, idx) => (
          <Card key={`${item.timestamp}-${idx}`}>
            <CardContent className="py-3">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 pt-0.5">
                  <div className="h-2.5 w-2.5 rounded-full bg-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge
                      className={
                        AGENT_COLORS[item.agent] || "bg-muted text-foreground"
                      }
                    >
                      {item.agent}
                    </Badge>
                    <span className="text-xs text-muted-foreground font-mono">
                      {item.action_type}
                    </span>
                    {item.duration_ms && (
                      <span className="text-xs text-muted-foreground">
                        {item.duration_ms < 1000
                          ? `${item.duration_ms}ms`
                          : `${(item.duration_ms / 1000).toFixed(1)}s`}
                      </span>
                    )}
                    <span className="ml-auto text-xs text-muted-foreground">
                      {formatTimestamp(item.timestamp)}
                    </span>
                  </div>
                  <p className="text-sm text-foreground truncate">
                    {item.input_summary}
                  </p>
                  {item.output_summary && (
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                      {item.output_summary}
                    </p>
                  )}
                  {item.tools_used.length > 0 && (
                    <div className="flex gap-1 mt-1">
                      {item.tools_used.map((tool) => (
                        <Badge
                          key={tool}
                          variant="outline"
                          className="text-xs"
                        >
                          {tool}
                        </Badge>
                      ))}
                    </div>
                  )}
                  <FeedbackButtons
                    messageContent={`${item.action_type}: ${item.input_summary}${item.output_summary ? ` → ${item.output_summary}` : ""}`}
                    agent={item.agent}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function formatTimestamp(ts: string): string {
  try {
    const date = new Date(ts);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);

    if (diffMin < 1) return "just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffMin < 1440) return `${Math.floor(diffMin / 60)}h ago`;
    return date.toLocaleDateString();
  } catch {
    return ts;
  }
}
