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
  getBoolean,
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
  handoffPrompt,
  compact = false,
}: {
  title?: string;
  description?: string;
  requester?: string;
  taskClass?: string;
  handoffPrompt?: string;
  compact?: boolean;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const controlQuery = useQuery({
    queryKey: ["operator-panel", "subscriptions", requester, taskClass],
    queryFn: async () => ({
      providers: await fetchJson<JsonObject>("/api/subscriptions/providers"),
      policy: await fetchJson<JsonObject>("/api/subscriptions/policy"),
      summary: await fetchJson<JsonObject>("/api/subscriptions/summary"),
      quotas: await fetchJson<JsonObject>("/api/subscriptions/quotas"),
      leases: await fetchJson<JsonObject>("/api/subscriptions/leases"),
      execution: await fetchJson<JsonObject>("/api/subscriptions/execution"),
      handoffs: await fetchJson<JsonObject>("/api/subscriptions/handoffs"),
    }),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  async function requestLease() {
    setBusy("lease");
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
      setBusy(null);
    }
  }

  async function createHandoff() {
    setBusy("handoff");
    setFeedback(null);
    try {
      const response = await fetchJson<JsonObject>("/api/subscriptions/handoffs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          requester,
          task_class: taskClass,
          prompt:
            handoffPrompt ??
            `Prepare a structured execution bundle for ${requester} on ${taskClass}. Include plan, risks, validation, and rollback posture.`,
          sensitivity: "medium",
          interactive: false,
          expected_context: "medium",
          parallelism: "normal",
          issue_lease: true,
          metadata: { source: "dashboard_operator_panel", create_mode: "handoff_bundle" },
        }),
      });
      const handoff = asObject(response.handoff);
      setFeedback(
        handoff
          ? `Handoff ${getString(handoff.id)} created for ${getString(handoff.provider)}.`
          : "Handoff bundle created."
      );
      await controlQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Handoff creation failed.");
    } finally {
      setBusy(null);
    }
  }

  async function executeProvider() {
    setBusy("execute");
    setFeedback(null);
    try {
      const response = await fetchJson<JsonObject>("/api/subscriptions/execution", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          requester,
          task_class: taskClass,
          prompt:
            handoffPrompt ??
            `Review and plan the next safe implementation batch for ${requester} on ${taskClass}. Return a structured result with summary, risks, and next actions.`,
          sensitivity: "medium",
          interactive: false,
          expected_context: "medium",
          parallelism: "normal",
          issue_lease: true,
          metadata: { source: "dashboard_operator_panel", create_mode: "provider_execution" },
          timeout_seconds: 90,
        }),
      });
      const status = getString(response.status, "unknown");
      const handoff = asObject(response.handoff);
      const execution = asObject(response.execution);
      if (status === "completed" && execution) {
        setFeedback(
          `Provider execution completed on ${getString(response.provider)} in ${getNumber(execution.duration_ms, 0)}ms.`
        );
      } else if (status === "fallback_to_handoff" && handoff) {
        setFeedback(`Direct execution failed; handoff ${getString(handoff.id)} remains queued for ${getString(handoff.provider)}.`);
      } else if (handoff) {
        setFeedback(`${formatKey(status)} via ${getString(handoff.provider, getString(response.provider, "provider"))}.`);
      } else {
        setFeedback(getString(response.message, "Provider execution request completed."));
      }
      await controlQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Provider execution failed.");
    } finally {
      setBusy(null);
    }
  }

  async function recordHandoffOutcome(handoffId: string, outcome: "completed" | "failed") {
    setBusy(`handoff:${outcome}`);
    setFeedback(null);
    try {
      await fetchJson<JsonObject>(`/api/subscriptions/handoffs/${handoffId}/outcome`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          outcome,
          result_summary:
            outcome === "completed"
              ? "Completed from the operator-facing subscription control surface."
              : "",
          notes:
            outcome === "failed"
              ? "Marked failed from the operator-facing subscription control surface."
              : "",
        }),
      });
      setFeedback(`Handoff ${handoffId} marked ${outcome}.`);
      await controlQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Failed to record handoff outcome.");
    } finally {
      setBusy(null);
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

  const providersPayload = asObject(controlQuery.data?.providers);
  const policyPayload = asObject(controlQuery.data?.policy);
  const summaryPayload = asObject(controlQuery.data?.summary);
  const quotasPayload = asObject(controlQuery.data?.quotas);
  const leasesPayload = asObject(controlQuery.data?.leases);
  const executionPayload = asObject(controlQuery.data?.execution);
  const handoffsPayload = asObject(controlQuery.data?.handoffs);

  const providers = asArray<JsonObject>(providersPayload?.providers);
  const providerSummaries = asArray<JsonObject>(summaryPayload?.provider_summaries);
  const providerQuotaMap = asObject(quotasPayload?.providers) ?? {};
  const leases = asArray<JsonObject>(leasesPayload?.leases);
  const adapterMap = new Map(
    asArray<JsonObject>(executionPayload?.adapters).map((adapter) => [
      getString(adapter.provider),
      asObject(adapter) ?? {},
    ])
  );
  const providerSummaryMap = new Map(
    providerSummaries.map((summary) => [getString(summary.provider), asObject(summary) ?? {}])
  );
  const handoffs = asArray<JsonObject>(handoffsPayload?.handoffs);
  const handoffStatusCounts = asObject(executionPayload?.handoff_status_counts);
  const providerStateCounts = asObject(executionPayload?.provider_state_counts);
  const taskClasses = Object.keys(asObject(policyPayload?.task_classes) ?? {});
  const recentEvents = asArray<JsonObject>(quotasPayload?.recent_events);
  const directReadyCount = providerSummaries.filter((summary) =>
    getBoolean(summary.direct_execution_ready)
  ).length;
  const constrainedCount = providerSummaries.filter((summary) =>
    ["degraded", "handoff_only", "throttled"].includes(
      getString(summary.provider_state, getString(summary.availability, "unknown"))
    )
  ).length;

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
          <PanelMetric label="Direct ready" value={`${directReadyCount}`} />
          <PanelMetric label="Constrained" value={`${constrainedCount}`} />
        </div>

        <div className={compact ? "space-y-2" : "grid gap-3 lg:grid-cols-2"}>
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
              Provider posture
            </p>
            {providers.length > 0 ? (
              providers.slice(0, compact ? 3 : 4).map((provider) => {
                const providerId = getString(provider.id ?? provider.name);
                const quota = asObject(providerQuotaMap[providerId]);
                const summary = providerSummaryMap.get(providerId);
                const providerState = getString(
                  summary?.provider_state,
                  getString(summary?.availability, "tracked")
                );
                return (
                  <div
                    key={providerId}
                    className="rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-medium break-words">{getString(provider.name ?? providerId)}</p>
                        <p className="text-xs text-muted-foreground break-all">
                          {getString(provider.default_task_class ?? provider.description, "policy-backed")}
                        </p>
                      </div>
                      <Badge variant="outline">
                        {formatKey(providerState)}
                      </Badge>
                    </div>
                    {summary ? (
                      <p className="mt-2 text-xs text-muted-foreground">
                        reserve {formatKey(getString(summary.reserve_state, "standard"))}
                        {" | "}
                        next {formatKey(getString(summary.next_action, "monitor"))}
                      </p>
                    ) : null}
                    {summary ? (
                      <p className="mt-1 text-xs text-muted-foreground">
                        Remaining {getNumber(summary.remaining, 0)} / limit {getNumber(summary.limit, 0)}
                      </p>
                    ) : null}
                    {adapterMap.get(providerId) ? (
                      <p className="mt-1 text-xs text-muted-foreground">
                        mode {formatKey(getString(summary?.execution_mode, getString(adapterMap.get(providerId)?.execution_mode, "handoff_bundle")))}
                        {getBoolean(summary?.direct_execution_ready)
                          ? " | direct ready"
                          : getBoolean(summary?.governed_handoff_ready)
                            ? " | governed handoff"
                            : " | unavailable"}
                      </p>
                    ) : null}
                    {summary ? (
                      <p className="mt-1 text-xs text-muted-foreground">
                        exec {formatKey(getString(summary.recent_execution_state, "unknown"))}
                        {getOptionalString(summary.recent_execution_detail)
                          ? ` | ${getString(summary.recent_execution_detail)}`
                          : ""}
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
                  key={getString(lease.id ?? lease.lease_id)}
                  className="rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                        <p className="font-medium break-words">{getString(lease.provider)}</p>
                        <p className="text-xs text-muted-foreground break-all">
                          {formatKey(getString(lease.task_class, "unspecified"))}
                        </p>
                    </div>
                    <Badge variant="secondary">{getString(lease.requester, requester)}</Badge>
                  </div>
                  {getOptionalString(lease.expires_at) ? (
                    <p className="mt-2 text-xs text-muted-foreground" data-volatile="true">
                      expires {formatRelativeTime(getString(lease.expires_at))}
                    </p>
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
            {recentEvents.length > 0 ? (
              <p className="text-xs text-muted-foreground">
                {recentEvents.length} recent quota events observed from{" "}
                {getString(quotasPayload?.policy_source, "broker state")}.
              </p>
            ) : null}
            {providerStateCounts ? (
              <p className="text-xs text-muted-foreground">
                {Object.entries(providerStateCounts)
                  .map(([state, count]) => `${formatKey(state)} ${count}`)
                  .join(" | ")}
              </p>
            ) : null}
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
              Execution adapters
            </p>
            {adapterMap.size > 0 ? (
              Array.from(adapterMap.entries()).slice(0, compact ? 3 : 5).map(([providerId, adapter]) => (
                <div
                  key={providerId}
                  className="rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium break-words">{providerId}</p>
                      <p className="text-xs text-muted-foreground break-all">
                        {formatKey(getString(adapter.meta_lane, "frontier_cloud"))}
                      </p>
                    </div>
                    <Badge variant="outline">
                      {formatKey(
                        getString(
                          providerSummaryMap.get(providerId)?.provider_state,
                          getString(adapter.availability_state, "unknown")
                        )
                      )}
                    </Badge>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {getBoolean(providerSummaryMap.get(providerId)?.direct_execution_ready)
                      ? "Direct adapter is available on this runtime."
                      : getBoolean(providerSummaryMap.get(providerId)?.governed_handoff_ready)
                        ? "Bundle/handoff path is the current governed fallback."
                        : "This lane is currently unavailable."}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    next {formatKey(getString(providerSummaryMap.get(providerId)?.next_action, "monitor"))}
                    {" | "}
                    fallbacks {getNumber(providerSummaryMap.get(providerId)?.fallback_handoffs, 0)}
                    {" | "}
                    direct {getNumber(providerSummaryMap.get(providerId)?.direct_execution_count, 0)}
                  </p>
                </div>
              ))
            ) : (
              <EmptyState
                title="No adapter posture yet"
                description="Provider execution state will appear here once the broker reports adapter metadata."
                className="py-6"
              />
            )}
          </div>

          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
              Recent handoffs
            </p>
            {handoffs.length > 0 ? (
              handoffs.slice(0, compact ? 2 : 4).map((handoff) => (
                <div
                  key={getString(handoff.id)}
                  className="rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium break-words">{getString(handoff.provider)}</p>
                      <p className="text-xs text-muted-foreground break-all">
                        {formatKey(getString(handoff.task_class, "task"))}
                      </p>
                    </div>
                    <Badge variant="secondary">{formatKey(getString(handoff.prompt_mode, "raw"))}</Badge>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <Badge variant="outline">{formatKey(getString(handoff.status, "pending"))}</Badge>
                    <span>mode {formatKey(getString(handoff.execution_mode, "handoff_bundle"))}</span>
                    <span>
                      attempts {asArray<JsonObject>(handoff.execution_attempts).length}
                    </span>
                    {getOptionalString(handoff.fallback_from_execution_mode) ? (
                      <span>
                        fallback from {formatKey(getString(handoff.fallback_from_execution_mode))}
                      </span>
                    ) : null}
                    {getOptionalString(handoff.lease_id) ? (
                      <span>lease {getString(handoff.lease_id)}</span>
                    ) : null}
                    <span data-volatile="true">
                      {formatRelativeTime(
                        getString(
                          handoff.completed_at ?? handoff.updated_at ?? handoff.created_at,
                          new Date().toISOString()
                        )
                      )}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {getString(handoff.summary, "Structured handoff bundle")}
                  </p>
                  {getOptionalString(handoff.result_summary) ? (
                    <p className="mt-2 text-xs text-muted-foreground">
                      result {getString(handoff.result_summary)}
                    </p>
                  ) : null}
                  {getOptionalString(asObject(handoff.last_execution)?.summary) ? (
                    <p className="mt-2 text-xs text-muted-foreground">
                      execution {getString(asObject(handoff.last_execution)?.summary)}
                    </p>
                  ) : null}
                  {getOptionalString(handoff.fallback_reason) ? (
                    <p className="mt-2 text-xs text-muted-foreground">
                      fallback {getString(handoff.fallback_reason)}
                    </p>
                  ) : null}
                  {getString(handoff.status, "pending") === "pending" ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void recordHandoffOutcome(getString(handoff.id), "completed")}
                        disabled={busy !== null}
                      >
                        Mark complete
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void recordHandoffOutcome(getString(handoff.id), "failed")}
                        disabled={busy !== null}
                      >
                        Mark failed
                      </Button>
                    </div>
                  ) : null}
                </div>
              ))
            ) : (
              <EmptyState
                title="No handoffs generated yet"
                description="Structured handoff bundles will appear here when cloud-capable work is packaged for external execution."
                className="py-6"
              />
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={() => void controlQuery.refetch()}
            disabled={controlQuery.isFetching || busy !== null}
          >
            <RefreshCcw className={`mr-2 h-4 w-4 ${controlQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button onClick={() => void requestLease()} disabled={busy !== null}>
            <Rocket className="mr-2 h-4 w-4" />
            {busy === "lease" ? "Requesting..." : "Request lease"}
          </Button>
          <Button variant="outline" onClick={() => void executeProvider()} disabled={busy !== null}>
            {busy === "execute" ? "Executing..." : "Run provider task"}
          </Button>
          <Button variant="outline" onClick={() => void createHandoff()} disabled={busy !== null}>
            {busy === "handoff" ? "Packaging..." : "Create handoff"}
          </Button>
          {handoffStatusCounts ? (
            <Badge variant="outline">
              {Object.entries(handoffStatusCounts)
                .map(([status, count]) => `${formatKey(status)} ${count}`)
                .join(" | ")}
            </Badge>
          ) : null}
          <Badge variant="outline">{getString(policyPayload?.policy_source, "policy")}</Badge>
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
