"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Home, RefreshCcw } from "lucide-react";
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

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Domain Console"
        title="Home"
        description="Home Assistant readiness, setup ladder, and focused panel launches without leaving the command center blind."
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
          <StatCard label="Runtime" value={snapshot.online ? "Reachable" : "Offline"} detail={snapshot.online ? "Probe succeeded." : "Probe failed or timed out."} tone={snapshot.online ? "success" : "warning"} />
          <StatCard label="Configured" value={snapshot.configured ? "Yes" : "No"} detail={`${completeSteps}/${snapshot.setupSteps.length} setup steps complete.`} tone={snapshot.configured ? "success" : "warning"} />
          <StatCard label="Featured project" value="Athanor" detail="Home remains a core domain lane inside the operator shell." />
          <StatCard label="Last snapshot" value={formatRelativeTime(snapshot.generatedAt)} detail={snapshot.summary} detailVolatile />
        </div>
      </PageHeader>

      <div className="grid gap-4 xl:grid-cols-[1.05fr_1fr]">
        <Card className="border-border/70 bg-card/70">
          <CardHeader>
            <CardTitle className="text-lg">Setup ladder</CardTitle>
            <CardDescription>Keep the home lane honest about what is complete, pending, or blocked.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {snapshot.setupSteps.map((step) => (
              <div key={step.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={step.status === "complete" ? "secondary" : step.status === "blocked" ? "destructive" : "outline"}>
                    {step.status}
                  </Badge>
                  <p className="font-medium">{step.label}</p>
                </div>
                {step.note ? <p className="mt-2 text-sm text-muted-foreground">{step.note}</p> : null}
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-card/70">
          <CardHeader>
            <CardTitle className="text-lg">Focused panels</CardTitle>
            <CardDescription>Drawer-based previews keep Home Assistant in the satellite role, not as a cloned in-dashboard app.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {snapshot.panels.length > 0 ? (
              snapshot.panels.map((entry) => (
                <button
                  key={entry.id}
                  type="button"
                  onClick={() => setSearchValue("panel", entry.id)}
                  className="w-full rounded-2xl border border-border/70 bg-background/20 p-4 text-left transition hover:bg-accent/40"
                >
                  <div className="flex items-center gap-3">
                    <div className="rounded-xl border border-border/70 bg-background/40 p-2 text-primary">
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

      <Sheet open={Boolean(activePanel)} onOpenChange={(open) => setSearchValue("panel", open ? panel : null)}>
        <SheetContent side="right" className="w-full max-w-xl overflow-y-auto border-l border-border/80 bg-background/95">
          {activePanel ? (
            <>
              <SheetHeader className="border-b border-border/80 px-6 py-5 text-left">
                <SheetTitle>{activePanel.label}</SheetTitle>
                <SheetDescription>{activePanel.description}</SheetDescription>
              </SheetHeader>
              <div className="space-y-6 p-6">
                <Card className="border-border/70 bg-card/70">
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
