"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowUpRight } from "lucide-react";
import { LensSwitcher } from "@/components/lens-switcher";
import { PageHeader } from "@/components/page-header";
import { RouteIcon } from "@/components/route-icon";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useLens } from "@/hooks/use-lens";
import { getCompatibilityRoutes, getRouteFamiliesWithRoutes, type RouteDefinition } from "@/lib/navigation";

const ROUTE_FAMILIES = getRouteFamiliesWithRoutes();
const COMPATIBILITY_ROUTES = getCompatibilityRoutes();

function routeIndexTestId(href: string) {
  if (href === "/") {
    return "route-index-root";
  }

  return `route-index-${href.replace(/\//g, "-").replace(/^-+/, "")}`;
}

function renderRouteCard(
  route: RouteDefinition,
  familyLabel: string,
  pathname: string,
  lensQuery: string,
  familyOverride?: string
) {
  const active = pathname === route.href;
  const routeLabel = route.href === "/" ? route.label : route.shortLabel ?? route.label;
  const showsAlias = route.label !== routeLabel;
  const familyText = familyOverride ?? familyLabel;

  return (
    <Link
      key={route.href}
      href={`${route.href}${lensQuery}`}
      aria-label={routeLabel}
      data-testid={routeIndexTestId(route.href)}
      className={cn(
        "rounded-2xl border border-border/70 bg-background/20 p-4 transition hover:bg-accent/40",
        active && "border-primary/60 bg-primary/5"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="rounded-xl border border-border/70 bg-background/50 p-2 text-primary">
              <RouteIcon icon={route.icon} className="h-4 w-4" />
            </div>
            <div>
              <p className="font-medium">{routeLabel}</p>
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                {showsAlias ? `${familyText} - ${route.label}` : familyText}
              </p>
            </div>
          </div>
          <p className="text-sm text-muted-foreground">{route.description}</p>
        </div>
        <ArrowUpRight className="h-4 w-4 shrink-0 text-muted-foreground" />
      </div>
    </Link>
  );
}

export default function MorePage() {
  const pathname = usePathname();
  const { lens } = useLens();
  const lensQuery = lens !== "default" ? `?lens=${lens}` : "";

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Catalog"
        title="All Pages"
        description="Complete route index for every command-center page when you need the full map instead of the curated launchpad."
      />

      <Card className="border-border/70 bg-card/70">
        <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-medium">Lens</p>
            <p className="text-sm text-muted-foreground">
              Keep route deep links aligned to the current project lens where supported.
            </p>
          </div>
          <LensSwitcher />
        </CardContent>
      </Card>

      <div className="space-y-6" data-testid="route-index-families">
        {ROUTE_FAMILIES.map((family) => (
          <Card key={family.id} className="border-border/70 bg-card/70">
            <CardHeader>
              <CardTitle className="text-lg">{family.label}</CardTitle>
              <CardDescription>{family.description}</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {family.routes.map((route) => renderRouteCard(route, family.label, pathname, lensQuery))}
            </CardContent>
          </Card>
        ))}

        {COMPATIBILITY_ROUTES.length > 0 ? (
          <Card className="border-border/70 bg-card/70">
            <CardHeader>
              <CardTitle className="text-lg">Compatibility Surfaces</CardTitle>
              <CardDescription>
                Legacy redirects and compatibility shells are still reachable here, but they are no longer part of the
                first-class operator shell.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {COMPATIBILITY_ROUTES.map((route) =>
                renderRouteCard(route, "Compatibility", pathname, lensQuery, "Compatibility")
              )}
            </CardContent>
          </Card>
        ) : null}
      </div>
    </div>
  );
}
