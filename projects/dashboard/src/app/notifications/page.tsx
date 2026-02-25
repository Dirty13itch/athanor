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

interface Notification {
  id: string;
  agent: string;
  action: string;
  category: string;
  confidence: number;
  description: string;
  tier: "act" | "notify" | "ask";
  created_at: number;
  resolved: boolean;
  resolution: string;
}

const TIER_STYLES: Record<string, { badge: string; label: string }> = {
  ask: { badge: "bg-red-500/20 text-red-400", label: "Needs Approval" },
  notify: {
    badge: "bg-yellow-500/20 text-yellow-400",
    label: "Auto-acted",
  },
  act: { badge: "bg-green-500/20 text-green-400", label: "Autonomous" },
};

const CATEGORY_LABELS: Record<string, string> = {
  read: "Status Query",
  routine: "Routine Adjustment",
  content: "Content Addition",
  delete: "Deletion",
  config: "Configuration",
  security: "Security",
};

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showResolved, setShowResolved] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchNotifications = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (showResolved) params.set("include_resolved", "true");
      const res = await fetch(
        `${config.agentServer.url}/v1/notifications?${params}`
      );
      if (!res.ok) throw new Error(`Failed (${res.status})`);
      const data = await res.json();
      setNotifications(data.notifications || []);
      setUnread(data.unread || 0);
      setError(null);
      setLastUpdated(new Date());
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Failed to fetch notifications"
      );
    } finally {
      setLoading(false);
    }
  }, [showResolved]);

  useEffect(() => {
    fetchNotifications();
    const id = setInterval(fetchNotifications, 5000);
    return () => clearInterval(id);
  }, [fetchNotifications]);

  const resolveAction = async (actionId: string, approved: boolean) => {
    try {
      const res = await fetch(
        `${config.agentServer.url}/v1/notifications/${actionId}/resolve`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ approved }),
        }
      );
      if (!res.ok) throw new Error(`Failed (${res.status})`);
      fetchNotifications();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to resolve");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Notifications</h1>
          <p className="text-muted-foreground">
            Agent actions requiring attention or acknowledgment
          </p>
        </div>
        <div className="flex items-center gap-3">
          {unread > 0 && (
            <Badge className="bg-red-500/20 text-red-400">
              {unread} pending
            </Badge>
          )}
          {lastUpdated && (
            <p className="text-xs text-muted-foreground">
              Updated {lastUpdated.toLocaleTimeString()}
            </p>
          )}
        </div>
      </div>

      {/* Filter toggle */}
      <div className="flex gap-3">
        <button
          onClick={() => setShowResolved(!showResolved)}
          className={`rounded-md border px-3 py-1.5 text-xs transition-colors ${
            showResolved
              ? "border-primary bg-primary/10 text-primary"
              : "border-border text-muted-foreground hover:bg-accent"
          }`}
        >
          {showResolved ? "Showing all" : "Show resolved"}
        </button>
      </div>

      {loading && (
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-muted-foreground">Loading...</p>
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

      {!loading && notifications.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-sm text-muted-foreground">
              No notifications. Agents are operating within confidence
              thresholds.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Notification cards */}
      <div className="space-y-3">
        {notifications.map((notif) => {
          const tierStyle =
            TIER_STYLES[notif.tier] || TIER_STYLES.act;
          const isPending = notif.tier === "ask" && !notif.resolved;

          return (
            <Card
              key={notif.id}
              className={isPending ? "border-red-500/30" : ""}
            >
              <CardContent className="py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge className={tierStyle.badge}>
                        {tierStyle.label}
                      </Badge>
                      <Badge variant="outline">{notif.agent}</Badge>
                      <Badge variant="outline">
                        {CATEGORY_LABELS[notif.category] || notif.category}
                      </Badge>
                      <span className="text-xs text-muted-foreground font-mono">
                        {(notif.confidence * 100).toFixed(0)}% confidence
                      </span>
                    </div>
                    <p className="text-sm font-medium">{notif.action}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {notif.description}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatTimestamp(notif.created_at)}
                    </p>
                    {notif.resolved && (
                      <p className="text-xs mt-1">
                        <Badge
                          variant="outline"
                          className={
                            notif.resolution === "approved"
                              ? "text-green-400"
                              : notif.resolution === "rejected"
                                ? "text-red-400"
                                : "text-muted-foreground"
                          }
                        >
                          {notif.resolution}
                        </Badge>
                      </p>
                    )}
                  </div>

                  {isPending && (
                    <div className="flex gap-2 flex-shrink-0">
                      <button
                        onClick={() => resolveAction(notif.id, true)}
                        className="rounded-md bg-green-500/20 px-3 py-1.5 text-xs text-green-400 hover:bg-green-500/30 transition-colors"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => resolveAction(notif.id, false)}
                        className="rounded-md bg-red-500/20 px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/30 transition-colors"
                      >
                        Reject
                      </button>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Escalation thresholds info */}
      <EscalationConfig />
    </div>
  );
}

function EscalationConfig() {
  const [config_, setConfig] = useState<Record<
    string,
    { default: number; agents: Record<string, number> }
  > | null>(null);

  useEffect(() => {
    fetch(`${config.agentServer.url}/v1/escalation/config`)
      .then((r) => r.json())
      .then((d) => setConfig(d.thresholds))
      .catch(() => {});
  }, []);

  if (!config_) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Escalation Thresholds</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
          {Object.entries(config_).map(([category, data]) => (
            <div key={category}>
              <p className="text-xs font-medium text-foreground mb-1">
                {CATEGORY_LABELS[category] || category}
              </p>
              <p className="text-xs text-muted-foreground">
                Default: {(data.default * 100).toFixed(0)}%
              </p>
              {Object.entries(data.agents).map(([agent, threshold]) => (
                <p key={agent} className="text-xs text-muted-foreground">
                  {agent}: {(threshold * 100).toFixed(0)}%
                </p>
              ))}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function formatTimestamp(unixTs: number): string {
  try {
    const date = new Date(unixTs * 1000);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);

    if (diffMin < 1) return "just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffMin < 1440) return `${Math.floor(diffMin / 60)}h ago`;
    return date.toLocaleDateString();
  } catch {
    return "unknown";
  }
}
