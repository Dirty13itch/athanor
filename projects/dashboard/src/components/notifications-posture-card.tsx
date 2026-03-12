"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  asArray,
  asObject,
  fetchJson,
  getNumber,
  getString,
  type JsonObject,
} from "@/components/runtime-panel-utils";

export function NotificationsPostureCard() {
  const postureQuery = useQuery({
    queryKey: ["operator-panel", "notifications-posture"],
    queryFn: async () => ({
      alerts: await fetchJson<JsonObject>("/api/alerts"),
      budgets: await fetchJson<JsonObject>("/api/notification-budget"),
    }),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  if (postureQuery.isError && !postureQuery.data) {
    return (
      <ErrorPanel
        title="Notification posture"
        description={
          postureQuery.error instanceof Error
            ? postureQuery.error.message
            : "Failed to load notification posture."
        }
      />
    );
  }

  const alerts = asArray<JsonObject>(asObject(postureQuery.data?.alerts)?.alerts);
  const budgets = Object.entries(asObject(asObject(postureQuery.data?.budgets)?.budgets) ?? {});

  return (
    <Card className="border-border/70 bg-card/70">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <AlertTriangle className="h-5 w-5 text-primary" />
          Alerts and notification budgets
        </CardTitle>
        <CardDescription>
          Runtime alert feed plus per-agent notification budget posture.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <Metric label="Alerts" value={`${alerts.length}`} />
          <Metric label="Tracked agents" value={`${budgets.length}`} />
          <Metric
            label="Over budget"
            value={`${
              budgets.filter(([, value]) => getNumber(asObject(value)?.remaining, 0) <= 0).length
            }`}
          />
        </div>

        <div className="grid gap-3 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Alerts</p>
            {alerts.length > 0 ? (
              alerts.slice(0, 5).map((alert, index) => (
                <div
                  key={`${getString(alert.name, "alert")}-${index}`}
                  className="rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium">{getString(alert.name, "runtime alert")}</p>
                    <Badge variant={getString(alert.severity) === "critical" ? "destructive" : "outline"}>
                      {getString(alert.severity, "info")}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {getString(alert.description, "No description returned.")}
                  </p>
                </div>
              ))
            ) : (
              <EmptyState
                title="No active alerts"
                description="The runtime did not report any active alerts."
                className="py-8"
              />
            )}
          </div>

          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Budget posture</p>
            {budgets.length > 0 ? (
              budgets.slice(0, 5).map(([agentName, value]) => {
                const budget = asObject(value);
                return (
                  <div
                    key={agentName}
                    className="rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium">{agentName}</p>
                      <Badge variant="outline">
                        {getNumber(budget?.remaining, 0)} remaining
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      used {getNumber(budget?.used, 0)} / {getNumber(budget?.limit, 0)}
                    </p>
                  </div>
                );
              })
            ) : (
              <EmptyState
                title="No budget data"
                description="Notification budgets are not currently available."
                className="py-8"
              />
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/40 px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}
