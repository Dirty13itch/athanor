"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Lightbulb, RefreshCcw, Rocket, Sparkles, Target } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { formatRelativeTime } from "@/lib/format";
import { postJson, requestJson } from "@/features/workforce/helpers";

type IdeaStatus = "all" | "seed" | "sprout" | "candidate" | "promoted" | "discarded";

interface OperatorIdea {
  id: string;
  title: string;
  note: string;
  tags: string[];
  source: string;
  confidence: number;
  energy_class: string;
  scope_guess: string;
  status: Exclude<IdeaStatus, "all">;
  created_at: number;
  updated_at: number;
}

interface OperatorSummary {
  ideas?: {
    total?: number;
    by_status?: Record<string, number>;
  };
}

const STATUS_FILTERS: IdeaStatus[] = ["candidate", "sprout", "seed", "promoted", "discarded", "all"];

export function IdeasConsole() {
  const [status, setStatus] = useState<IdeaStatus>("candidate");
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const ideasQuery = useQuery({
    queryKey: ["operator-ideas", status],
    queryFn: async (): Promise<OperatorIdea[]> => {
      const query = status === "all" ? "" : `?status=${encodeURIComponent(status)}`;
      const data = await requestJson(`/api/operator/ideas${query}`);
      return (data?.ideas ?? data ?? []) as OperatorIdea[];
    },
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });

  const summaryQuery = useQuery({
    queryKey: ["operator-work-summary"],
    queryFn: async (): Promise<OperatorSummary> => {
      const data = await requestJson("/api/operator/summary");
      return (data ?? {}) as OperatorSummary;
    },
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });

  async function handleAction(action: string, run: () => Promise<void>) {
    setBusy(action);
    setFeedback(null);
    try {
      await run();
      await Promise.all([ideasQuery.refetch(), summaryQuery.refetch()]);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Request failed.");
    } finally {
      setBusy(null);
    }
  }

  if (ideasQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Operator Work" title="Ideas" description="The idea garden failed to load." attentionHref="/ideas" />
        <ErrorPanel description={ideasQuery.error instanceof Error ? ideasQuery.error.message : "Failed to load operator ideas."} />
      </div>
    );
  }

  const ideas = ideasQuery.data ?? [];
  const byStatus = summaryQuery.data?.ideas?.by_status ?? {};

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Operator Work"
        title="Ideas"
        description="Low-commitment capture before work becomes a todo, backlog item, or project."
        attentionHref="/ideas"
        actions={
          <Button variant="outline" onClick={() => void Promise.all([ideasQuery.refetch(), summaryQuery.refetch()])} disabled={ideasQuery.isFetching || summaryQuery.isFetching}>
            <RefreshCcw className={`mr-2 h-4 w-4 ${ideasQuery.isFetching || summaryQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Visible ideas" value={`${ideas.length}`} detail="Current filtered idea lane." icon={<Lightbulb className="h-5 w-5" />} />
          <StatCard label="Candidates" value={`${byStatus.candidate ?? 0}`} detail={`${byStatus.sprout ?? 0} sprouting and ${byStatus.seed ?? 0} seeded.`} icon={<Sparkles className="h-5 w-5" />} />
          <StatCard label="Promoted" value={`${byStatus.promoted ?? 0}`} detail={`${byStatus.discarded ?? 0} discarded so far.`} icon={<Rocket className="h-5 w-5" />} />
          <StatCard label="Next move" value={ideas[0]?.status ?? "clear"} detail="Highest-signal item in the current view." icon={<Target className="h-5 w-5" />} />
        </div>
      </PageHeader>

      {feedback ? <ErrorPanel title="Idea feedback" description={feedback} /> : null}

      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Capture idea</CardTitle>
          <CardDescription>Use the idea garden for low-commitment captures before they become real work.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Canonical foundry promotion flow" />
          <textarea
            rows={3}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Why it matters, what it unlocks, or what should happen next."
            className="surface-instrument w-full rounded-xl border px-3 py-2 text-sm outline-none transition focus:border-primary"
          />
          <Button
            onClick={() =>
              void handleAction("create", async () => {
                await postJson("/api/operator/ideas", { title: title.trim(), note: note.trim(), confidence: 0.6 });
                setTitle("");
                setNote("");
              })
            }
            disabled={busy === "create" || !title.trim()}
          >
            Add idea
          </Button>
        </CardContent>
      </Card>

      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Idea garden</CardTitle>
          <CardDescription>Promote the ideas that deserve explicit work.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {STATUS_FILTERS.map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setStatus(value)}
                className={`rounded-full border px-3 py-1 text-xs transition ${
                  status === value
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border/70 text-muted-foreground hover:bg-accent"
                }`}
              >
                {value}
              </button>
            ))}
          </div>

          {ideas.length > 0 ? (
            <div className="space-y-3">
              {ideas.map((idea) => (
                <div key={idea.id} className="surface-tile rounded-2xl border p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{idea.status}</Badge>
                    <Badge variant="secondary">{idea.source}</Badge>
                    <span className="text-xs text-muted-foreground">{`${Math.round(idea.confidence * 100)}% confidence`}</span>
                  </div>
                  <p className="mt-3 font-medium">{idea.title}</p>
                  {idea.note ? <p className="mt-2 text-sm text-muted-foreground">{idea.note}</p> : null}
                  {idea.tags.length > 0 ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {idea.tags.map((tag) => (
                        <Badge key={`${idea.id}-${tag}`} variant="secondary">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  ) : null}
                  <p className="mt-3 text-xs text-muted-foreground">{formatRelativeTime(new Date(idea.updated_at * 1000).toISOString())}</p>
                  {idea.status !== "promoted" && idea.status !== "discarded" ? (
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void handleAction(`todo:${idea.id}`, () => postJson(`/api/operator/ideas/${idea.id}/promote`, { target: "todo" }))}
                        disabled={busy === `todo:${idea.id}`}
                      >
                        Promote to todo
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => void handleAction(`backlog:${idea.id}`, () => postJson(`/api/operator/ideas/${idea.id}/promote`, { target: "backlog", owner_agent: "coding-agent" }))}
                        disabled={busy === `backlog:${idea.id}`}
                      >
                        Promote to backlog
                      </Button>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="Idea garden is empty" description="Capture the next low-commitment concept here." className="py-10" />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
