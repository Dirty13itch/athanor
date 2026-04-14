"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowRightLeft,
  DollarSign,
  RefreshCcw,
  Rocket,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { LiveBadge } from "@/components/live-badge";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { StatusDot } from "@/components/status-dot";
import { formatRelativeTime } from "@/lib/format";
import { liveQueryOptions } from "@/lib/live-updates";
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

/* ---------- query key ---------- */
const QUERY_KEY = ["subscriptions-console"] as const;
const REFRESH_MS = 30_000;

function getCatalogMonthlyCost(summary: JsonObject, providerStatus: JsonObject | undefined): number | null {
  const summaryValue = asObject(summary)?.catalog_monthly_cost_usd;
  if (typeof summaryValue === "number") {
    return summaryValue;
  }
  const statusValue = providerStatus?.monthly_cost;
  return typeof statusValue === "number" ? statusValue : null;
}

function getCatalogPricingStatus(summary: JsonObject, providerStatus: JsonObject | undefined): string | null {
  const summaryValue = getOptionalString(asObject(summary)?.catalog_pricing_status);
  if (summaryValue) {
    return summaryValue;
  }
  return getOptionalString(providerStatus?.pricing_status) ?? null;
}

function formatMonthlyCost(monthlyCost: number | null, pricingStatus: string | null): string {
  if (typeof monthlyCost === "number") {
    return monthlyCost > 0 ? `$${monthlyCost}` : "$0";
  }
  if (pricingStatus?.includes("unverified")) {
    return "Unverified";
  }
  if (pricingStatus === "metered") {
    return "Metered";
  }
  return "--";
}

/* ---------- data fetcher ---------- */
async function fetchSubscriptionData() {
  const [summary, providers, quotas, leases, execution, handoffs, policy] = await Promise.all([
    fetchJson<JsonObject>("/api/subscriptions/summary"),
    fetchJson<JsonObject>("/api/routing/providers"),
    fetchJson<JsonObject>("/api/subscriptions/quotas"),
    fetchJson<JsonObject>("/api/subscriptions/leases"),
    fetchJson<JsonObject>("/api/subscriptions/execution"),
    fetchJson<JsonObject>("/api/subscriptions/handoffs"),
    fetchJson<JsonObject>("/api/subscriptions/policy"),
  ]);
  return { summary, providers, quotas, leases, execution, handoffs, policy };
}

/* ---------- component ---------- */

