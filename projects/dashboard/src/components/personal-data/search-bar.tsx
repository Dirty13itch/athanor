"use client";

import { useState, useCallback } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface SearchResult {
  id: string | number;
  score: number;
  title?: string;
  name?: string;
  url?: string;
  source?: string;
  category?: string;
  subcategory?: string;
  folder?: string;
  description?: string;
  type?: string;
}

export function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = useCallback(async () => {
    const trimmed = query.trim();
    if (!trimmed) return;

    setLoading(true);
    setSearched(true);
    try {
      const res = await fetch("/api/personal-data/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed, limit: 20 }),
      });
      if (!res.ok) throw new Error("Search failed");
      const data = await res.json();
      setResults(data.results ?? []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search bookmarks, repos, notes..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            className="pl-9"
          />
        </div>
        <Button onClick={handleSearch} disabled={loading || !query.trim()}>
          {loading ? "Searching..." : "Search"}
        </Button>
      </div>

      {loading && (
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 rounded-lg bg-muted/50 animate-pulse" />
          ))}
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <p className="text-sm text-muted-foreground py-4 text-center">
          No results found for &ldquo;{query}&rdquo;
        </p>
      )}

      {!loading && results.length > 0 && (
        <div className="space-y-2">
          {results.map((result) => (
            <Card key={result.id} className="py-3">
              <CardContent className="px-4 py-0">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      {result.url ? (
                        <a
                          href={result.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm font-medium truncate hover:underline text-primary"
                        >
                          {result.title || result.name || "Untitled"}
                        </a>
                      ) : (
                        <span className="text-sm font-medium truncate">
                          {result.title || result.name || "Untitled"}
                        </span>
                      )}
                      {result.category && (
                        <Badge variant="outline" className="text-[10px] shrink-0">
                          {result.category}
                        </Badge>
                      )}
                      {result.subcategory && (
                        <Badge variant="secondary" className="text-[10px] shrink-0">
                          {result.subcategory}
                        </Badge>
                      )}
                    </div>
                    {result.description && (
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {result.description}
                      </p>
                    )}
                    <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                      {result.source && <span>{result.source}</span>}
                      {result.folder && (
                        <span className="font-mono text-[10px]">{result.folder}</span>
                      )}
                      {result.type && <span>{result.type}</span>}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <span
                      className={`text-xs font-mono ${
                        result.score > 0.8
                          ? "text-green-400"
                          : result.score > 0.6
                          ? "text-yellow-400"
                          : "text-muted-foreground"
                      }`}
                    >
                      {(result.score * 100).toFixed(0)}%
                    </span>
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

function SearchIcon({ className }: { className?: string }) {
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
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  );
}
