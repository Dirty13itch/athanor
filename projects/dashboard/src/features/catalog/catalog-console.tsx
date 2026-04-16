import Link from "next/link";
import {
  ArrowUpRight,
  ExternalLink,
  FolderKanban,
  LayoutGrid,
  Network,
  PanelTop,
} from "lucide-react";
import operatorSurfaces from "@/generated/operator-surfaces.json";
import { PageHeader } from "@/components/page-header";
import { RouteIcon } from "@/components/route-icon";
import { StatCard } from "@/components/stat-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { config } from "@/lib/config";
import { getRouteFamiliesWithRoutes } from "@/lib/navigation";

const ROUTE_FAMILIES = getRouteFamiliesWithRoutes();

const TOOL_CATEGORY_LABELS: Record<string, string> = {
  ai: "AI",
  creative: "Creative",
  project: "Projects",
  home: "Home",
  knowledge: "Knowledge",
  media: "Media",
  monitoring: "Monitoring",
};

function groupToolsByCategory() {
  const grouped = new Map<string, typeof operatorSurfaces.externalTools>();
  for (const tool of operatorSurfaces.externalTools) {
    const existing = grouped.get(tool.category) ?? [];
    existing.push(tool);
    grouped.set(tool.category, existing);
  }

   for (const [, tools] of grouped) {
    tools.sort((left, right) => {
      const leftPenalty = left.runtimeState === "reachable" ? 1 : 0;
      const rightPenalty = right.runtimeState === "reachable" ? 1 : 0;
      if (leftPenalty !== rightPenalty) {
        return leftPenalty - rightPenalty;
      }
      return left.label.localeCompare(right.label);
    });
  }

  return Array.from(grouped.entries()).sort(([left], [right]) => left.localeCompare(right));
}

function formatDeploymentMode(value: string) {
  return value.replace(/_/g, " ");
}

function formatRuntimeState(value: string) {
  return value.replace(/_/g, " ");
}

function runtimeBadgeVariant(value: string): "default" | "secondary" | "destructive" | "outline" {
  if (value === "reachable") {
    return "default";
  }
  if (value === "http_error" || value === "unreachable") {
    return "destructive";
  }
  return "outline";
}

