"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Compass, RefreshCcw, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { getWorkforce } from "@/lib/api";
import { type WorkforceSnapshot } from "@/lib/contracts";
import { compactText, formatRelativeTime, formatTimestamp } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import { getAgentName, getProjectName, postJson, postWithoutBody } from "@/features/workforce/helpers";

const conventionTone: Record<string, string> = {
  behavior: "bg-blue-500/15 text-blue-100 border-blue-500/30",
  preference: "bg-purple-500/15 text-purple-100 border-purple-500/30",
  quality: "bg-sky-500/15 text-sky-100 border-sky-500/30",
  schedule: "bg-emerald-500/15 text-emerald-100 border-emerald-500/30",
};

export function WorkspaceConsole({ initialSnapshot }: { initialSnapshot: WorkforceSnapshot }) {
  const [feedback, setFeedback] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const workforceQuery = useQuery({
    queryKey: queryKeys.workforce,
    queryFn: getWorkforce,
    initialData: initialSnapshot,
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });

  async function handleAction(action: string, run: () => Promise<void>) {
    setBusy(action);
    setFeedback(null);
    try {
      await run();
      await workforceQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Request failed.");
    } finally {
      setBusy(null);
    }
  }

  if (workforceQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Workforce" title="Workspace" description="The workspace snapshot failed to load." />
        <ErrorPanel
          description={
            workforceQuery.error instanceof Error
              ? workforceQuery.error.message
              : "Failed to load workforce data."
          }
        />
      </div>
    );
  }

  const snapshot = workforceQuery.data ?? initialSnapshot;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Workforce"
        title="Workspace"
        description="Shared broadcast state, coalition signals, conventions, and subscription posture for the agent workforce."
        actions={
          <Button variant="outline" onClick={() => void workforceQuery.refetch()} disabled={workforceQuery.isFetching}>
            <RefreshCcw className={`mr-2 h-4 w-4 ${workforceQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Broadcast items" value={`${snapshot.workspace.broadcastItems}`} detail={`${snapshot.workspace.totalItems} total candidates in the current competition set.`} icon={<Compass className="h-5 w-5" />} />
          <StatCard label="Utilization" value={`${Math.round((snapshot.workspace.utilization ?? 0) * 100)}%`} detail={`Capacity ${snapshot.workspace.capacity} items.`} />
          <StatCard label="Registered agents" value={`${snapshot.agents.length}`} detail={`${snapshot.subscriptions.length} active workspace subscriptions.`} icon={<Users className="h-5 w-5" />} />
          <StatCard label="Proposed conventions" value={`${snapshot.conventions.proposed.length}`} detail={`${snapshot.conventions.confirmed.length} conventions are active.`} />
        </div>
      </PageHeader>

      {feedback ? <ErrorPanel title="Workspace feedback" description={feedback} /> : null}

      <div className="grid gap-4 xl:grid-cols-[1.3fr_1fr]">
        <Card className="border-border/70 bg-card/70">
          <CardHeader>
            <CardTitle className="text-lg">Current broadcast</CardTitle>
            <CardDescription>Highest-salience items in the shared workspace competition window.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {snapshot.workspace.broadcast.length > 0 ? (
              snapshot.workspace.broadcast.map((item, index) => (
                <div key={item.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                  <div className="flex items-start gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full border border-border/70 bg-background/40 text-xs font-semibold">
                      {index + 1}
                    </div>
                    <div className="flex-1 space-y-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="secondary">{getAgentName(snapshot, item.sourceAgent)}</Badge>
                        <Badge variant="outline">{item.priority}</Badge>
                        {item.projectId ? <Badge variant="outline">{getProjectName(snapshot, item.projectId)}</Badge> : null}
                        <span className="text-xs text-muted-foreground">salience {item.salience.toFixed(1)}</span>
                      </div>
                      <p className="text-sm">{item.content}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatRelativeTime(item.createdAt)} | ttl {item.ttlSeconds}s
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {snapshot.agents
                          .filter((agent) => agent.id !== item.sourceAgent && !item.coalition.includes(agent.id))
                          .slice(0, 4)
                          .map((agent) => (
                            <Button
                              key={agent.id}
                              size="sm"
                              variant="outline"
                              disabled={busy === `endorse:${item.id}:${agent.id}`}
                              onClick={() =>
                                void handleAction(`endorse:${item.id}:${agent.id}`, () =>
                                  postJson(`/api/workforce/workspace/${item.id}/endorse`, { agentName: agent.id })
                                )
                              }
                            >
                              Endorse as {agent.name}
                            </Button>
                          ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <EmptyState title="Workspace is quiet" description="No broadcast items are active in the current workspace window." className="py-10" />
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="border-border/70 bg-card/70">
            <CardHeader>
              <CardTitle className="text-lg">Agent registry</CardTitle>
              <CardDescription>Capability and queue posture by registered workforce agent.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {snapshot.agents.map((agent) => (
                <div key={agent.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{agent.name}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{agent.type} | {agent.tools.length} tools</p>
                    </div>
                    <Badge variant={agent.status === "ready" ? "default" : "outline"}>{agent.status}</Badge>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-1">
                    {agent.tools.slice(0, 6).map((tool) => (
                      <Badge key={tool} variant="outline">
                        {tool}
                      </Badge>
                    ))}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="border-border/70 bg-card/70">
            <CardHeader>
              <CardTitle className="text-lg">Subscriptions</CardTitle>
              <CardDescription>Which agents are listening for which classes of shared signals.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {snapshot.subscriptions.length > 0 ? (
                snapshot.subscriptions.map((subscription) => (
                  <div key={subscription.agentId} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium">{getAgentName(snapshot, subscription.agentId)}</p>
                      <Badge variant="outline">{Math.round(subscription.threshold * 100)}%</Badge>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-1">
                      {subscription.keywords.slice(0, 6).map((keyword) => (
                        <Badge key={keyword} variant="outline">
                          {keyword}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <EmptyState title="No subscriptions available" description="Workspace subscriptions have not been configured yet." className="py-8" />
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1.2fr]">
        <Card className="border-border/70 bg-card/70">
          <CardHeader>
            <CardTitle className="text-lg">Proposed conventions</CardTitle>
            <CardDescription>Patterns awaiting operator confirmation before they become policy.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {snapshot.conventions.proposed.length > 0 ? (
              snapshot.conventions.proposed.map((convention) => (
                <div key={convention.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge className={conventionTone[convention.type] ?? conventionTone.behavior}>{convention.type}</Badge>
                    <Badge variant="secondary">{getAgentName(snapshot, convention.agentId)}</Badge>
                    <span className="text-xs text-muted-foreground">{convention.occurrences} sightings</span>
                  </div>
                  <p className="mt-3 text-sm">{convention.description}</p>
                  <p className="mt-2 text-xs text-muted-foreground">{compactText(convention.rule, 160)}</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      onClick={() =>
                        void handleAction(`confirm:${convention.id}`, () =>
                          postWithoutBody(`/api/workforce/conventions/${convention.id}/confirm`)
                        )
                      }
                    >
                      Confirm
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        void handleAction(`reject:${convention.id}`, () =>
                          postWithoutBody(`/api/workforce/conventions/${convention.id}/reject`)
                        )
                      }
                    >
                      Reject
                    </Button>
                  </div>
                </div>
              ))
            ) : (
              <EmptyState title="No proposed conventions" description="No new patterns are waiting for operator review." className="py-10" />
            )}
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-card/70">
          <CardHeader>
            <CardTitle className="text-lg">Active conventions</CardTitle>
            <CardDescription>Confirmed coordination rules shaping how the workforce behaves.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {snapshot.conventions.confirmed.length > 0 ? (
              snapshot.conventions.confirmed.map((convention) => (
                <div key={convention.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge className={conventionTone[convention.type] ?? conventionTone.behavior}>{convention.type}</Badge>
                    <Badge variant="secondary">{getAgentName(snapshot, convention.agentId)}</Badge>
                    <span className="text-xs text-muted-foreground">{convention.source}</span>
                  </div>
                  <p className="mt-3 text-sm">{convention.description}</p>
                  <p className="mt-2 text-xs text-muted-foreground">{convention.rule}</p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Confirmed {formatTimestamp(convention.confirmedAt)}
                  </p>
                </div>
              ))
            ) : (
              <EmptyState title="No confirmed conventions" description="Confirmed conventions will appear here once the workforce establishes them." className="py-10" />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
