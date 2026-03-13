"use client";

import Link from "next/link";
import { useDeferredValue, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bell, Database, RefreshCcw, Search } from "lucide-react";
import { FamilyTabs } from "@/components/family-tabs";
import { ConsolidationCard } from "@/components/consolidation-card";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { SearchBar } from "@/components/personal-data/search-bar";
import { PushManager } from "@/components/push-manager";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { StatCard } from "@/components/stat-card";
import { getMemory } from "@/lib/api";
import { type MemorySnapshot } from "@/lib/contracts";
import { formatRelativeTime, formatTimestamp } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import { useUrlState } from "@/lib/url-state";

const TABS = [
  { href: "/preferences", label: "Preferences" },
  { href: "/personal-data", label: "Personal Data" },
];

type MemoryVariant = "preferences" | "personal-data";

function inferProjectIdFromMemory(text: string) {
  const normalized = text.toLowerCase();
  if (
    normalized.includes("eoq") ||
    normalized.includes("eobq") ||
    normalized.includes("empire of broken queens") ||
    normalized.includes("broken queens")
  ) {
    return "eoq";
  }
  if (normalized.includes("kindred")) {
    return "kindred";
  }
  if (normalized.includes("media")) {
    return "media";
  }
  return "athanor";
}

function getProjectName(snapshot: MemorySnapshot, projectId: string) {
  return snapshot.projects.find((project) => project.id === projectId)?.name ?? projectId;
}