export function SubscriptionsConsole() {
  const query = useQuery({
    queryKey: QUERY_KEY,
    queryFn: fetchSubscriptionData,
    ...liveQueryOptions(REFRESH_MS),
  });

  if (query.isError && !query.data) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Subscriptions"
          title="Subscription Burn"
          description="Subscription data failed to load."
        />
        <ErrorPanel
          description={
            query.error instanceof Error
              ? query.error.message
              : "Failed to load subscription data."
          }
        />
      </div>
    );
  }

  if (!query.data) return null;

  const data = query.data;
  const providerSummaries = asArray<JsonObject>(asObject(data.summary)?.provider_summaries);
  const providerStatusEntries = asArray<JsonObject>(asObject(data.providers)?.providers);
  const providerStatusById = new Map(
    providerStatusEntries.map((entry) => [getString(entry.id), entry] as const)
  );
  const providerQuotaMap = asObject(asObject(data.quotas)?.providers) ?? {};
  const quotaEvents = asArray<JsonObject>(asObject(data.quotas)?.recent_events);
  const leases = asArray<JsonObject>(asObject(data.leases)?.leases);
  const handoffs = asArray<JsonObject>(asObject(data.handoffs)?.handoffs);
  const verifiedMonthlySpend = providerSummaries.reduce((sum, summary) => {
    const providerStatus = providerStatusById.get(getString(summary.provider));
    const monthlyCost = getCatalogMonthlyCost(summary, providerStatus);
    return typeof monthlyCost === "number" && monthlyCost > 0 ? sum + monthlyCost : sum;
  }, 0);
  const unverifiedMonthlyLanes = providerSummaries.filter((summary) => {
    const providerStatus = providerStatusById.get(getString(summary.provider));
    return (
      getCatalogMonthlyCost(summary, providerStatus) == null &&
      getCatalogPricingStatus(summary, providerStatus)?.includes("unverified")
    );
  }).length;

  const directReadyCount = providerSummaries.filter((s) =>
    getBoolean(s.direct_execution_ready)
  ).length;
  const handoffOnlyCount = providerSummaries.filter(
    (s) => getString(s.provider_state, "") === "handoff_only"
  ).length;
  const totalLeases = Object.values(providerQuotaMap).reduce<number>(
    (acc, v) => acc + getNumber(asObject(v)?.leases_issued, 0),
    0
  );

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Subscriptions"
        title="Subscription Burn"
        description="Canonical home for provider burn posture, spend tracking, provider capacity, active leases, and execution history. Routing and model surfaces deep-link here for economics."
        actions={
          <>
            <LiveBadge
              updatedAt={new Date().toISOString()}
              intervalMs={REFRESH_MS}
            />
            <Button
              variant="outline"
              onClick={() => void query.refetch()}
              disabled={query.isFetching}
            >
              <RefreshCcw
                className={`mr-2 h-4 w-4 ${query.isFetching ? "animate-spin" : ""}`}
              />
              Refresh
            </Button>
          </>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Monthly spend"
            value={verifiedMonthlySpend > 0 ? `$${verifiedMonthlySpend}${unverifiedMonthlyLanes > 0 ? "+" : ""}` : "$0"}
            detail={
              unverifiedMonthlyLanes > 0
                ? `${unverifiedMonthlyLanes} provider lane${unverifiedMonthlyLanes === 1 ? "" : "s"} still cost-unverified.`
                : "Catalog-backed fixed subscription total."
            }
            icon={<DollarSign className="h-5 w-5" />}
          />
          <StatCard
            label="Providers"
            value={`${providerSummaries.length}`}
            detail={`${directReadyCount} direct ready, ${handoffOnlyCount} handoff only.`}
            icon={<Zap className="h-5 w-5" />}
          />
          <StatCard
            label="Total leases"
            value={`${totalLeases}`}
            detail="Across all providers lifetime."
            icon={<ArrowRightLeft className="h-5 w-5" />}
          />
          <StatCard
            label="Handoffs"
            value={`${handoffs.length}`}
            detail="Structured execution bundles."
            icon={<Rocket className="h-5 w-5" />}
          />
        </div>
      </PageHeader>

      {/* ---------- provider cards grid ---------- */}
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Provider subscriptions</CardTitle>
          <CardDescription>
            Per-provider cost, availability, reserve posture, and quota state.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {providerSummaries.length > 0 ? (
            providerSummaries.map((summary) => {
              const providerId = getString(summary.provider);
              const providerStatus = providerStatusById.get(providerId);
              const monthly = getCatalogMonthlyCost(summary, providerStatus);
              const pricingStatus = getCatalogPricingStatus(summary, providerStatus);
              const quotaData = asObject(providerQuotaMap[providerId]);
              const leasesIssued = getNumber(quotaData?.leases_issued, 0);
              const providerState = getString(
                summary.provider_state,
                getString(summary.availability, "unknown")
              );
              const isAvailable = providerState === "available";
              const isHandoff = providerState === "handoff_only";

              return (
                <div
                  key={providerId}
                  className={`rounded-2xl border p-4 ${
                    isAvailable
                      ? "surface-instrument border"
                      : "surface-panel border"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">
                        {getString(summary.label, getOptionalString(providerStatus?.name) ?? formatKey(providerId))}
                      </p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {getString(
                          summary.subscription_product,
                          getOptionalString(providerStatus?.subscription) ?? formatKey(providerId)
                        )}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusDot
                        tone={
                          isAvailable
                            ? "healthy"
                            : isHandoff
                              ? "warning"
                              : "danger"
                        }
                      />
                      <Badge variant="outline" className="status-badge">
                        {formatKey(providerState)}
                      </Badge>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-2 sm:grid-cols-2">
                    <Metric
                      label="Monthly"
                      value={formatMonthlyCost(monthly, pricingStatus)}
                      icon={<DollarSign className="h-3.5 w-3.5" />}
                    />
                    <Metric
                      label="Leases issued"
                      value={`${leasesIssued}`}
                      icon={<ArrowRightLeft className="h-3.5 w-3.5" />}
                    />
                    <Metric
                      label="Reserve"
                      value={formatKey(getString(summary.reserve_state, "standard"))}
                      icon={<ShieldCheck className="h-3.5 w-3.5" />}
                    />
                    <Metric
                      label="Execution mode"
                      value={formatKey(getString(summary.execution_mode, "unknown"))}
                      icon={<Zap className="h-3.5 w-3.5" />}
                    />
                  </div>

                  <div className="mt-3 space-y-1">
                    <p className="text-xs text-muted-foreground">
                      Lane: {formatKey(getString(summary.lane, "unassigned"))}
                    </p>
                    {pricingStatus ? (
                      <p className="text-xs text-muted-foreground">
                        Pricing posture: {formatKey(pricingStatus)}
                      </p>
                    ) : null}
                    <p className="text-xs text-muted-foreground">
                      Slots: {getNumber(summary.occupied_slots, 0)}/{getNumber(summary.slot_limit, 0)} occupied
                      {" | "}
                      Privacy: {getString(summary.privacy, "unknown")}
                    </p>
                    {getBoolean(summary.direct_execution_ready) ? (
                      <p className="text-xs text-[color:var(--signal-success)]">
                        Direct execution ready
                      </p>
                    ) : getBoolean(summary.governed_handoff_ready) ? (
                      <p className="text-xs text-[color:var(--signal-warning)]">
                        Governed handoff only
                      </p>
                    ) : (
                      <p className="text-xs text-muted-foreground">
                        Unavailable for execution
                      </p>
                    )}
                    {getOptionalString(summary.last_issued_at) && (
                      <p className="text-xs text-muted-foreground" data-volatile="true">
                        Last lease {formatRelativeTime(getString(summary.last_issued_at))}
                      </p>
                    )}
                  </div>
                </div>
              );
            })
          ) : (
            <EmptyState
              title="No providers tracked"
              description="The subscription broker has not returned provider metadata."
            />
          )}
        </CardContent>
      </Card>

      {/* ---------- active leases + handoffs ---------- */}
      <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <Card className="surface-instrument">
          <CardHeader>
            <CardTitle className="text-lg">Active leases</CardTitle>
            <CardDescription>
              Currently issued provider leases and their assigned agents.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {leases.length > 0 ? (
              leases.slice(0, 12).map((lease) => {
                const leaseId = getString(lease.id);
                const createdAt = getNumber(lease.created_at, 0);
                const expiresAt = getNumber(lease.expires_at, 0);
                const createdIso = createdAt > 0 ? new Date(createdAt * 1000).toISOString() : null;
                const expiresIso = expiresAt > 0 ? new Date(expiresAt * 1000).toISOString() : null;

                return (
                  <div
                    key={leaseId}
                    className="rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-medium">
                          {getString(lease.provider)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatKey(getString(lease.task_class, "unspecified"))}
                        </p>
                      </div>
                      <Badge variant="secondary">
                        {getString(lease.requester, "agent")}
                      </Badge>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
                      <span>surface: {getString(lease.surface, "--")}</span>
                      <span>privacy: {getString(lease.privacy, "--")}</span>
                      {createdIso && (
                        <span data-volatile="true">
                          issued {formatRelativeTime(createdIso)}
                        </span>
                      )}
                      {expiresIso && (
                        <span data-volatile="true">
                          expires {formatRelativeTime(expiresIso)}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            ) : (
              <EmptyState
                title="No active leases"
                description="No provider leases are currently issued."
                className="py-6"
              />
            )}
            {leases.length > 12 && (
              <p className="text-xs text-muted-foreground">
                Showing 12 of {leases.length} active leases.
              </p>
            )}
          </CardContent>
        </Card>

        <Card className="surface-panel">
          <CardHeader>
            <CardTitle className="text-lg">Recent handoffs</CardTitle>
            <CardDescription>
              Structured execution bundles packaged for external providers.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {handoffs.length > 0 ? (
              handoffs.slice(0, 8).map((handoff) => {
                const handoffId = getString(handoff.id);
                const status = getString(handoff.status, "pending");
                const isCompleted = status === "completed";
                const isFailed = status === "failed";
                return (
                  <div
                    key={handoffId}
                    className="rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-medium">
                          {getString(handoff.provider)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatKey(getString(handoff.task_class, "task"))}
                        </p>
                      </div>
                      <Badge
                        variant={isCompleted ? "default" : isFailed ? "destructive" : "outline"}
                      >
                        {formatKey(status)}
                      </Badge>
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {getString(handoff.summary, "Structured handoff bundle")}
                    </p>
                    <div className="mt-1 flex flex-wrap gap-3 text-xs text-muted-foreground">
                      <span>mode: {formatKey(getString(handoff.execution_mode, "handoff"))}</span>
                      {getOptionalString(handoff.requester) && (
                        <span>agent: {getString(handoff.requester)}</span>
                      )}
                      {getOptionalString(handoff.completed_at) ? (
                        <span data-volatile="true">
                          {formatRelativeTime(getString(handoff.completed_at))}
                        </span>
                      ) : getOptionalString(handoff.created_at) ? (
                        <span data-volatile="true">
                          created {formatRelativeTime(getString(handoff.created_at))}
                        </span>
                      ) : null}
                    </div>
                    {getOptionalString(handoff.result_summary) && (
                      <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                        result: {getString(handoff.result_summary)}
                      </p>
                    )}
                  </div>
                );
              })
            ) : (
              <EmptyState
                title="No handoffs yet"
                description="Structured bundles will appear when cloud work is packaged."
                className="py-6"
              />
            )}
          </CardContent>
        </Card>
      </div>

      {/* ---------- execution history ---------- */}
      <Card className="surface-instrument">
        <CardHeader>
          <CardTitle className="text-lg">Execution event log</CardTitle>
          <CardDescription>
            Recent lease and outcome events from the subscription broker.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {quotaEvents.length > 0 ? (
            <div className="space-y-2">
              {quotaEvents.slice(0, 20).map((event, index) => {
                const eventType = getString(event.event, "unknown");
                const isOutcome = eventType.includes("outcome");
                const timestamp = getNumber(event.timestamp, 0);
                const timeIso =
                  timestamp > 0 ? new Date(timestamp * 1000).toISOString() : null;

                return (
                  <div
                    key={`${getString(event.lease_id)}-${index}`}
                    className="flex items-center justify-between gap-4 rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm"
                  >
                    <div className="flex items-center gap-3">
                      <StatusDot
                        tone={
                          isOutcome
                            ? getString(event.outcome) === "completed"
                              ? "healthy"
                              : "danger"
                            : "warning"
                        }
                      />
                      <div>
                        <p className="font-medium">
                          {formatKey(eventType)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {getString(event.provider)} | {getString(event.requester, getString(event.task_class, "--"))}
                          {isOutcome && ` | ${getString(event.outcome, "--")}`}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      {timeIso && (
                        <p className="text-xs text-muted-foreground" data-volatile="true">
                          {formatRelativeTime(timeIso)}
                        </p>
                      )}
                      <p className="font-mono text-xs text-muted-foreground">
                        {getString(event.lease_id, "").slice(0, 18)}
                      </p>
                    </div>
                  </div>
                );
              })}
              {quotaEvents.length > 20 && (
                <p className="text-xs text-muted-foreground">
                  Showing 20 of {quotaEvents.length} events.
                </p>
              )}
            </div>
          ) : (
            <EmptyState
              title="No execution events"
              description="Lease and outcome events will appear as the subscription broker processes work."
            />
          )}
        </CardContent>
      </Card>

      {/* ---------- routing policy summary ---------- */}
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Routing policy</CardTitle>
          <CardDescription>
            Task class routing from the active subscription policy.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {Object.keys(asObject(asObject(data.policy)?.task_classes) ?? {}).length > 0 ? (
            <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
              {Object.entries(
                asObject(asObject(data.policy)?.task_classes) ?? {}
              ).map(([taskClass, routing]) => {
                const routingObj = asObject(routing);
                const primary = asArray<string>(routingObj?.primary);
                const fallback = asArray<string>(routingObj?.fallback);
                return (
                  <div
                    key={taskClass}
                    className="rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm"
                  >
                    <p className="font-medium">{formatKey(taskClass)}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Primary: {primary.map(formatKey).join(", ") || "none"}
                    </p>
                    {fallback.length > 0 && (
                      <p className="text-xs text-muted-foreground">
                        Fallback: {fallback.map(formatKey).join(", ")}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <EmptyState
              title="No routing policy loaded"
              description="The subscription policy file did not return task class routing."
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/* ---------- local metric sub-component ---------- */

function Metric({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="surface-metric rounded-xl border p-3">
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      <p className="mt-2 text-sm font-semibold">{value}</p>
    </div>
  );
}
