"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Layers3, RefreshCcw } from "lucide-react";
import { ErrorPanel } from "@/components/error-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  asObject,
  fetchJson,
  formatKey,
  getNumber,
  type JsonObject,
} from "@/components/runtime-panel-utils";

export function ConsolidationCard() {
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [lastRun, setLastRun] = useState<JsonObject | null>(null);

  const consolidationQuery = useQuery({
    queryKey: ["operator-panel", "consolidation"],
    queryFn: async () => fetchJson<JsonObject>("/api/consolidation/stats"),
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  async function runConsolidation() {
    setBusy(true);
    setFeedback(null);
    try {
      const response = await fetchJson<JsonObject>("/api/consolidation", { method: "POST" });
      setLastRun(response);
      setFeedback("Consolidation run completed.");
      await consolidationQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Consolidation failed.");
    } finally {
      setBusy(false);
    }
  }

  if (consolidationQuery.isError && !consolidationQuery.data) {
    return (
      <ErrorPanel
        title="Consolidation"
        description={
          consolidationQuery.error instanceof Error
            ? consolidationQuery.error.message
            : "Failed to load consolidation data."
        }
      />
    );
  }

  const collections = Object.entries(consolidationQuery.data ?? {});

  return (
    <Card className="border-border/70 bg-card/70">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Layers3 className="h-5 w-5 text-primary" />
          Consolidation posture
        </CardTitle>
        <CardDescription>
          Retention-backed counts across collections tracked by the consolidation pipeline.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {feedback ? (
          <div className="rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm">
            {feedback}
          </div>
        ) : null}

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {collections.slice(0, 4).map(([name, value]) => {
            const meta = asObject(value);
            return (
              <Metric
                key={name}
                label={formatKey(name)}
                value={`${getNumber(meta?.count, 0)}`}
                detail={`${getNumber(meta?.retention_days, 0)} day retention`}
              />
            );
          })}
        </div>

        <div className="space-y-2">
          {collections.map(([name, value]) => {
            const meta = asObject(value);
            return (
              <div
                key={name}
                className="flex items-center justify-between rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm"
              >
                <div>
                  <p className="font-medium">{formatKey(name)}</p>
                  <p className="text-xs text-muted-foreground">
                    {getNumber(meta?.retention_days, 0)} day retention window
                  </p>
                </div>
                <span className="font-medium">{getNumber(meta?.count, 0)} points</span>
              </div>
            );
          })}
        </div>

        {lastRun ? (
          <div className="rounded-xl border border-border/60 bg-background/30 p-3 text-sm">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Last run</p>
            <pre className="mt-2 whitespace-pre-wrap text-xs text-muted-foreground">
              {JSON.stringify(lastRun, null, 2)}
            </pre>
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => void consolidationQuery.refetch()} disabled={consolidationQuery.isFetching}>
            <RefreshCcw className={`mr-2 h-4 w-4 ${consolidationQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button onClick={() => void runConsolidation()} disabled={busy}>
            Run now
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail?: string;
}) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/40 px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
      {detail ? <p className="text-xs text-muted-foreground">{detail}</p> : null}
    </div>
  );
}
