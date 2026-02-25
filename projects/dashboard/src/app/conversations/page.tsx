"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { config } from "@/lib/config";

interface Conversation {
  agent: string;
  user_message: string;
  assistant_response: string;
  tools_used: string[];
  duration_ms: number | null;
  thread_id: string;
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
  "stash-agent": "bg-fuchsia-500/20 text-fuchsia-400",
};

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [filterAgent, setFilterAgent] = useState<string>("");
  const [limit, setLimit] = useState(20);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const fetchConversations = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limit: limit.toString() });
      if (filterAgent) params.set("agent", filterAgent);
      const res = await fetch(
        `${config.agentServer.url}/v1/conversations?${params}`
      );
      if (!res.ok) throw new Error(`Failed (${res.status})`);
      const data = await res.json();
      setConversations(data.conversations || []);
      setError(null);
      setLastUpdated(new Date());
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Failed to fetch conversations"
      );
    } finally {
      setLoading(false);
    }
  }, [filterAgent, limit]);

  useEffect(() => {
    fetchConversations();
    const id = setInterval(fetchConversations, 15000);
    return () => clearInterval(id);
  }, [fetchConversations]);

  const agents = [...new Set(conversations.map((c) => c.agent))].sort();

  const toggleExpand = (idx: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Conversations</h1>
          <p className="text-muted-foreground">
            Logged agent conversations with semantic search
          </p>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <p className="text-xs text-muted-foreground">
              Updated {lastUpdated.toLocaleTimeString()}
            </p>
          )}
          <Badge variant="outline">{conversations.length} conversations</Badge>
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
            <p className="text-sm text-muted-foreground">
              Loading conversations...
            </p>
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

      {!loading && conversations.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-sm text-muted-foreground">
              No conversations recorded yet. Chat with an agent to see history
              here.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Conversation list */}
      <div className="space-y-3">
        {conversations.map((conv, idx) => {
          const isExpanded = expanded.has(idx);
          return (
            <Card
              key={`${conv.timestamp}-${idx}`}
              className="cursor-pointer transition-colors hover:bg-accent/50"
              onClick={() => toggleExpand(idx)}
            >
              <CardContent className="py-3">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 pt-1">
                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                      <UserIcon className="h-4 w-4 text-primary" />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge
                        className={
                          AGENT_COLORS[conv.agent] ||
                          "bg-muted text-foreground"
                        }
                      >
                        {conv.agent}
                      </Badge>
                      {conv.duration_ms && (
                        <span className="text-xs text-muted-foreground">
                          {conv.duration_ms < 1000
                            ? `${conv.duration_ms}ms`
                            : `${(conv.duration_ms / 1000).toFixed(1)}s`}
                        </span>
                      )}
                      {conv.tools_used.length > 0 && (
                        <div className="flex gap-1">
                          {conv.tools_used.map((tool) => (
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
                      <span className="ml-auto text-xs text-muted-foreground">
                        {formatTimestamp(conv.timestamp)}
                      </span>
                    </div>

                    {/* User message */}
                    <p className="text-sm text-foreground">
                      {conv.user_message}
                    </p>

                    {/* Agent response (expandable) */}
                    {isExpanded && conv.assistant_response && (
                      <div className="mt-3 rounded-md border border-border bg-muted/50 p-3">
                        <div className="flex items-center gap-2 mb-2">
                          <div className="h-5 w-5 rounded-full bg-accent flex items-center justify-center">
                            <BotSmallIcon className="h-3 w-3 text-accent-foreground" />
                          </div>
                          <span className="text-xs font-medium text-muted-foreground">
                            {formatAgentName(conv.agent)}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                          {conv.assistant_response}
                        </p>
                      </div>
                    )}

                    {!isExpanded && conv.assistant_response && (
                      <p className="text-xs text-muted-foreground mt-1 truncate">
                        {conv.assistant_response}
                      </p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function formatAgentName(name: string): string {
  return name
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
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

function UserIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

function BotSmallIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M12 8V4H8" />
      <rect width="16" height="12" x="4" y="8" rx="2" />
      <path d="M2 14h2" />
      <path d="M20 14h2" />
      <path d="M15 13v2" />
      <path d="M9 13v2" />
    </svg>
  );
}
