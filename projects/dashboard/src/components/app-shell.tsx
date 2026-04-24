"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Menu, Search } from "lucide-react";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { LensSwitcher } from "@/components/lens-switcher";
import { CommandPalette } from "@/components/command-palette";
import { Kbd } from "@/components/kbd";
import { NavAttentionIndicator } from "@/components/nav-attention-indicator";
import { NavAttentionLabel } from "@/components/nav-attention-label";
import { NavAttentionProvider, useNavAttention } from "@/components/nav-attention-provider";
import { OperatorPresenceHeartbeat } from "@/components/operator-presence-heartbeat";
import { RouteIcon } from "@/components/route-icon";
import { StatusDot } from "@/components/status-dot";
import { getCapabilityPilotReadiness, getOverview } from "@/lib/api";
import {
  getBuilderKernelPressureLabel,
  getBuilderKernelPressureTone,
  getBuilderKernelSharedPressure,
} from "@/lib/builder-kernel-pressure";
import {
  getRouteFamiliesWithRoutes,
  getRouteLabel,
  type RouteIconKey,
} from "@/lib/navigation";
import { useOperatorUiPreferences } from "@/lib/operator-ui-preferences";
import { queryKeys } from "@/lib/query-client";
import {
  buildSteadyStateDecisionSummary,
  type SteadyStateDigestSnapshot,
  buildSteadyStateDigestSnapshot,
  describeSteadyStateDigestChange,
} from "@/lib/steady-state-summary";
import { STORAGE_KEYS, shouldPersistComparisonKey, usePersistentState } from "@/lib/state";
import { cn } from "@/lib/utils";
import { formatLatency, formatPercent, formatRelativeTime } from "@/lib/format";

const PushManager = dynamic(() => import("@/components/push-manager").then((m) => m.PushManager), {
  ssr: false,
});

const ROUTE_FAMILIES = getRouteFamiliesWithRoutes();
const PRIMARY_NAV_HREFS = new Set([
  "/",
  "/operator",
  "/builder",
  "/services",
  "/topology",
  "/routing",
  "/subscriptions",
  "/projects",
  "/catalog",
]);
const NAV_ROUTE_FAMILIES = ROUTE_FAMILIES.map((family) => ({
  ...family,
  routes: family.routes.filter((route) => PRIMARY_NAV_HREFS.has(route.href)),
})).filter((family) => family.routes.length > 0);

function NavRailItem({
  href,
  icon,
  label,
  shortLabel,
  active,
}: {
  href: string;
  icon: RouteIconKey;
  label: string;
  shortLabel?: string;
  active: boolean;
}) {
  const attention = useNavAttention(href, active);
  const railLabel = shortLabel ?? label;

  return (
    <Link
      href={href}
      className={cn(
        "nav-rail-link flex items-center justify-between rounded-lg px-3 py-2.5 text-sm transition-colors",
        active ? "text-foreground" : "text-muted-foreground hover:text-foreground",
      )}
      data-active={active ? "true" : "false"}
      data-attention-tier={attention.displayTier}
      title={attention.reason ?? undefined}
    >
      <span className="flex min-w-0 items-center gap-3">
        <RouteIcon icon={icon} className="h-4 w-4 shrink-0" />
        <span className="min-w-0 truncate">
          <NavAttentionLabel label={railLabel} attention={attention} />
        </span>
      </span>
      {active ? <StatusDot tone="healthy" /> : <NavAttentionIndicator attention={attention} />}
    </Link>
  );
}

