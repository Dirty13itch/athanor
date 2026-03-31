"use client";

import { useQuery } from "@tanstack/react-query";
import { Flame } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  asArray,
  asObject,
  fetchJson,
  getNumber,
  getString,
  type JsonObject,
} from "@/components/runtime-panel-utils";
import { isOperatorSessionLocked, useOperatorSessionStatus } from "@/lib/operator-session";

const REFRESH_MS = 30_000;

async function fetchSubscriptionSummary() {
  return fetchJson<JsonObject>("/api/subscriptions/summary");
}

export function SubscriptionBurn() {
  const session = useOperatorSessionStatus();
  const locked = isOperatorSessionLocked(session);
  const query = useQuery({
    queryKey: ["subscription-burn-card"],
    queryFn: fetchSubscriptionSummary,
    enabled: !locked,
    refetchInterval: REFRESH_MS,
  });

  if (locked) {
    return (
      <Card className="surface-instrument border">
        <CardHeader className="px-4 pb-2 pt-4 sm:px-6 sm:pb-3 sm:pt-6">
          <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
            <Flame className="h-4 w-4 text-primary sm:h-5 sm:w-5" />
            Subscription posture
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 sm:px-6">
          <EmptyState
            title="Unlock required"
            description="Provider posture and subscription evidence stay hidden until the operator session is unlocked."
            className="py-6"
          />
        </CardContent>
      </Card>
    );
  }

  const providerSummaries = asArray<JsonObject>(asObject(query.data)?.provider_summaries);
  const recentLeases = asArray<JsonObject>(asObject(query.data)?.recent_leases);
  const knownMonthlyCost = providerSummaries.reduce<number>((acc, summary) => {
    const raw = asObject(summary)?.catalog_monthly_cost_usd;
    return acc + (typeof raw === "number" ? raw : 0);
  }, 0);
  const providersMissingFlatRate = providerSummaries.filter((summary) => {
    const raw = asObject(summary)?.catalog_monthly_cost_usd;
    const pricingStatus = getString(summary.catalog_pricing_status, "");
    return raw == null && pricingStatus !== "not_applicable";
  }).length;

  return (
    <Card className="surface-instrument border">
      <CardHeader className="px-4 pb-2 pt-4 sm:px-6 sm:pb-3 sm:pt-6">
        <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
          <Flame className="h-4 w-4 text-primary sm:h-5 sm:w-5" />
          Subscription posture
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 px-4 sm:px-6">
        <div className="flex items-center justify-between text-xs sm:text-sm">
          <span className="text-muted-foreground">Known flat-rate cost</span>
          <span className="font-mono font-semibold">${knownMonthlyCost}/mo</span>
        </div>

        <div className="rounded-xl border border-border/60 bg-background/30 p-3 text-xs text-muted-foreground">
          Heuristic burn estimates have been removed. This card now shows catalog-backed cost and observed
          subscription activity only.
        </div>

        <div className="grid gap-2 sm:grid-cols-2">
          <Metric label="Providers" value={`${providerSummaries.length}`} />
          <Metric label="Recent leases" value={`${recentLeases.length}`} />
          <Metric
            label="Pricing gaps"
            value={providersMissingFlatRate > 0 ? `${providersMissingFlatRate}` : "0"}
          />
          <Metric
            label="Available"
            value={`${
              providerSummaries.filter((summary) => getString(summary.provider_state, "") === "available").length
            }`}
          />
        </div>

        <div className="space-y-1.5">
          {providerSummaries.slice(0, 4).map((summary) => {
            const label = getString(summary.label, getString(summary.provider, "provider"));
            const providerState = getString(summary.provider_state, "unknown");
            const pricingStatus = getString(summary.catalog_pricing_status, "unknown");
            return (
              <div
                key={getString(summary.provider, label)}
                className="flex items-center justify-between text-[11px] sm:text-xs"
              >
                <span className="text-muted-foreground">{label}</span>
                <div className="flex items-center gap-2 font-mono">
                  <span>{providerState}</span>
                  <span className="text-muted-foreground/80">{pricingStatus}</span>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border/50 bg-background/30 px-3 py-2">
      <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 font-mono text-sm font-semibold">{value}</p>
    </div>
  );
}
