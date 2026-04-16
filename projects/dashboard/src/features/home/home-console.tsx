"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Home, RefreshCcw, Thermometer } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { StatCard } from "@/components/stat-card";
import { getHomeOverview } from "@/lib/api";
import { config } from "@/lib/config";
import { type HomeSnapshot } from "@/lib/contracts";
import { formatRelativeTime } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import { useUrlState } from "@/lib/url-state";

function homeStepTone(status: string) {
  switch (status) {
    case "complete":
      return "success";
    case "blocked":
      return "danger";
    case "pending":
      return "warning";
    default:
      return "info";
  }
}

function homeStepSurface(status: string) {
  switch (status) {
    case "complete":
      return "surface-instrument border";
    case "blocked":
      return "surface-hero border";
    case "pending":
      return "surface-tile border";
    default:
      return "surface-tile border";
  }
}

export function HomeConsole({ initialSnapshot }: { initialSnapshot: HomeSnapshot }) {
  const { getSearchValue, setSearchValue } = useUrlState();
  const panel = getSearchValue("panel", "");

  const homeQuery = useQuery({
    queryKey: queryKeys.homeOverview,
    queryFn: getHomeOverview,
    initialData: initialSnapshot,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  if (homeQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Domain Console" title="Home" description="The home snapshot failed to load." />
        <ErrorPanel
          description={
            homeQuery.error instanceof Error ? homeQuery.error.message : "Failed to load home snapshot."
          }
        />
      </div>
    );
  }

  const snapshot = homeQuery.data ?? initialSnapshot;
  const activePanel = snapshot.panels.find((entry) => entry.id === panel) ?? null;
  const completeSteps = snapshot.setupSteps.filter((step) => step.status === "complete").length;
  const entities = snapshot.entities ?? 0;
  const lights = snapshot.lights ?? { total: 0, on: 0 };
  const automations = snapshot.automations ?? { total: 0, on: 0 };
  const climate = snapshot.climate ?? [];
  const sensors = snapshot.sensors ?? [];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Domain Console"
        title="Home"
        description="Home Assistant integration — live entity status, climate, lighting, and automation state."
        actions={
          <>
            <Button variant="outline" onClick={() => void homeQuery.refetch()} disabled={homeQuery.isFetching}>
              <RefreshCcw className={`mr-2 h-4 w-4 ${homeQuery.isFetching ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button asChild variant="outline">
              <a href={config.homeAssistant.url} target="_blank" rel="noopener noreferrer">
                <ArrowUpRight className="mr-2 h-4 w-4" />
                Open Home Assistant
              </a>
            </Button>
          </>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Runtime" value={snapshot.online ? "Online" : "Offline"} detail={snapshot.configured ? "Token active" : "No token"} tone={snapshot.online ? "success" : "warning"} />
          <StatCard label="Entities" value={entities > 0 ? `${entities}` : "--"} detail={entities > 0 ? `${lights.total} lights, ${automations.total} automations` : "No entity data"} tone={entities > 0 ? "success" : "default"} />
          <StatCard label="Lights" value={lights.total > 0 ? `${lights.on}/${lights.total}` : "--"} detail={lights.total > 0 ? `${lights.on} currently on` : "No lights found"} tone={lights.on > 0 ? "success" : "default"} />
          <StatCard label="Automations" value={automations.total > 0 ? `${automations.on}/${automations.total}` : "--"} detail={automations.total > 0 ? `${automations.on} active` : "No automations found"} tone={automations.on > 0 ? "success" : "default"} />
        </div>
      </PageHeader>

      <div className="grid gap-4 xl:grid-cols-2">
        {/* Climate */}
        <Card className="surface-panel border">
          <CardHeader>
            <CardTitle className="text-lg">Climate</CardTitle>
            <CardDescription>HVAC zones and temperature readings.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {climate.length > 0 ? (
              climate.map((zone) => (
                <div key={zone.id} className="surface-instrument flex items-center justify-between rounded-2xl border p-4">
                  <div className="flex items-center gap-3">
                    <div className="surface-metric rounded-xl border p-2" style={{ color: "var(--domain-home)" }}>
                      <Thermometer className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="font-medium">{zone.name}</p>
                      <p className="text-sm text-muted-foreground">{zone.hvac_action ?? zone.state}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    {zone.current_temperature != null && (
                      <p className="text-lg font-semibold tabular-nums">{zone.current_temperature}&deg;F</p>
                    )}
                    {zone.temperature != null && (
                      <p className="text-xs text-muted-foreground">Target: {zone.temperature}&deg;F</p>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <EmptyState title="No climate data" description="Climate entities will appear when HA is fully connected." />
            )}
          </CardContent>
        </Card>

        {/* Setup + Panels */}
        <div className="space-y-4">
          <Card className="surface-panel border">
            <CardHeader>
              <CardTitle className="text-lg">Integration Status</CardTitle>
              <CardDescription>{completeSteps}/{snapshot.setupSteps.length} steps complete.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {snapshot.setupSteps.map((step) => (
                <div key={step.id} className={`rounded-2xl p-4 ${homeStepSurface(step.status)}`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline" className="status-badge" data-tone={homeStepTone(step.status)}>
                      {step.status}
                    </Badge>
                    <p className="font-medium">{step.label}</p>
                  </div>
                  {step.note ? <p className="mt-2 text-sm text-muted-foreground">{step.note}</p> : null}
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="surface-panel border">
            <CardHeader>
              <CardTitle className="text-lg">Focused panels</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {snapshot.panels.length > 0 ? (
                snapshot.panels.map((entry) => (
                  <button
                    key={entry.id}
                    type="button"
                    onClick={() => setSearchValue("panel", entry.id)}
                    className="surface-instrument w-full rounded-2xl border p-4 text-left transition hover:bg-accent/40"
                  >
                    <div className="flex items-center gap-3">
                      <div className="surface-metric rounded-xl border p-2" style={{ color: "var(--domain-home)" }}>
                        <Home className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="font-medium">{entry.label}</p>
                        <p className="text-sm text-muted-foreground">{entry.description}</p>
                      </div>
                    </div>
                  </button>
                ))
              ) : (
                <EmptyState title="No home panels yet" description="Panels appear here once the home lane is configured." />
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Key sensors */}
      {sensors.length > 0 && (
        <Card className="surface-panel border">
          <CardHeader>
            <CardTitle className="text-lg">Key Sensors</CardTitle>
            <CardDescription>Temperature, humidity, power, and energy sensors.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {sensors.map((sensor) => (
                <div key={sensor.id} className="surface-instrument rounded-xl border px-3 py-2">
                  <p className="text-xs text-muted-foreground truncate">{sensor.name}</p>
                  <p className="text-sm font-semibold tabular-nums">
                    {sensor.state} {sensor.unit}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Sheet open={Boolean(activePanel)} onOpenChange={(open) => setSearchValue("panel", open ? panel : null)}>
        <SheetContent side="right" className="w-full max-w-xl overflow-y-auto border-l border-border/80 bg-background/95">
          {activePanel ? (
            <>
              <SheetHeader className="border-b border-border/80 px-6 py-5 text-left">
                <SheetTitle>{activePanel.label}</SheetTitle>
                <SheetDescription>{activePanel.description}</SheetDescription>
              </SheetHeader>
              <div className="space-y-6 p-6">
                <Card className="surface-instrument border">
                  <CardHeader>
                    <CardTitle className="text-lg">Panel preview</CardTitle>
                    <CardDescription>Preserve route state in Athanor, then jump to Home Assistant for the full workflow.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm text-muted-foreground">
                      This drawer anchors the panel in the command center and gives you a consistent back path when you close it.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <Button asChild>
                        <a href={config.homeAssistant.url} target="_blank" rel="noopener noreferrer">
                          <ArrowUpRight className="mr-2 h-4 w-4" />
                          Open Home Assistant
                        </a>
                      </Button>
                      <Button asChild variant="outline">
                        <Link href="/monitoring">Open monitoring</Link>
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}
