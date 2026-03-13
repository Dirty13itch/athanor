"use client";

import { useQuery } from "@tanstack/react-query";
import { BellRing, RefreshCcw, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { NotificationsPostureCard } from "@/components/notifications-posture-card";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { getWorkforce } from "@/lib/api";
import { type WorkforceNotification, type WorkforceSnapshot } from "@/lib/contracts";
import { formatRelativeTime } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import { useUrlState } from "@/lib/url-state";
import { getAgentName, postJson } from "@/features/workforce/helpers";

const tierMeta: Record<WorkforceNotification["tier"], { label: string; tone: "danger" | "info" | "success" }> = {
  ask: { label: "Needs approval", tone: "danger" },
  notify: { label: "Auto-acted", tone: "info" },
  act: { label: "Autonomous", tone: "success" },
};

function notificationSurfaceClass(notification: WorkforceNotification) {
  if (notification.resolved) {
    return "surface-tile opacity-85";
  }
  if (notification.tier === "ask") {
    return "surface-hero";
  }
  if (notification.tier === "notify") {
    return "surface-panel";
  }
  return "surface-instrument";
}

export function NotificationsConsole({ initialSnapshot }: { initialSnapshot: WorkforceSnapshot }) {
  const { getSearchValue, setSearchValue } = useUrlState();
  const showResolved = getSearchValue("resolved", "0") === "1";
  const workforceQuery = useQuery({
    queryKey: queryKeys.workforce,
    queryFn: getWorkforce,
    initialData: initialSnapshot,
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });

  async function resolveAction(notificationId: string, approved: boolean) {
    await postJson(`/api/workforce/notifications/${notificationId}/resolve`, { approved });
    await workforceQuery.refetch();
  }

  if (workforceQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Workforce"
          title="Notifications"
          description="The workforce notification snapshot failed to load."
          attentionHref="/notifications"
        />
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
  const notifications = showResolved
    ? snapshot.notifications
    : snapshot.notifications.filter((notification) => !notification.resolved);
  const pendingApprovals = snapshot.notifications.filter(
    (notification) => notification.tier === "ask" && !notification.resolved
  );

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Workforce"
        title="Notifications"
        description="Escalations, auto-actions, and operator review items emitted by the workforce."
        attentionHref="/notifications"
        actions={
          <>
            <Button variant="outline" onClick={() => void workforceQuery.refetch()} disabled={workforceQuery.isFetching}>
              <RefreshCcw className={`mr-2 h-4 w-4 ${workforceQuery.isFetching ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button variant="outline" onClick={() => setSearchValue("resolved", showResolved ? null : "1")}>
              {showResolved ? "Hide resolved" : "Show resolved"}
            </Button>
          </>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Unread" value={`${snapshot.summary.unreadNotifications}`} detail="Items not yet acknowledged in the operator loop." icon={<BellRing className="h-5 w-5" />} />
          <StatCard label="Needs approval" value={`${pendingApprovals.length}`} detail="High-impact decisions outside autonomous bounds." tone={pendingApprovals.length > 0 ? "warning" : "success"} icon={<ShieldAlert className="h-5 w-5" />} />
          <StatCard label="Auto-acted" value={`${snapshot.notifications.filter((item) => item.tier === "notify").length}`} detail="Actions executed and surfaced for review." />
          <StatCard label="Resolved" value={`${snapshot.notifications.filter((item) => item.resolved).length}`} detail="Closed notifications in the retained history window." />
        </div>
      </PageHeader>

      <NotificationsPostureCard />

      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Notification lane</CardTitle>
          <CardDescription>{notifications.length} items in the current view.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {notifications.length > 0 ? (
            notifications.map((notification) => {
              const meta = tierMeta[notification.tier];
              const pending = notification.tier === "ask" && !notification.resolved;
              return (
                <div key={notification.id} className={`${notificationSurfaceClass(notification)} rounded-2xl border p-4`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline" className="status-badge" data-tone={meta.tone}>
                      {meta.label}
                    </Badge>
                    <Badge variant="secondary">{getAgentName(snapshot, notification.agentId)}</Badge>
                    <Badge variant="outline">{notification.category}</Badge>
                    <span className="text-xs text-muted-foreground">
                      {Math.round(notification.confidence * 100)}% confidence
                    </span>
                  </div>
                  <p className="mt-3 font-medium">{notification.action}</p>
                  <p className="mt-2 text-sm text-muted-foreground">{notification.description}</p>
                  <p className="mt-2 text-xs text-muted-foreground">{formatRelativeTime(notification.createdAt)}</p>
                  {notification.resolved ? (
                    <p className="mt-3 text-xs text-muted-foreground">
                      Resolved as {notification.resolution ?? "closed"}
                    </p>
                  ) : null}
                  {pending ? (
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button size="sm" onClick={() => void resolveAction(notification.id, true)}>
                        Approve
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => void resolveAction(notification.id, false)}>
                        Reject
                      </Button>
                    </div>
                  ) : null}
                </div>
              );
            })
          ) : (
            <EmptyState title="No notifications in this view" description="The workforce is currently operating inside the selected filter scope." className="py-10" />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