function NavLinks({
  pathname,
  compact = false,
}: {
  pathname: string;
  compact?: boolean;
}) {
  return (
    <nav className={cn("space-y-4", compact && "space-y-3")}>
      {NAV_ROUTE_FAMILIES.map((family) => (
        <div key={family.id} className="space-y-1.5">
          <p className="px-3 text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            {family.label}
          </p>
          <div className="space-y-1">
            {family.routes.map((item) => {
              const active = pathname === item.href;
              return (
                <NavRailItem
                  key={item.href}
                  href={item.href}
                  icon={item.icon}
                  label={item.label}
                  shortLabel={item.shortLabel}
                  active={active}
                />
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );
}

function HeaderMetric({
  label,
  value,
  tone,
  detail,
}: {
  label: string;
  value: string;
  tone: "healthy" | "warning" | "danger";
  detail?: string;
}) {
  return (
    <div className="flex min-w-[5.5rem] items-start gap-2 border-l border-border/70 pl-4 first:border-l-0 first:pl-0">
      <StatusDot tone={tone} pulse={tone !== "healthy"} className="mt-1" />
      <div className="min-w-0">
        <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
        <p className="font-mono text-sm font-medium tracking-tight text-foreground">{value}</p>
        {detail ? <p className="text-[11px] text-muted-foreground">{detail}</p> : null}
      </div>
    </div>
  );
}

export function AppShell({
  children,
  initialOverview = null,
}: {
  children: React.ReactNode;
  initialOverview?: Awaited<ReturnType<typeof getOverview>> | null;
}) {
  const pathname = usePathname();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { preferences } = useOperatorUiPreferences();
  const overviewQuery = useQuery({
    queryKey: queryKeys.overview,
    queryFn: getOverview,
    initialData: initialOverview ?? undefined,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });
  const pilotReadinessQuery = useQuery({
    queryKey: ["app-shell-pilot-readiness"],
    queryFn: getCapabilityPilotReadiness,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const overview = overviewQuery.data ?? initialOverview ?? undefined;
  const pilotReadiness = pilotReadinessQuery.data;
  const blockedPilotCount = pilotReadiness?.summary.blocked ?? 0;
  const topBlockedPilot =
    pilotReadiness?.records.find(
      (record) => record.readinessState === "blocked" || record.formalEvalStatus === "failed",
    ) ?? pilotReadiness?.records[0] ?? null;
  const warningCount = overview?.summary.warningServices ?? 0;
  const degradedCount = overview?.summary.degradedServices ?? 0;
  const builderFrontDoor = overview?.builderFrontDoor ?? null;
  const builderCurrent = builderFrontDoor?.current_session ?? null;
  const builderSharedPressure = builderFrontDoor ? getBuilderKernelSharedPressure(builderFrontDoor) : null;
  const builderStatusLabel = builderFrontDoor ? getBuilderKernelPressureLabel(builderFrontDoor) : "ready";
  const builderTone = builderFrontDoor ? getBuilderKernelPressureTone(builderFrontDoor) : "healthy";
  const routeLabel = getRouteLabel(pathname);
  const shellIndicatorTone = degradedCount > 0 ? "danger" : warningCount > 0 ? "warning" : "healthy";
  const lastRefresh = overview ? formatRelativeTime(overview.generatedAt) : "Loading";
  const steadyStateSummary = buildSteadyStateDecisionSummary(overview?.steadyState ?? null, {
    attentionLabel:
      degradedCount > 0 ? "Service pressure" : warningCount > 0 ? "Warnings under watch" : "No action needed",
    attentionSummary: "Steady-state front door is not attached to this overview payload.",
    currentWorkTitle: "No governed work published.",
    currentWorkDetail: "Steady-state front door is not attached to this overview payload.",
    nextUpTitle: "No follow-on handoff published.",
    nextUpDetail: "Use the operator desk for the canonical attention lane.",
    queuePosture: "Steady-state queue posture unavailable.",
    needsYou: degradedCount > 0,
  });
  const steadyStateDigest = buildSteadyStateDigestSnapshot(
    overview?.steadyState ?? null,
    overview?.steadyStateReadStatus ?? null,
    {
      attentionLabel: steadyStateSummary.attentionLabel,
      attentionSummary: steadyStateSummary.attentionSummary,
      currentWorkTitle: steadyStateSummary.currentWorkTitle,
      currentWorkDetail: steadyStateSummary.currentWorkDetail,
      nextUpTitle: steadyStateSummary.nextUpTitle,
      nextUpDetail: steadyStateSummary.nextUpDetail,
      queuePosture: steadyStateSummary.queuePosture,
      needsYou: steadyStateSummary.needsYou,
    },
  );
  const [previousDigest, setPreviousDigest, digestHydrated] = usePersistentState<SteadyStateDigestSnapshot | null>(
    STORAGE_KEYS.steadyStateDigest,
    null,
  );

  useEffect(() => {
    if (!overview || !digestHydrated) {
      return;
    }

    if (shouldPersistComparisonKey(previousDigest, steadyStateDigest)) {
      setPreviousDigest(steadyStateDigest);
    }
  }, [digestHydrated, overview, previousDigest, setPreviousDigest, steadyStateDigest]);

  const digestChangeSummary = digestHydrated
    ? describeSteadyStateDigestChange(previousDigest, steadyStateDigest)
    : steadyStateDigest.degraded
      ? steadyStateDigest.changeHeadline
      : "Front door synced on this device.";

  return (
    <NavAttentionProvider overview={overview} pathname={pathname}>
      <div
        className={cn(
          "min-h-screen bg-background text-foreground",
          preferences.density === "compact" && "[&_[data-density-block]]:py-3",
        )}
      >
        <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} overview={overview} />
        <PushManager />
        <LensSwitcher />
        <OperatorPresenceHeartbeat />

        <header className="surface-chrome fixed inset-x-0 top-0 z-40 border-b">
          <div className="flex h-16 items-center gap-3 px-4 sm:px-6 lg:pl-[16.5rem]">
            <div className="hidden min-w-0 lg:block">
              <p className="text-[10px] uppercase tracking-[0.24em] text-muted-foreground">Athanor</p>
              <div className="mt-1 flex items-center gap-2">
                <StatusDot tone={shellIndicatorTone} pulse={degradedCount > 0 || warningCount > 0} />
                <p className="text-sm font-medium text-foreground">{routeLabel}</p>
              </div>
            </div>

            <div className="min-w-0 flex-1">
              <Button
                variant="outline"
                className="h-10 w-full justify-start gap-3 border-border/80 bg-transparent text-[color:var(--text-secondary)] hover:bg-[color:var(--state-hover)] hover:text-foreground md:max-w-[21rem]"
                onClick={() => setPaletteOpen(true)}
              >
                <Search className="h-4 w-4" />
                Command palette
                <span className="ml-auto hidden items-center gap-1 md:flex">
                  <Kbd>Ctrl</Kbd>
                  <Kbd>K</Kbd>
                </span>
              </Button>
            </div>

            <div className="hidden items-center gap-4 xl:flex">
              <HeaderMetric
                label="Services"
                value={overview ? `${overview.summary.healthyServices}/${overview.summary.totalServices}` : "--"}
                tone={shellIndicatorTone}
                detail={degradedCount > 0 ? `${degradedCount} degraded` : `${warningCount} warnings`}
              />
              <HeaderMetric
                label="Latency"
                value={overview ? formatLatency(overview.summary.averageLatencyMs) : "--"}
                tone="healthy"
                detail={lastRefresh}
              />
              <HeaderMetric
                label="GPU"
                value={overview ? formatPercent(overview.summary.averageGpuUtilization, 0) : "--"}
                tone={
                  overview?.summary.averageGpuUtilization !== null &&
                  (overview?.summary.averageGpuUtilization ?? 0) >= 80
                    ? "warning"
                    : "healthy"
                }
                detail="Fleet load"
              />
              <HeaderMetric
                label="Operator"
                value={overview ? steadyStateSummary.attentionLabel : "--"}
                tone={overview ? steadyStateSummary.attentionTone : "warning"}
                detail={overview ? `${steadyStateDigest.currentWorkTitle} · ${digestChangeSummary}` : "Loading front door"}
              />
              <HeaderMetric
                label="Builder"
                value={builderFrontDoor ? builderStatusLabel : "--"}
                tone={builderTone}
                detail={
                  builderFrontDoor
                    ? builderFrontDoor.degraded
                      ? builderFrontDoor.detail ?? "Builder summary degraded."
                      : builderCurrent
                        ? builderSharedPressure?.current_session_needs_sync
                          ? "Shared review/result evidence missing."
                          : builderSharedPressure && (
                                builderSharedPressure.current_session_pending_review_count > 0 ||
                                builderSharedPressure.current_session_actionable_result_count > 0
                              )
                            ? `${builderSharedPressure.current_session_pending_review_count} shared reviews · ${builderSharedPressure.current_session_actionable_result_count} result alerts`
                            : `${builderCurrent.primary_adapter} · ${builderCurrent.verification_status.replaceAll("_", " ")}`
                        : "No active builder session."
                    : "Loading builder front door"
                }
              />
              <HeaderMetric
                label="Activation"
                value={pilotReadiness ? `${blockedPilotCount} blocked` : "--"}
                tone={blockedPilotCount > 0 ? "warning" : "healthy"}
                detail={
                  pilotReadiness
                    ? topBlockedPilot?.label ?? "No activation blockers published."
                    : "Loading pilot readiness"
                }
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
                  className="surface-sidebar w-[17rem] border-r p-0"
                  showCloseButton={false}
                >
                  <SheetHeader className="border-b border-border/80 px-4 py-4 text-left">
                    <p className="text-[10px] uppercase tracking-[0.24em] text-muted-foreground">Mission Control</p>
                    <SheetTitle className="mt-2 font-heading text-xl font-medium tracking-[-0.03em]">
                      Athanor
                    </SheetTitle>
                  </SheetHeader>
                  <div className="p-3">
                    <NavLinks pathname={pathname} compact />
                  </div>
                </SheetContent>
              </Sheet>
            </div>
          </div>
        </header>

        <aside className="surface-sidebar fixed inset-y-0 left-0 hidden w-[15rem] flex-col border-r px-4 pb-5 pt-5 lg:flex">
          <Link href="/" className="px-3 py-2">
            <p className="text-[10px] uppercase tracking-[0.24em] text-muted-foreground">Mission Control</p>
            <p className="mt-2 font-heading text-[1.45rem] font-medium tracking-[-0.035em] text-foreground">
              Athanor
            </p>
            <p className="mt-1 text-xs text-muted-foreground">Operate the cluster. Jump only when needed.</p>
          </Link>

          <div className="mt-5 flex-1">
            <NavLinks pathname={pathname} />
          </div>

          <div className="mt-5 border-t border-border/70 px-3 pt-4">
            <p className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Operator digest</p>
            <div className="mt-2 flex items-center gap-2">
              <StatusDot tone={steadyStateDigest.attentionTone} pulse={steadyStateDigest.attentionTone !== "healthy"} />
              <p className="text-sm font-medium text-foreground">{steadyStateDigest.attentionLabel}</p>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Needs Shaun: {steadyStateDigest.needsYou ? "Yes" : "No"}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">{digestChangeSummary}</p>
            <div className="mt-3 space-y-2 text-xs text-muted-foreground">
              <p>
                <span className="text-foreground">Current:</span> {steadyStateDigest.currentWorkTitle}
              </p>
              <p>
                <span className="text-foreground">Next:</span> {steadyStateDigest.nextUpTitle}
              </p>
              <p>
                <span className="text-foreground">Queue:</span> {steadyStateDigest.queuePosture}
              </p>
              <p>
                <span className="text-foreground">Builder:</span>{" "}
                {builderCurrent
                  ? `${builderCurrent.status.replaceAll("_", " ")} · ${builderCurrent.primary_adapter}`
                  : builderFrontDoor
                    ? "ready for intake"
                    : "Loading"}
              </p>
              <p>
                <span className="text-foreground">Source:</span> {steadyStateDigest.sourceLabel}
              </p>
              <p>
                <span className="text-foreground">Activation:</span>{" "}
                {pilotReadiness ? `${blockedPilotCount} blocked` : "Loading"}
                {topBlockedPilot ? ` · ${topBlockedPilot.label}` : ""}
              </p>
              <p>Overview refreshed {lastRefresh.toLowerCase()}.</p>
            </div>
          </div>
        </aside>

        <main className="min-h-screen px-4 pb-8 pt-20 sm:px-6 lg:ml-[15rem] lg:px-8">{children}</main>
      </div>
    </NavAttentionProvider>
  );
}