export function MemoryConsole({
  initialSnapshot,
  variant,
}: {
  initialSnapshot: MemorySnapshot;
  variant: MemoryVariant;
}) {
  const { getSearchValue, setSearchValue } = useUrlState();
  const query = getSearchValue("query", "");
  const project = getSearchValue("project", "all");
  const agent = getSearchValue("agent", "all");
  const category = getSearchValue("category", "all");
  const entity = getSearchValue("entity", "");
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());
  const [newPreference, setNewPreference] = useState("");
  const [newAgent, setNewAgent] = useState("global");
  const [newCategory, setNewCategory] = useState("");
  const [newSignalType, setNewSignalType] = useState("remember_this");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const memoryQuery = useQuery({
    queryKey: queryKeys.memory,
    queryFn: getMemory,
    initialData: initialSnapshot,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  async function storePreference() {
    if (!newPreference.trim()) {
      return;
    }

    setSaving(true);
    setFeedback(null);
    try {
      const response = await fetch("/api/preferences", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agent: newAgent,
          signal_type: newSignalType,
          content: newPreference.trim(),
          category: newCategory,
        }),
      });
      if (!response.ok) {
        throw new Error(`Request failed (${response.status})`);
      }
      setNewPreference("");
      setNewCategory("");
      await memoryQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Failed to store preference.");
    } finally {
      setSaving(false);
    }
  }

  if (memoryQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Memory" title="Memory Console" description="The memory snapshot failed to load." />
        <ErrorPanel
          description={
            memoryQuery.error instanceof Error ? memoryQuery.error.message : "Failed to load memory snapshot."
          }
        />
      </div>
    );
  }

  const snapshot = memoryQuery.data ?? initialSnapshot;
  const filteredPreferences = snapshot.preferences.filter((preference) => {
    const projectId = inferProjectIdFromMemory(preference.content);
    const text = `${preference.content} ${preference.signalType} ${preference.category ?? ""}`.toLowerCase();
    return (
      (project === "all" || projectId === project) &&
      (agent === "all" || preference.agentId === agent) &&
      (category === "all" || (preference.category ?? "uncategorized") === category) &&
      (!deferredQuery || text.includes(deferredQuery))
    );
  });
  const filteredItems = snapshot.recentItems.filter((item) => {
    const projectId = inferProjectIdFromMemory(`${item.title} ${item.description ?? ""}`);
    const text = `${item.title} ${item.description ?? ""} ${item.category ?? ""} ${item.subcategory ?? ""}`.toLowerCase();
    return (
      (project === "all" || projectId === project) &&
      (category === "all" || (item.category ?? "uncategorized") === category) &&
      (!deferredQuery || text.includes(deferredQuery))
    );
  });
  const selectedItem = filteredItems.find((item) => `${item.id}` === entity) ?? null;
  const title = variant === "preferences" ? "Preferences" : "Personal Data";
  const description =
    variant === "preferences"
      ? "Operator memory, preference capture, and notification preferences."
      : "Semantic search, graph memory, and indexed personal knowledge.";

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Memory"
        title={title}
        description={description}
        actions={
          <Button variant="outline" onClick={() => void memoryQuery.refetch()} disabled={memoryQuery.isFetching}>
            <RefreshCcw className={`mr-2 h-4 w-4 ${memoryQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      >
        <div className="space-y-4">
          <FamilyTabs tabs={TABS} />
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Qdrant" value={snapshot.summary.qdrantOnline ? "Online" : "Offline"} detail={`${snapshot.summary.points} points`} tone={snapshot.summary.qdrantOnline ? "success" : "warning"} />
            <StatCard label="Neo4j" value={snapshot.summary.neo4jOnline ? "Online" : "Offline"} detail={`${snapshot.summary.graphNodes} graph nodes`} tone={snapshot.summary.neo4jOnline ? "success" : "warning"} />
            <StatCard label="Preferences" value={`${snapshot.preferences.length}`} detail="Operator memory signals currently surfaced." />
            <StatCard label="Featured project" value="EoBQ" detail="Primary tenant context for project-aware memory." />
          </div>
        </div>
      </PageHeader>

      {feedback ? <ErrorPanel title="Memory action" description={feedback} /> : null}

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.35fr]">
        <Card className="surface-panel">
          <CardHeader>
            <CardTitle className="text-lg">Shared filters</CardTitle>
            <CardDescription>Memory routes share project, category, query, and entity state.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(event) => setSearchValue("query", event.target.value || null)}
                placeholder={`Search ${variant === "preferences" ? "preferences" : "memory"}`}
                className="surface-instrument pl-9"
              />
            </div>
            <FilterRow
              label="Project"
              values={[{ id: "all", label: "All" }, ...snapshot.projects.map((projectEntry) => ({ id: projectEntry.id, label: projectEntry.id === "eoq" ? `${projectEntry.name} (Featured)` : projectEntry.name }))]}
              activeValue={project}
              onChange={(value) => setSearchValue("project", value === "all" ? null : value)}
            />
            <FilterRow
              label="Agent"
              values={[
                { id: "all", label: "All" },
                { id: "global", label: "Global" },
                ...Array.from(new Set(snapshot.preferences.map((preference) => preference.agentId)))
                  .filter((value) => value !== "global")
                  .map((value) => ({ id: value, label: value })),
              ]}
              activeValue={agent}
              onChange={(value) => setSearchValue("agent", value === "all" ? null : value)}
            />
            <FilterRow
              label="Category"
              values={[
                { id: "all", label: "All" },
                ...snapshot.categories.map((categoryEntry) => ({ id: categoryEntry.name, label: `${categoryEntry.name} (${categoryEntry.count})` })),
              ]}
              activeValue={category}
              onChange={(value) => setSearchValue("category", value === "all" ? null : value)}
            />
          </CardContent>
        </Card>

        <Card className="surface-hero">
          <CardHeader>
            <CardTitle className="text-lg">Knowledge posture</CardTitle>
            <CardDescription>Recent indexing, graph coverage, and operator preference signals.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            <Metric label="Vectors" value={`${snapshot.summary.vectors}`} />
            <Metric label="Relationships" value={`${snapshot.summary.graphRelationships}`} />
            <Metric label="Last snapshot" value={formatRelativeTime(snapshot.generatedAt)} />
          </CardContent>
        </Card>
      </div>

      {variant === "preferences" ? (
        <>
          <Card className="surface-panel">
            <CardHeader>
              <CardTitle className="text-lg">Preference capture</CardTitle>
              <CardDescription>Store operator signals and keep notification preferences close to memory management.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input
                value={newPreference}
                onChange={(event) => setNewPreference(event.target.value)}
                placeholder="Store a new operator preference or constraint"
                className="surface-instrument"
              />
              <div className="grid gap-3 md:grid-cols-3">
                <select
                  value={newAgent}
                  onChange={(event) => setNewAgent(event.target.value)}
                  aria-label="Preference target agent"
                  className="surface-instrument rounded-xl border px-3 py-2 text-sm"
                >
                  <option value="global">Global</option>
                  <option value="coding-agent">coding-agent</option>
                  <option value="creative-agent">creative-agent</option>
                  <option value="knowledge-agent">knowledge-agent</option>
                  <option value="media-agent">media-agent</option>
                </select>
                <select
                  value={newSignalType}
                  onChange={(event) => setNewSignalType(event.target.value)}
                  aria-label="Preference signal type"
                  className="surface-instrument rounded-xl border px-3 py-2 text-sm"
                >
                  <option value="remember_this">remember_this</option>
                  <option value="thumbs_up">thumbs_up</option>
                  <option value="thumbs_down">thumbs_down</option>
                  <option value="config_choice">config_choice</option>
                </select>
                <Input
                  value={newCategory}
                  onChange={(event) => setNewCategory(event.target.value)}
                  placeholder="Category"
                  className="surface-instrument"
                />
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <Button onClick={() => void storePreference()} disabled={saving || !newPreference.trim()}>
                  Store preference
                </Button>
                <div className="surface-instrument flex items-center gap-2 rounded-xl border px-3 py-2 text-sm">
                  <Bell className="h-4 w-4 text-primary" />
                  <PushManager />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="surface-panel">
            <CardHeader>
              <CardTitle className="text-lg">Stored preferences</CardTitle>
              <CardDescription>{filteredPreferences.length} preference signals match the current filters.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {filteredPreferences.length > 0 ? (
                filteredPreferences.map((preference) => (
                  <div key={`${preference.timestamp}-${preference.content}`} className="surface-instrument rounded-2xl border p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="secondary">{preference.signalType}</Badge>
                      <Badge variant="outline">{preference.agentId}</Badge>
                      {preference.category ? <Badge variant="outline">{preference.category}</Badge> : null}
                      <span className="ml-auto text-xs text-muted-foreground">{formatRelativeTime(preference.timestamp)}</span>
                    </div>
                    <p className="mt-3 text-sm">{preference.content}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Button asChild size="sm" variant="outline">
                        <Link href={`/workplanner?project=${inferProjectIdFromMemory(preference.content)}`}>
                          Open project
                        </Link>
                      </Button>
                    </div>
                  </div>
                ))
              ) : (
                <EmptyState title="No preferences match the current filters" description="Try a different category or clear the project filter." />
              )}
            </CardContent>
          </Card>
        </>
      ) : null}

      {variant === "personal-data" ? (
        <>
          <Card className="surface-panel">
            <CardHeader>
              <CardTitle className="text-lg">Semantic search</CardTitle>
              <CardDescription>Use the existing semantic search surface underneath the shared memory model.</CardDescription>
            </CardHeader>
            <CardContent>
              <SearchBar />
            </CardContent>
          </Card>

          <ConsolidationCard />

          <div className="grid gap-4 xl:grid-cols-[1.25fr_0.9fr]">
            <Card className="surface-panel">
              <CardHeader>
                <CardTitle className="text-lg">Recently indexed</CardTitle>
                <CardDescription>{filteredItems.length} items match the current filters.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {filteredItems.length > 0 ? (
                  filteredItems.map((item) => (
                    <button
                      key={`${item.id}`}
                      type="button"
                      onClick={() => setSearchValue("entity", `${item.id}`)}
                      className="surface-instrument w-full rounded-2xl border p-4 text-left transition hover:bg-accent/40"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="secondary">{item.category ?? "uncategorized"}</Badge>
                        {item.subcategory ? <Badge variant="outline">{item.subcategory}</Badge> : null}
                        <span className="ml-auto text-xs text-muted-foreground">{item.indexedAt ? formatRelativeTime(item.indexedAt) : "Unknown"}</span>
                      </div>
                      <p className="mt-3 text-sm font-medium">{item.title}</p>
                      {item.description ? <p className="mt-2 text-sm text-muted-foreground">{item.description}</p> : null}
                    </button>
                  ))
                ) : (
                  <EmptyState title="No indexed items match the current filters" description="Clear the query or widen the category filter." />
                )}
              </CardContent>
            </Card>

            <Card className="surface-panel">
              <CardHeader>
                <CardTitle className="text-lg">Top topics</CardTitle>
                <CardDescription>Graph-backed topics and category density from the current snapshot.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {snapshot.topTopics.map((topic) => (
                  <div key={topic.name} className="surface-metric flex items-center justify-between rounded-xl border px-3 py-2 text-sm">
                    <span>{topic.name}</span>
                    <span className="text-muted-foreground">{topic.connections} links</span>
                  </div>
                ))}
                <div className="flex flex-wrap gap-2 pt-2">
                  {snapshot.graphLabels.map((label) => (
                    <Badge key={label} variant="outline">
                      {label}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      ) : null}

      <Sheet open={Boolean(selectedItem)} onOpenChange={(open) => setSearchValue("entity", open ? entity : null)}>
        <SheetContent side="right" className="w-full max-w-xl overflow-y-auto border-l border-border/80 bg-background/95">
          {selectedItem ? (
            <>
              <SheetHeader className="border-b border-border/80 px-6 py-5 text-left">
                <SheetTitle>{selectedItem.title}</SheetTitle>
                <SheetDescription>{selectedItem.description ?? selectedItem.category ?? "Indexed memory item"}</SheetDescription>
              </SheetHeader>
              <div className="space-y-6 p-6">
                <div className="grid gap-3 md:grid-cols-2">
                  <Metric label="Project" value={getProjectName(snapshot, inferProjectIdFromMemory(`${selectedItem.title} ${selectedItem.description ?? ""}`))} />
                  <Metric label="Indexed" value={selectedItem.indexedAt ? formatTimestamp(selectedItem.indexedAt) : "Unknown"} />
                </div>
                {selectedItem.url ? (
                  <Button asChild size="sm" variant="outline">
                    <a href={selectedItem.url} target="_blank" rel="noopener noreferrer">
                      <Database className="mr-2 h-4 w-4" />
                      Open source
                    </a>
                  </Button>
                ) : null}
                <Section label="Back-links">
                  <div className="flex flex-wrap gap-2">
                    <Button asChild size="sm" variant="outline">
                      <Link href={`/workplanner?project=${inferProjectIdFromMemory(`${selectedItem.title} ${selectedItem.description ?? ""}`)}`}>
                        Open project
                      </Link>
                    </Button>
                    <Button asChild size="sm" variant="outline">
                      <Link href="/preferences?project=athanor">Preference view</Link>
                    </Button>
                  </div>
                </Section>
              </div>
            </>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function FilterRow({
  label,
  values,
  activeValue,
  onChange,
}: {
  label: string;
  values: Array<{ id: string; label: string }>;
  activeValue: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
      <div className="flex flex-wrap gap-2">
        {values.map((value) => (
          <Button
            key={value.id}
            size="sm"
            variant={activeValue === value.id ? "default" : "outline"}
            onClick={() => onChange(value.id)}
          >
            {value.label}
          </Button>
        ))}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="surface-metric rounded-xl border px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 font-medium">{value}</p>
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <div className="surface-instrument mt-2 rounded-xl border p-3 text-sm">
        {children}
      </div>
    </div>
  );
}
