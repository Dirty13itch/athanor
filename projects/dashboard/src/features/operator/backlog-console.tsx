"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Archive, PlayCircle, RefreshCcw, ShieldAlert, Workflow } from "lucide-react";
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

type BacklogStatus = "all" | "captured" | "triaged" | "ready" | "scheduled" | "running" | "waiting_approval" | "blocked" | "completed" | "failed" | "archived";

interface BacklogItem {
  id: string;
  title: string;
  prompt: string;
  owner_agent: string;
  work_class: string;
  family?: string;
  project_id?: string;
  routing_class?: string;
  source_type?: string;
  verification_contract?: string;
  materialization_reason?: string;
  result_id?: string;
  review_id?: string;
  priority: number;
  status: Exclude<BacklogStatus, "all">;
  approval_mode: string;
  blocking_reason: string;
  updated_at: number;
}

interface OperatorSummary {
  backlog?: {
    total?: number;
    by_status?: Record<string, number>;
  };
}

interface BacklogFeedStatus {
  available?: boolean;
  degraded?: boolean;
  detail?: string;
  source?: string;
}

interface BacklogFeedPayload extends BacklogFeedStatus {
  backlog?: BacklogItem[];
  count?: number;
}

const STATUS_FILTERS: BacklogStatus[] = ["ready", "running", "waiting_approval", "blocked", "captured", "archived", "all"];

function normalizeBacklogStatus(value: string | null | undefined): BacklogStatus {
  if (!value) {
    return "ready";
  }

  return STATUS_FILTERS.includes(value as BacklogStatus) ? (value as BacklogStatus) : "ready";
}

