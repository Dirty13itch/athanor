"use client";

import { useState, useCallback } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { config } from "@/lib/config";
import { PushManager } from "@/components/push-manager";

interface Preference {
  score: number;
  content: string;
  signal_type: string;
  agent: string;
  category: string;
  timestamp: string;
}

const SIGNAL_STYLES: Record<string, string> = {
  remember_this: "bg-blue-500/20 text-blue-400",
  thumbs_up: "bg-green-500/20 text-green-400",
  thumbs_down: "bg-red-500/20 text-red-400",
  config_choice: "bg-purple-500/20 text-purple-400",
};

export default function PreferencesPage() {
  const [preferences, setPreferences] = useState<Preference[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterAgent, setFilterAgent] = useState("");
  const [lastSearched, setLastSearched] = useState<Date | null>(null);

  // New preference form
  const [newContent, setNewContent] = useState("");
  const [newAgent, setNewAgent] = useState("global");
  const [newCategory, setNewCategory] = useState("");
  const [newSignalType, setNewSignalType] = useState("remember_this");
  const [storing, setStoring] = useState(false);
  const [storeSuccess, setStoreSuccess] = useState<string | null>(null);

  const searchPreferences = useCallback(async () => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({
        query: searchQuery,
        limit: "20",
      });
      if (filterAgent) params.set("agent", filterAgent);
      const res = await fetch(
        `${config.agentServer.url}/v1/preferences?${params}`
      );
      if (!res.ok) throw new Error(`Failed (${res.status})`);
      const data = await res.json();
      setPreferences(data.preferences || []);
      setError(null);
      setLastSearched(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to search");
    } finally {
      setLoading(false);
    }
  }, [searchQuery, filterAgent]);

  const storePreference = async () => {
    if (!newContent.trim()) return;
    setStoring(true);
    setStoreSuccess(null);
    try {
      const res = await fetch(
        `${config.agentServer.url}/v1/preferences`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            agent: newAgent,
            signal_type: newSignalType,
            content: newContent,
            category: newCategory,
          }),
        }
      );
      if (!res.ok) throw new Error(`Failed (${res.status})`);
      setStoreSuccess(`Stored: "${newContent}"`);
      setNewContent("");
      // Re-search if there's an active query
      if (searchQuery.trim()) {
        setTimeout(searchPreferences, 1000);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to store");
    } finally {
      setStoring(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Preferences</h1>
          <p className="text-muted-foreground">
            What agents know about your preferences — view, search, and add
          </p>
        </div>
      </div>

      {/* Push Notifications */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Notifications</CardTitle>
          <CardDescription>
            Get push notifications for agent escalations and system alerts
          </CardDescription>
        </CardHeader>
        <CardContent>
          <PushManager />
        </CardContent>
      </Card>

      {/* Store new preference */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Add Preference</CardTitle>
          <CardDescription>
            Tell agents what you like, dislike, or want them to remember
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <input
              type="text"
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && storePreference()}
              placeholder="e.g., I prefer 4K quality for movies, I don't like horror"
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground"
            />
            <div className="flex gap-3 items-center">
              <select
                value={newAgent}
                onChange={(e) => setNewAgent(e.target.value)}
                className="rounded-md border border-border bg-card px-3 py-1.5 text-sm text-foreground"
              >
                <option value="global">All agents</option>
                <option value="media-agent">Media Agent</option>
                <option value="home-agent">Home Agent</option>
                <option value="creative-agent">Creative Agent</option>
                <option value="research-agent">Research Agent</option>
                <option value="coding-agent">Coding Agent</option>
              </select>
              <select
                value={newSignalType}
                onChange={(e) => setNewSignalType(e.target.value)}
                className="rounded-md border border-border bg-card px-3 py-1.5 text-sm text-foreground"
              >
                <option value="remember_this">Remember this</option>
                <option value="thumbs_up">Thumbs up</option>
                <option value="thumbs_down">Thumbs down</option>
                <option value="config_choice">Config choice</option>
              </select>
              <input
                type="text"
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                placeholder="Category (optional)"
                className="rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground w-40"
              />
              <button
                onClick={storePreference}
                disabled={storing || !newContent.trim()}
                className="rounded-md bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {storing ? "Storing..." : "Store"}
              </button>
            </div>
            {storeSuccess && (
              <p className="text-xs text-green-400">{storeSuccess}</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Search preferences */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Search Preferences</CardTitle>
          <CardDescription>
            Semantic search across all stored preferences
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && searchPreferences()}
              placeholder="e.g., media quality, dark theme, temperature settings"
              className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground"
            />
            <select
              value={filterAgent}
              onChange={(e) => setFilterAgent(e.target.value)}
              className="rounded-md border border-border bg-card px-3 py-1.5 text-sm text-foreground"
            >
              <option value="">All agents</option>
              <option value="global">Global</option>
              <option value="media-agent">Media Agent</option>
              <option value="home-agent">Home Agent</option>
              <option value="creative-agent">Creative Agent</option>
            </select>
            <button
              onClick={searchPreferences}
              disabled={loading || !searchQuery.trim()}
              className="rounded-md border border-border px-4 py-1.5 text-sm hover:bg-accent transition-colors disabled:opacity-50"
            >
              {loading ? "Searching..." : "Search"}
            </button>
          </div>
          {lastSearched && (
            <p className="text-xs text-muted-foreground mt-2">
              {preferences.length} results found
            </p>
          )}
        </CardContent>
      </Card>

      {error && (
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {preferences.length > 0 && (
        <div className="space-y-2">
          {preferences.map((pref, idx) => (
            <Card key={`${pref.timestamp}-${idx}`}>
              <CardContent className="py-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge
                        className={
                          SIGNAL_STYLES[pref.signal_type] ||
                          "bg-muted text-foreground"
                        }
                      >
                        {pref.signal_type.replace("_", " ")}
                      </Badge>
                      <Badge variant="outline">{pref.agent}</Badge>
                      {pref.category && (
                        <Badge variant="outline">{pref.category}</Badge>
                      )}
                    </div>
                    <p className="text-sm">{pref.content}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-muted-foreground font-mono">
                        relevance: {(pref.score * 100).toFixed(0)}%
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {formatTimestamp(pref.timestamp)}
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function formatTimestamp(ts: string): string {
  try {
    const date = new Date(ts);
    return date.toLocaleString();
  } catch {
    return ts;
  }
}
