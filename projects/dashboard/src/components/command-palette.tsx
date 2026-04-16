"use client";

import { useEffect } from "react";
import { Command } from "cmdk";
import { ArrowUpRight, Command as CommandIcon, FolderKanban, MonitorPlay, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { RouteIcon } from "@/components/route-icon";
import type { OverviewSnapshot } from "@/lib/contracts";
import { Kbd } from "@/components/kbd";
import { getRouteFamiliesWithRoutes } from "@/lib/navigation";
import { cn } from "@/lib/utils";

const ROUTE_FAMILIES = getRouteFamiliesWithRoutes();

export function CommandPalette({
  open,
  onOpenChange,
  overview,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  overview: OverviewSnapshot | undefined;
}) {
  const router = useRouter();

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        onOpenChange(!open);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onOpenChange, open]);

  function navigate(href: string) {
    onOpenChange(false);
    router.push(href);
  }

  function openExternal(url: string) {
    onOpenChange(false);
    window.open(url, "_blank", "noopener,noreferrer");
  }

  return (
    <Command.Dialog
      open={open}
      onOpenChange={onOpenChange}
      label="Command palette"
      className="fixed inset-0 z-50 overflow-hidden bg-black/60 p-4 backdrop-blur"
    >
      <div className="mx-auto mt-[10vh] w-full max-w-2xl overflow-hidden rounded-2xl border border-border/80 bg-background/95 shadow-2xl">
        <div className="flex items-center gap-3 border-b border-border/80 px-4 py-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <Command.Input
            className="h-10 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            placeholder="Jump to a route, tool, or priority item"
          />
          <Kbd>Esc</Kbd>
        </div>

        <Command.List className="max-h-[28rem] overflow-y-auto p-2">
          <Command.Empty className="px-3 py-8 text-center text-sm text-muted-foreground">
            No matching commands.
          </Command.Empty>

          {ROUTE_FAMILIES.map((family) => (
            <Command.Group
              key={family.id}
              heading={family.label}
              className="px-2 py-2 text-xs uppercase tracking-[0.24em] text-muted-foreground"
            >
              {family.routes.map((item) => (
                <Command.Item
                  key={item.href}
                  value={`${family.label} ${item.label} ${item.description}`}
                  onSelect={() => navigate(item.href)}
                  className={cn(
                    "flex cursor-pointer items-center justify-between rounded-xl px-3 py-3 text-sm outline-none data-[selected=true]:bg-accent"
                  )}
                >
                  <span className="flex items-center gap-3">
                    <RouteIcon icon={item.icon} className="h-4 w-4 text-primary" />
                    {item.label}
                  </span>
                  <Kbd>Go</Kbd>
                </Command.Item>
              ))}
            </Command.Group>
          ))}

          {overview?.alerts?.length ? (
            <Command.Group heading="Priority" className="px-2 py-2 text-xs uppercase tracking-[0.24em] text-muted-foreground">
              {overview.alerts.map((alert) => (
                <Command.Item
                  key={alert.id}
                  value={`${alert.title} ${alert.description}`}
                  onSelect={() => navigate(alert.href)}
                  className="flex cursor-pointer items-start gap-3 rounded-xl px-3 py-3 outline-none data-[selected=true]:bg-accent"
                >
                  <MonitorPlay className="mt-0.5 h-4 w-4 text-primary" />
                  <div>
                    <p className="text-sm font-medium">{alert.title}</p>
                    <p className="text-xs text-muted-foreground">{alert.description}</p>
                  </div>
                </Command.Item>
              ))}
            </Command.Group>
          ) : null}

          {overview?.projects?.length ? (
            <Command.Group heading="Projects" className="px-2 py-2 text-xs uppercase tracking-[0.24em] text-muted-foreground">
              {overview.projects.map((project) => (
                <Command.Item
                  key={project.id}
                  value={`${project.name} ${project.description} ${project.status}`}
                  onSelect={() => navigate(project.primaryRoute)}
                  className="flex cursor-pointer items-start gap-3 rounded-xl px-3 py-3 outline-none data-[selected=true]:bg-accent"
                >
                  <FolderKanban className="mt-0.5 h-4 w-4 text-primary" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium">{project.name}</p>
                    <p className="text-xs text-muted-foreground">{project.headline}</p>
                  </div>
                </Command.Item>
              ))}
            </Command.Group>
          ) : null}

          {overview?.externalTools?.length ? (
            <Command.Group heading="External Tools" className="px-2 py-2 text-xs uppercase tracking-[0.24em] text-muted-foreground">
              {overview.externalTools.map((tool) => (
                <Command.Item
                  key={tool.id}
                  value={`${tool.label} ${tool.description} ${tool.runtimeState} ${tool.runtimeDetail ?? ""}`}
                  onSelect={() => openExternal(tool.url)}
                  className="flex cursor-pointer items-center justify-between gap-3 rounded-xl px-3 py-3 text-sm outline-none data-[selected=true]:bg-accent"
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{tool.label}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {tool.runtimeState === "reachable"
                        ? tool.description
                        : `${tool.description} • runtime ${tool.runtimeState.replace(/_/g, " ")}${
                            tool.runtimeDetail ? ` (${tool.runtimeDetail})` : ""
                          }`}
                    </span>
                  </span>
                  <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
                </Command.Item>
              ))}
            </Command.Group>
          ) : null}
        </Command.List>

        <div className="flex items-center justify-between border-t border-border/80 px-4 py-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-2">
            <CommandIcon className="h-3.5 w-3.5" />
            Quick routes, incidents, and tooling
          </span>
          <span className="flex items-center gap-2">
            <Kbd>Ctrl</Kbd>
            <Kbd>K</Kbd>
          </span>
        </div>
      </div>
    </Command.Dialog>
  );
}