export function BacklogConsole({ initialStatus = "ready" }: { initialStatus?: string }) {
  const [status, setStatus] = useState<BacklogStatus>(normalizeBacklogStatus(initialStatus));
  const [title, setTitle] = useState("");
  const [prompt, setPrompt] = useState("");
  const [ownerAgent, setOwnerAgent] = useState("coding-agent");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const backlogQuery = useQuery({
    queryKey: ["operator-backlog", status],
    queryFn: async (): Promise<BacklogFeedPayload> => {
      const query = status === "all" ? "" : `?status=${encodeURIComponent(status)}`;
      const data = await requestJson(`/api/operator/backlog${query}`);
      return (data ?? {}) as BacklogFeedPayload;
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
      await Promise.all([backlogQuery.refetch(), summaryQuery.refetch()]);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Request failed.");
    } finally {
      setBusy(null);
    }
  }

  if (backlogQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Operator Work" title="Backlog" description="The operator backlog failed to load." attentionHref="/backlog" />
        <ErrorPanel description={backlogQuery.error instanceof Error ? backlogQuery.error.message : "Failed to load operator backlog."} />
      </div>
    );
  }

  const backlog = backlogQuery.data?.backlog ?? [];
  const byStatus = summaryQuery.data?.backlog?.by_status ?? {};
  const backlogFeedStatus = backlogQuery.data;
  const backlogFeedUnavailable = backlogFeedStatus?.available === false || backlogFeedStatus?.degraded;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Operator Work"
        title="Backlog"
        description="Agent-eligible work capture and dispatch separate from active execution runs."
        attentionHref="/backlog"
        actions={
          <Button variant="outline" onClick={() => void Promise.all([backlogQuery.refetch(), summaryQuery.refetch()])} disabled={backlogQuery.isFetching || summaryQuery.isFetching}>
            <RefreshCcw className={`mr-2 h-4 w-4 ${backlogQuery.isFetching || summaryQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Visible backlog" value={`${backlog.length}`} detail="Current filtered backlog view." icon={<Workflow className="h-5 w-5" />} />
          <StatCard label="Ready" value={`${byStatus.ready ?? 0}`} detail={`${byStatus.running ?? 0} already running.`} icon={<PlayCircle className="h-5 w-5" />} />
          <StatCard label="Waiting approval" value={`${byStatus.waiting_approval ?? 0}`} detail={`${byStatus.blocked ?? 0} blocked work items.`} icon={<ShieldAlert className="h-5 w-5" />} />
          <StatCard label="Archived" value={`${byStatus.archived ?? 0}`} detail="Operator-retired backlog items." icon={<Archive className="h-5 w-5" />} />
        </div>
      </PageHeader>

      {backlogFeedUnavailable ? (
        <div className="surface-panel rounded-[24px] border border-[color:var(--signal-warning)]/40 px-5 py-4 sm:px-6">
          <p className="page-eyebrow text-[color:var(--signal-warning)]">Backlog feed degraded</p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            The operator backlog is still usable, but the dashboard is falling back to empty state data because the upstream backlog feed is temporarily unavailable.
          </p>
        </div>
      ) : null}

      {feedback ? <ErrorPanel title="Backlog feedback" description={feedback} /> : null}

      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Capture backlog item</CardTitle>
          <CardDescription>Use the backlog for agent-eligible work that should be dispatched later.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Build the foundry promotion packet" />
          <textarea
            rows={4}
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Write the exact agent-facing prompt or work slice."
            className="surface-instrument w-full rounded-xl border px-3 py-2 text-sm outline-none transition focus:border-primary"
          />
          <select
            value={ownerAgent}
            onChange={(event) => setOwnerAgent(event.target.value)}
            className="surface-instrument rounded-xl border px-3 py-2 text-sm outline-none transition focus:border-primary"
          >
            <option value="coding-agent">coding-agent</option>
            <option value="research-agent">research-agent</option>
            <option value="knowledge-agent">knowledge-agent</option>
            <option value="general-assistant">general-assistant</option>
          </select>
          <Button
            onClick={() =>
              void handleAction("create", async () => {
                await postJson("/api/operator/backlog", {
                  title: title.trim(),
                  prompt: prompt.trim(),
                  owner_agent: ownerAgent,
                  work_class: "project_build",
                  priority: 3,
                });
                setTitle("");
                setPrompt("");
              })
            }
            disabled={busy === "create" || !title.trim() || !prompt.trim()}
          >
            Add backlog item
          </Button>
        </CardContent>
      </Card>

      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Backlog lane</CardTitle>
          <CardDescription>Dispatch, block, or archive work without confusing it with execution state.</CardDescription>
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

          {backlog.length > 0 ? (
            <div className="space-y-3">
              {backlog.map((item) => (
                <div key={item.id} className="surface-tile rounded-2xl border p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{item.status}</Badge>
                    <Badge variant="secondary">{item.owner_agent}</Badge>
                    {item.family ? <Badge variant="secondary">{item.family}</Badge> : null}
                    <span className="text-xs text-muted-foreground">{`${item.work_class} · P${item.priority}`}</span>
                  </div>
                  <p className="mt-3 font-medium">{item.title}</p>
                  <p className="mt-2 text-sm text-muted-foreground">{item.prompt}</p>
                  <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
                    {item.project_id ? <span>{`project ${item.project_id}`}</span> : null}
                    {item.routing_class ? <span>{item.routing_class}</span> : null}
                    {item.source_type ? <span>{item.source_type}</span> : null}
                    {item.verification_contract ? <span>{item.verification_contract}</span> : null}
                  </div>
                  {item.materialization_reason ? (
                    <p className="mt-2 text-xs text-muted-foreground">{item.materialization_reason}</p>
                  ) : null}
                  <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
                    {item.review_id ? <span>{`review ${item.review_id}`}</span> : null}
                    {item.result_id ? <span>{`result ${item.result_id}`}</span> : null}
                  </div>
                  {item.blocking_reason ? <p className="mt-3 text-xs text-amber-600">{item.blocking_reason}</p> : null}
                  <p className="mt-3 text-xs text-muted-foreground">{formatRelativeTime(new Date(item.updated_at * 1000).toISOString())}</p>
                  {item.status !== "archived" && item.status !== "completed" ? (
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        onClick={() => void handleAction(`dispatch:${item.id}`, () => postJson(`/api/operator/backlog/${item.id}/dispatch`, {}))}
                        disabled={busy === `dispatch:${item.id}`}
                      >
                        Dispatch
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void handleAction(`block:${item.id}`, () => postJson(`/api/operator/backlog/${item.id}/transition`, { status: "blocked", blocking_reason: "Operator blocked this item for follow-up." }))}
                        disabled={busy === `block:${item.id}`}
                      >
                        Block
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void handleAction(`archive:${item.id}`, () => postJson(`/api/operator/backlog/${item.id}/transition`, { status: "archived" }))}
                        disabled={busy === `archive:${item.id}`}
                      >
                        Archive
                      </Button>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title={backlogFeedUnavailable ? "Backlog feed unavailable" : "No backlog items here"}
              description={
                backlogFeedUnavailable
                  ? "The dashboard cannot currently read the live operator backlog, so this view is showing the fail-soft fallback."
                  : "Capture agent work or change the current filter."
              }
              className="py-10"
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
