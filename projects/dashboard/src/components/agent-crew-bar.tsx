"use client";

import { useSystemStream } from "@/hooks/use-system-stream";
import Link from "next/link";
import { cn } from "@/lib/utils";

const agentMeta: Record<string, { icon: string; color: string; shortName: string }> = {
  "general-assistant": { icon: "G", color: "oklch(0.75 0.08 65)", shortName: "General" },
  "media-agent":       { icon: "M", color: "oklch(0.65 0.12 160)", shortName: "Media" },
  "research-agent":    { icon: "R", color: "oklch(0.65 0.12 230)", shortName: "Research" },
  "creative-agent":    { icon: "C", color: "oklch(0.7 0.1 330)", shortName: "Creative" },
  "knowledge-agent":   { icon: "K", color: "oklch(0.6 0.06 90)", shortName: "Knowledge" },
  "home-agent":        { icon: "H", color: "oklch(0.65 0.18 145)", shortName: "Home" },
  "coding-agent":      { icon: "D", color: "oklch(0.55 0.1 230)", shortName: "Coding" },
  "stash-agent":       { icon: "S", color: "oklch(0.7 0.1 330)", shortName: "Stash" },
};

export function AgentCrewBar() {
  const { data } = useSystemStream();

  const agents = data?.agents.names ?? [];
  const isOnline = data?.agents.online ?? false;

  // Determine which agents are currently running tasks
  const busyAgents = new Set<string>();
  if (data?.tasks && typeof data.tasks === "object" && "by_agent" in data.tasks) {
    // We can't determine per-agent running state from stats alone,
    // but if currently_running > 0 we know some agents are busy
  }

  if (agents.length === 0) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-hide">
      <span className="shrink-0 text-xs font-medium text-muted-foreground">Crew</span>
      <div className="flex items-center gap-1.5">
        {agents.map((name) => {
          const meta = agentMeta[name] ?? { icon: name[0].toUpperCase(), color: "oklch(0.5 0 0)", shortName: name };
          return (
            <Link
              key={name}
              href={`/chat?agent=${name}`}
              className={cn(
                "group relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-bold transition-all",
                "hover:scale-110 hover:ring-2 hover:ring-primary/50",
                isOnline ? "opacity-100" : "opacity-40"
              )}
              style={{ backgroundColor: meta.color, color: "#111" }}
              title={`${meta.shortName} — ${isOnline ? "online" : "offline"}`}
            >
              {meta.icon}
              {/* Online indicator dot */}
              {isOnline && (
                <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border-2 border-background bg-green-500" />
              )}
              {/* Tooltip */}
              <span className="pointer-events-none absolute -bottom-6 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-popover px-1.5 py-0.5 text-[10px] text-popover-foreground opacity-0 shadow transition-opacity group-hover:opacity-100">
                {meta.shortName}
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
