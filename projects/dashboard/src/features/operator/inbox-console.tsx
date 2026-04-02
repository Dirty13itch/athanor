"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BellRing, CheckCircle2, ClipboardList, Clock3, RefreshCcw, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { formatRelativeTime, formatTimestamp } from "@/lib/format";
import { requestJson, postJson, postWithoutBody } from "@/features/workforce/helpers";

type InboxStatus = "all" | "new" | "acknowledged" | "snoozed" | "resolved" | "converted";

interface OperatorInboxItem {
  id: string;
  kind: string;
  severity: number;
  status: Exclude<InboxStatus, "all">;
  source: string;
  title: string;
  description: string;
  requires_decision: boolean;
  decision_type: string;
  snooze_until: number;
  created_at: number;
  updated_at: number;
  resolved_at: number;
  metadata?: Record<string, unknown>;
}

interface OperatorSummary {
  inbox?: {
    total?: number;
    by_status?: Record<string, number>;
  };
}

const STATUS_FILTERS: InboxStatus[] = ["new", "acknowledged", "snoozed", "resolved", "converted", "all"];

function severityTone(severity: number) {
  if (severity >= 3) return "destructive";
  if (severity === 2) return "secondary";
  return "outline";
}

export function InboxConsole() {
  const [status, setStatus] = useState<InboxStatus>("new");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const inboxQuery = useQuery({
    queryKey: ["operator-inbox", status],
    queryFn: async (): Promise<OperatorInboxItem[]> => {
      const query = status === "all" ? "" : `?status=${encodeURIComponent(status)}`;
      const data = await requestJson(`/api/operator/inbox${query}`);
      return (data?.items ?? data ?? []) as OperatorInboxItem[];
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
      await Promise.all([inboxQuery.refetch(), summaryQuery.refetch()]);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Request failed.");
    } finally {
      setBusy(null);
    }
  }

  if (inboxQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Operator Work" title="Inbox" description="The operator inbox failed to load." attentionHref="/inbox" />
        <ErrorPanel description={inboxQuery.error instanceof Error ? inboxQuery.error.message : "Failed to load operator inbox."} />
      </div>
    );
  }

  const items = inboxQuery.data ?? [];
  const summary = summaryQuery.data?.inbox;
  const byStatus = summary?.by_status ?? {};
  const urgentCount = items.filter((item) => item.severity >= 3 && item.status !== "resolved").length;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Operator Work"
        title="Inbox"
        description="Decision items, alerts, and conversion candidates for the human loop."
        attentionHref="/inbox"
        actions={
          <Button variant="outline" onClick={() => void Promise.all([inboxQuery.refetch(), summaryQuery.refetch()])} disabled={inboxQuery.isFetching || summaryQuery.isFetching}>
            <RefreshCcw className={`mr-2 h-4 w-4 ${inboxQuery.isFetching || summaryQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Visible items" value={`${items.length}`} detail="Current filtered inbox lane." icon={<BellRing className="h-5 w-5" />} />
          <StatCard label="Urgent" value={`${urgentCount}`} detail="Severity 3 items in the current view." tone={urgentCount > 0 ? "warning" : "success"} icon={<Sparkles className="h-5 w-5" />} />
          <StatCard label="New" value={`${byStatus.new ?? 0}`} detail={`${byStatus.acknowledged ?? 0} acknowledged and ${byStatus.snoozed ?? 0} snoozed.`} />
          <StatCard label="Converted" value={`${byStatus.converted ?? 0}`} detail={`${byStatus.resolved ?? 0} resolved so far.`} icon={<ClipboardList className="h-5 w-5" />} />
        </div>
      </PageHeader>

      {feedback ? <ErrorPanel title="Inbox feedback" description={feedback} /> : null}

      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Inbox lane</CardTitle>
          <CardDescription>Use this page for acknowledgements, snoozes, resolutions, and todo conversion.</CardDescription>
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

          {items.length > 0 ? (
            <div className="space-y-3">
              {items.map((item) => (
                <div key={item.id} className="surface-tile rounded-2xl border p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={severityTone(item.severity)}>{`severity ${item.severity}`}</Badge>
                    <Badge variant="secondary">{item.kind}</Badge>
                    <Badge variant="outline">{item.status}</Badge>
                    <span className="text-xs text-muted-foreground">{item.source}</span>
                  </div>
                  <p className="mt-3 font-medium">{item.title}</p>
                  {item.description ? <p className="mt-2 text-sm text-muted-foreground">{item.description}</p> : null}
                  <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
                    <span>{formatRelativeTime(new Date(item.created_at * 1000).toISOString())}</span>
                    {item.snooze_until > 0 ? <span>{`Snoozed until ${formatTimestamp(new Date(item.snooze_until * 1000).toISOString())}`}</span> : null}
                    {item.requires_decision ? <span>{`Decision: ${item.decision_type || "required"}`}</span> : null}
                  </div>
                  {item.status !== "resolved" && item.status !== "converted" ? (
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void handleAction(`ack:${item.id}`, () => postWithoutBody(`/api/operator/inbox/${item.id}/ack`))}
                        disabled={busy === `ack:${item.id}`}
                      >
                        <CheckCircle2 className="mr-2 h-4 w-4" />
                        Acknowledge
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void handleAction(`snooze:${item.id}`, () => postJson(`/api/operator/inbox/${item.id}/snooze`, {}))}
                        disabled={busy === `snooze:${item.id}`}
                      >
                        <Clock3 className="mr-2 h-4 w-4" />
                        Snooze
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void handleAction(`convert:${item.id}`, () => postJson(`/api/operator/inbox/${item.id}/convert`, {}))}
                        disabled={busy === `convert:${item.id}`}
                      >
                        <ClipboardList className="mr-2 h-4 w-4" />
                        Convert to todo
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => void handleAction(`resolve:${item.id}`, () => postJson(`/api/operator/inbox/${item.id}/resolve`, {}))}
                        disabled={busy === `resolve:${item.id}`}
                      >
                        Resolve
                      </Button>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="Inbox is clear" description="No operator inbox items match the current filter." className="py-10" />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