export function CatalogConsole() {
  const routeCount = ROUTE_FAMILIES.reduce((sum, family) => sum + family.routes.length, 0);
  const toolNodeCount = new Set(operatorSurfaces.externalTools.map((tool) => tool.node)).size;
  const firstClassProjects = config.projectRegistry.filter((project) => project.firstClass).length;
  const toolGroups = groupToolsByCategory();
  const frontDoor = operatorSurfaces.frontDoor;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Launchpad"
        title="Catalog"
        description="Canonical launchpad for approved routes, specialist tools, project surfaces, and operator front-door posture."
        attentionHref="/catalog"
        actions={
          <>
            <Button asChild size="sm" variant="outline">
              <Link href="/more">Full route index</Link>
            </Button>
            <Button asChild size="sm" variant="outline">
              <a href={frontDoor.runtimeUrl} target="_blank" rel="noopener noreferrer">
                Runtime fallback
              </a>
            </Button>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Front door"
          value={frontDoor.node}
          detail={frontDoor.canonicalUrl.replace(/^https?:\/\//, "")}
          icon={<PanelTop className="h-4 w-4" />}
          tone="success"
        />
        <StatCard
          label="Route families"
          value={String(ROUTE_FAMILIES.length)}
          detail={`${routeCount} routes`}
          icon={<LayoutGrid className="h-4 w-4" />}
        />
        <StatCard
          label="Specialist tools"
          value={String(operatorSurfaces.externalTools.length)}
          detail={`${toolNodeCount} nodes`}
          icon={<Network className="h-4 w-4" />}
        />
        <StatCard
          label="Projects"
          value={String(config.projectRegistry.length)}
          detail={`${firstClassProjects} first-class`}
          icon={<FolderKanban className="h-4 w-4" />}
        />
      </div>

      <Card className="border-border/70 bg-card/70">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <PanelTop className="h-5 w-5 text-primary" />
            {frontDoor.label}
          </CardTitle>
          <CardDescription>
            One canonical portal for system posture and approvals, with node-host deep links for specialist tools.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <Badge>{frontDoor.status.replace(/_/g, " ")}</Badge>
              <Badge variant="outline">{formatDeploymentMode(frontDoor.deploymentMode)}</Badge>
              <Badge variant="secondary">{frontDoor.node}</Badge>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-border/70 bg-background/20 p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Canonical URL</p>
                <p className="mt-2 break-all text-sm font-medium">{frontDoor.canonicalUrl}</p>
              </div>
              <div className="rounded-2xl border border-border/70 bg-background/20 p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Runtime fallback</p>
                <p className="mt-2 break-all text-sm font-medium">{frontDoor.runtimeUrl}</p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-border/70 bg-background/20 p-4">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Operator rule</p>
            <p className="mt-3 text-sm text-muted-foreground">
              Stay in the command center for posture, incidents, approvals, and autonomy state. Launch outward only
              when a specialist tool is the correct execution surface.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button asChild size="sm">
                <Link href="/">Command Center</Link>
              </Button>
              <Button asChild size="sm" variant="ghost">
                <Link href="/operator">Operator controls</Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="border-border/70 bg-card/70">
          <CardHeader>
            <CardTitle>Route families</CardTitle>
            <CardDescription>Canonical internal pages grouped the same way the shell and command palette expose them.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {ROUTE_FAMILIES.map((family) => (
              <div key={family.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                <div className="mb-3">
                  <p className="text-sm font-medium">{family.label}</p>
                  <p className="text-sm text-muted-foreground">{family.description}</p>
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  {family.routes.map((route) => (
                    <Link
                      key={route.href}
                      href={route.href}
                      className="flex items-center justify-between rounded-xl border border-border/70 bg-background/40 px-3 py-3 text-sm transition hover:bg-accent/40"
                    >
                      <span className="flex min-w-0 items-center gap-3">
                        <RouteIcon icon={route.icon} className="h-4 w-4 shrink-0 text-primary" />
                        <span className="truncate">{route.label}</span>
                      </span>
                      <ArrowUpRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-card/70">
          <CardHeader>
            <CardTitle>Project surfaces</CardTitle>
            <CardDescription>First-class and scaffolded project lanes exposed through the command center.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {config.projectRegistry.map((project) => (
              <div key={project.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium">{project.name}</p>
                  <Badge variant={project.firstClass ? "default" : "outline"}>
                    {project.firstClass ? "first-class" : project.kind}
                  </Badge>
                  <Badge variant="secondary">{project.status.replace(/_/g, " ")}</Badge>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{project.headline}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button asChild size="sm" variant="outline">
                    <Link href={project.primaryRoute}>Open in portal</Link>
                  </Button>
                  {project.externalUrl ? (
                    <Button asChild size="sm" variant="ghost">
                      <a href={project.externalUrl} target="_blank" rel="noopener noreferrer">
                        External surface
                      </a>
                    </Button>
                  ) : null}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/70 bg-card/70">
        <CardHeader>
          <CardTitle>Specialist tools</CardTitle>
          <CardDescription>Approved deep links grouped by domain instead of competing with the command center as a second portal.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {toolGroups.map(([category, tools]) => (
            <div key={category} className="space-y-3">
              <div className="flex items-center gap-2">
                <Badge variant="outline">{TOOL_CATEGORY_LABELS[category] ?? category}</Badge>
                <p className="text-sm text-muted-foreground">{tools.length} surfaces</p>
              </div>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {tools.map((tool) => (
                  <a
                    key={tool.id}
                    href={tool.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex min-h-[44px] items-start justify-between gap-3 rounded-2xl border border-border/70 bg-background/20 p-4 transition hover:bg-accent/40"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-medium">{tool.label}</p>
                        <Badge variant="secondary">{tool.node}</Badge>
                        <Badge variant={runtimeBadgeVariant(tool.runtimeState)}>
                          {formatRuntimeState(tool.runtimeState)}
                        </Badge>
                      </div>
                      <p className="mt-2 text-sm text-muted-foreground">{tool.description}</p>
                      {tool.runtimeState !== "reachable" ? (
                        <p className="mt-2 text-xs text-muted-foreground">
                          Runtime probe: {tool.runtimeDetail ?? "unreachable"}
                        </p>
                      ) : null}
                    </div>
                    <ExternalLink className="h-4 w-4 shrink-0 text-muted-foreground" />
                  </a>
                ))}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
