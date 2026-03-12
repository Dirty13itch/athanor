"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { RefreshCcw, Rocket, ShieldCheck } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatRelativeTime } from "@/lib/format";
import {
  asArray,
  asObject,
  fetchJson,
  formatKey,
  getNumber,
  getOptionalString,
  getString,
  type JsonObject,
} from "@/components/runtime-panel-utils";

export function SubscriptionControlCard({
  title = "Subscription control",
  description = "Provider posture, policy coverage, quotas, and recent execution leases.",
  requester = "coding-agent",
  taskClass = "multi_file_implementation",
  compact = false,
}: {
  title?: string;
  description?: string;
  requester?: string;
  taskClass?: string;
  compact?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const controlQuery = useQuery({
    queryKey: ["operator-panel", "subscriptions", requester, taskClass],
    queryFn: async () => fetchJson<JsonObject>("/api/subscriptions/summary"),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  async function requestLease() {
    setBusy(true);
    setFeedback(null);
    try {
      const response = await fetchJson<JsonObject>("/api/subscriptions/leases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          requester,
          task_class: taskClass,
          sensitivity: "medium",
          interactive: false,
          expected_context: "medium",
          parallelism: "normal",
          metadata: { source: "dashboard_operator_panel" },
        }),
      });
      const lease = asObject(response.lease);
      setFeedback(
        lease
          ? `Lease issued on ${getString(lease.provider)} for ${formatKey(getString(lease.task_class))}.`
          : "Lease request completed."
      );
      await controlQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Lease request failed.");
    } finally {
      setBusy(false);
    }
  }

  if (controlQuery.isError && !controlQuery.data) {
    return (
      <ErrorPanel
        title={title}
        description={
          controlQuery.error instanceof Error
            ? controlQuery.error.message
            : "Failed to load subscription control data."
        }
      />
    );
  }

  const summaryPayload = asObject(controlQuery.data);
  const providers = asArray<JsonObject>(summaryPayload?.provider_summaries);
  const leases = asArray<JsonObject>(summaryPayload?.recent_leases);

  return (
    <Card className="border-border/70 bg-card/70">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <ShieldCheck className="h-5 w-5 text-primary" />
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {feedback ? (
          <div className="rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm">
            {feedback}
          </div>
        ) : null}

        <div className="grid gap-3 sm:grid-cols-3">
          <PanelMetric label="Providers" value={`${providers.length}`} />
          <PanelMetric
            label="Constrained lanes"
            value={`${
              providers.filter((provider) => getString(provider.availability, "available") === "constrained").length
            }`}
          />
          <PanelMetric label="Recent leases" value={`${leases.length}`} />
        </div>

        <div className={compact ? "space-y-2" : "grid gap-3 lg:grid-cols-2"}>
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
              Provider posture
            </p>
            {providers.length > 0 ? (
              providers.slice(0, compact ? 3 : 4).map((provider) => {
                const outcomes = asArray<JsonObject>(provider.recent_outcomes);
                return (
                  <div
                    key={getString(provider.provider)}
                    className="rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-medium break-words">{formatKey(getString(provider.provider))}</p>
                        <p className="text-xs text-muted-foreground break-all">
                          {formatKey(getString(provider.lane, "policy-backed"))}
                        </p>
                      </div>
                      <Badge variant="outline">
                        {getString(provider.availability, "tracked")}
                      </Badge>
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                      Remaining {getNumber(provider.remaining, 0)} / limit {getNumber(provider.limit, 0)}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                      <span>reserve {formatKey(getString(provider.reserve_state, "standard"))}</span>
                      <span>throttles {getNumber(provider.throttle_events, 0)}</span>
                    </div>
                    {outcomes.length > 0 ? (
                      <p className="mt-2 text-xs text-muted-foreground">
                        outcomes {outcomes.map((entry) => `${getString(entry.outcome)}:${getNumber(entry.count, 0)}`).join(" · ")}
                      </p>
                    ) : null}
                  </div>
                );
              })
            ) : (
              <EmptyState
                title="No providers reported"
                description="The subscription broker did not return provider metadata."
                className="py-6"
              />
            )}
          </div>

          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
              Latest routing
            </p>
            {leases.length > 0 ? (
              leases.slice(0, compact ? 2 : 3).map((lease) => (
                <div
                  key={getString(lease.id)}
                  className="rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium break-words">{getString(lease.provider)}</p>
                      <p className="text-xs text-muted-foreground break-all">
                        {getString(lease.summary, formatKey(getString(lease.run_type, "unspecified")))}
                      </p>
                    </div>
                    <Badge variant="secondary">{getString(lease.agent, requester)}</Badge>
                  </div>
                  {getOptionalString(lease.created_at) ? (
                    <p className="mt-2 text-xs text-muted-foreground" data-volatile="true">
                      {getString(lease.status, "issued")} {formatRelativeTime(getString(lease.created_at))}
                    </p>
                  ) : null}
                  {getOptionalString(lease.failure_reason) ? (
                    <p className="mt-1 text-xs text-destructive">{getString(lease.failure_reason)}</p>
                  ) : null}
                </div>
              ))
            ) : (
              <EmptyState
                title="No leases issued yet"
                description="Request one from the dashboard to verify broker visibility."
                className="py-6"
              />
            )}
            <p className="text-xs text-muted-foreground">
              Policy source {getString(summaryPayload?.policy_source, "broker state")}.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => void controlQuery.refetch()} disabled={controlQuery.isFetching}>
            <RefreshCcw className={`mr-2 h-4 w-4 ${controlQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button onClick={() => void requestLease()} disabled={busy}>
            <Rocket className="mr-2 h-4 w-4" />
            {busy ? "Requesting..." : "Request lease"}
          </Button>
          <Badge variant="outline">{getString(summaryPayload?.policy_source, "policy")}</Badge>
        </div>
      </CardContent>
    </Card>
  );
}

function PanelMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/30 px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}
