"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Menu, Search, Sparkles } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { CommandPalette } from "@/components/command-palette";
import { Kbd } from "@/components/kbd";
import { MiniTrend } from "@/components/mini-trend";
import { RouteIcon } from "@/components/route-icon";
import { StatusDot } from "@/components/status-dot";
import { getOverview } from "@/lib/api";
import { getRouteFamiliesWithRoutes, getRouteLabel, getPrimaryRoutes } from "@/lib/navigation";
import { queryKeys } from "@/lib/query-client";
import { usePersistentState, STORAGE_KEYS, DEFAULT_UI_PREFERENCES } from "@/lib/state";
import { cn } from "@/lib/utils";
import { formatLatency, formatPercent, formatRelativeTime } from "@/lib/format";

const PRIMARY_ROUTES = getPrimaryRoutes();
const ROUTE_FAMILIES = getRouteFamiliesWithRoutes();
const DESKTOP_ROUTE_FAMILIES = ROUTE_FAMILIES.filter((family) => family.id !== "core");

function NavLinks({
  pathname,
  compact = false,
}: {
  pathname: string;
  compact?: boolean;
}) {
  return (
    <nav className={cn("space-y-4", compact && "space-y-3")}>
      {ROUTE_FAMILIES.map((family) => (
        <div key={family.id} className="space-y-1.5">
          <p className="px-3 text-[11px] uppercase tracking-[0.24em] text-muted-foreground">
            {family.label}
          </p>
          <div className="space-y-1">
            {family.routes.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center justify-between rounded-xl px-3 py-2.5 text-sm transition-colors",
                    active
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  )}
                >
                  <span className="flex items-center gap-3">
                    <RouteIcon icon={item.icon} className="h-4 w-4" />
                    {item.shortLabel ?? item.label}
                  </span>
                  {active ? <StatusDot tone="healthy" /> : null}
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [preferences] = usePersistentState(STORAGE_KEYS.uiPreferences, DEFAULT_UI_PREFERENCES);
  const overviewQuery = useQuery({
    queryKey: queryKeys.overview,
    queryFn: getOverview,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const overview = overviewQuery.data;
  const routeLabel = getRouteLabel(pathname);
  const degradedCount = overview?.summary.degradedServices ?? 0;
  const shellStateTone = degradedCount > 0 ? "warning" : "healthy";

  return (
    <div
      className={cn(
        "min-h-screen bg-background text-foreground",
        preferences.density === "compact" && "[&_[data-density-block]]:py-3"
      )}
    >
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} overview={overview} />

      <header className="fixed inset-x-0 top-0 z-40 border-b border-border/80 bg-background/85 backdrop-blur">
        <div className="flex h-[4.5rem] items-center gap-3 px-4 sm:px-6 lg:pl-[18.5rem]">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-3">
              <div className="hidden items-center gap-2 lg:flex">
                <StatusDot tone={shellStateTone} pulse={degradedCount > 0} />
                <p className="text-sm font-medium">{routeLabel}</p>
              </div>
              <Button
                variant="outline"
                className="hidden min-w-[16rem] justify-start gap-3 text-muted-foreground md:inline-flex"
                onClick={() => setPaletteOpen(true)}
              >
                <Search className="h-4 w-4" />
                Command palette
                <span className="ml-auto flex items-center gap-1">
                  <Kbd>Ctrl</Kbd>
                  <Kbd>K</Kbd>
                </span>
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="md:hidden"
                aria-label="Open command palette"
                onClick={() => setPaletteOpen(true)}
              >
                <Search className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="hidden items-center gap-3 xl:flex">
            <StatusChip
              label="Services"
              value={
                overview
                  ? `${overview.summary.healthyServices}/${overview.summary.totalServices}`
                  : "--"
              }
              tone={degradedCount > 0 ? "warning" : "healthy"}
              detail={overview ? `${overview.summary.degradedServices} degraded` : "Loading"}
            />
            <StatusChip
              label="Latency"
              value={overview ? formatLatency(overview.summary.averageLatencyMs) : "--"}
              tone="muted"
              detail={overview ? formatRelativeTime(overview.generatedAt) : "Loading"}
              detailVolatile
            />
            <StatusChip
              label="GPU"
              value={overview ? formatPercent(overview.summary.averageGpuUtilization, 0) : "--"}
              tone="healthy"
              detail="Fleet load"
            />
          </div>

          <div className="lg:hidden">
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="outline" size="icon" aria-label="Open navigation">
                  <Menu className="h-4 w-4" />
                </Button>
              </SheetTrigger>
              <SheetContent
                side="left"
                className="w-[18rem] border-r border-border/80 bg-sidebar/95 p-0 backdrop-blur"
                showCloseButton={false}
              >
                <SheetHeader className="border-b border-border/80 px-4 py-4 text-left">
                  <div>
                    <SheetTitle className="font-heading text-xl tracking-wide">Athanor</SheetTitle>
                    <SheetDescription>Operator command center</SheetDescription>
                  </div>
                </SheetHeader>
                <div className="p-3">
                  <NavLinks pathname={pathname} compact />
                </div>
                <div className="border-t border-border/80 p-4 text-sm text-muted-foreground">
                  Services, GPU telemetry, model chat, and agent workflows in one console.
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </header>

      <aside className="fixed inset-y-0 left-0 hidden w-[17rem] flex-col border-r border-border/80 bg-sidebar/88 px-4 pb-6 pt-6 backdrop-blur lg:flex">
        <Link href="/" className="rounded-2xl border border-border/70 bg-background/30 p-4">
          <p className="font-heading text-3xl font-semibold tracking-wide">Athanor</p>
          <p className="mt-1 text-xs uppercase tracking-[0.28em] text-muted-foreground">
            Command Center
          </p>
          <p className="mt-3 text-sm text-muted-foreground">
            Desktop-first operator console for cluster health, inference, and agents.
          </p>
        </Link>

        <div className="mt-6">
          <div className="space-y-4">
            <div className="space-y-2">
              <p className="px-3 text-[11px] uppercase tracking-[0.24em] text-muted-foreground">
                Quick Access
              </p>
              <div className="space-y-1">
                {PRIMARY_ROUTES.map((item) => {
                  const active = pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        "flex items-center justify-between rounded-xl px-3 py-3 text-sm transition-colors",
                        active
                          ? "bg-primary/10 text-primary"
                          : "text-muted-foreground hover:bg-accent hover:text-foreground"
                      )}
                    >
                      <span className="flex items-center gap-3">
                        <RouteIcon icon={item.icon} className="h-4 w-4" />
                        {item.shortLabel ?? item.label}
                      </span>
                      {active ? <StatusDot tone="healthy" /> : null}
                    </Link>
                  );
                })}
              </div>
            </div>
            <nav className="space-y-4">
              {DESKTOP_ROUTE_FAMILIES.map((family) => (
                <div key={family.id} className="space-y-1.5">
                  <p className="px-3 text-[11px] uppercase tracking-[0.24em] text-muted-foreground">
                    {family.label}
                  </p>
                  <div className="space-y-1">
                    {family.routes.map((item) => {
                      const active = pathname === item.href;
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          className={cn(
                            "flex items-center justify-between rounded-xl px-3 py-2.5 text-sm transition-colors",
                            active
                              ? "bg-primary/10 text-primary"
                              : "text-muted-foreground hover:bg-accent hover:text-foreground"
                          )}
                        >
                          <span className="flex items-center gap-3">
                            <RouteIcon icon={item.icon} className="h-4 w-4" />
                            {item.shortLabel ?? item.label}
                          </span>
                          {active ? <StatusDot tone="healthy" /> : null}
                        </Link>
                      );
                    })}
                  </div>
                </div>
              ))}
            </nav>
          </div>
        </div>

        <div className="mt-6 space-y-3 rounded-2xl border border-border/70 bg-background/20 p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Cluster</p>
            <StatusDot tone={shellStateTone} pulse={degradedCount > 0} />
          </div>
          <div>
            <p className="text-2xl font-semibold">
              {overview ? `${overview.summary.healthyServices}/${overview.summary.totalServices}` : "--"}
            </p>
            <p className="text-sm text-muted-foreground">
              {degradedCount > 0 ? `${degradedCount} services need attention` : "No active incidents"}
            </p>
          </div>
          <MiniTrend points={overview?.serviceTrend ?? []} />
        </div>

        <div className="mt-4 space-y-3 rounded-2xl border border-border/70 bg-background/20 p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Quick Actions</p>
            <Sparkles className="h-4 w-4 text-primary" />
          </div>
          <Button className="w-full justify-between" variant="outline" onClick={() => setPaletteOpen(true)}>
            Open palette
            <span className="flex items-center gap-1">
              <Kbd>Ctrl</Kbd>
              <Kbd>K</Kbd>
            </span>
          </Button>
          <Button asChild className="w-full justify-between" variant="ghost">
            <Link href="/services?status=degraded">View incidents</Link>
          </Button>
          <Button asChild className="w-full justify-between" variant="ghost">
            <Link href="/agents">Open agent console</Link>
          </Button>
          <Button asChild className="w-full justify-between" variant="ghost">
            <Link href="/workplanner">Project work planner</Link>
          </Button>
          <Button asChild className="w-full justify-between" variant="ghost">
            <Link href="/more">Browse all families</Link>
          </Button>
        </div>

        <div className="mt-auto rounded-2xl border border-border/70 bg-background/20 p-4">
          <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Shortcuts</p>
          <div className="mt-3 space-y-2 text-sm text-muted-foreground">
            <div className="flex items-center justify-between">
              <span>Command palette</span>
              <span className="flex items-center gap-1">
                <Kbd>Ctrl</Kbd>
                <Kbd>K</Kbd>
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span>Switch density</span>
              <Kbd>D</Kbd>
            </div>
          </div>
        </div>
      </aside>

      <main className="min-h-screen px-4 pb-8 pt-24 sm:px-6 lg:ml-[17rem] lg:px-8">{children}</main>
    </div>
  );
}

function StatusChip({
  label,
  value,
  detail,
  tone,
  detailVolatile = false,
}: {
  label: string;
  value: string;
  detail: string;
  tone: "healthy" | "warning" | "muted";
  detailVolatile?: boolean;
}) {
  return (
    <div className="min-w-[8rem] rounded-2xl border border-border/70 bg-background/30 px-3 py-2">
      <div className="flex items-center gap-2">
        <StatusDot tone={tone} />
        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
      </div>
      <p className="mt-1 text-sm font-semibold">{value}</p>
      <p className="text-xs text-muted-foreground" data-volatile={detailVolatile ? "true" : undefined}>
        {detail}
      </p>
    </div>
  );
}
