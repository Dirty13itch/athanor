"use client";

import { useState } from "react";
import { AgentDetailPanel } from "@/components/agent-detail-panel";
import { useLens } from "@/hooks/use-lens";
import { useSystemStream } from "@/hooks/use-system-stream";
import { cn } from "@/lib/utils";

type AgentMeta = {
  icon: string;
  color: string;
  foreground: string;
  shortName: string;
};

const FALLBACK_AGENT_META: AgentMeta = {
  icon: "?",
  color: "oklch(0.44 0.02 255)",
  foreground: "oklch(0.98 0.01 60)",
  shortName: "Agent",
};

const agentMeta: Record<string, AgentMeta> = {
  "general-assistant": {
    icon: "G",
    color: "oklch(0.75 0.08 65)",
    foreground: "oklch(0.12 0.01 60)",
    shortName: "General",
  },
  "media-agent": {
    icon: "M",
    color: "oklch(0.65 0.12 160)",
    foreground: "oklch(0.12 0.01 60)",
    shortName: "Media",
  },
  "research-agent": {
    icon: "R",
    color: "oklch(0.65 0.12 230)",
    foreground: "oklch(0.12 0.01 60)",
    shortName: "Research",
  },
  "creative-agent": {
    icon: "C",
    color: "oklch(0.7 0.1 330)",
    foreground: "oklch(0.12 0.01 60)",
    shortName: "Creative",
  },
  "knowledge-agent": {
    icon: "K",
    color: "oklch(0.54 0.06 90)",
    foreground: "oklch(0.98 0.01 60)",
    shortName: "Knowledge",
  },
  "home-agent": {
    icon: "H",
    color: "oklch(0.65 0.18 145)",
    foreground: "oklch(0.12 0.01 60)",
    shortName: "Home",
  },
  "coding-agent": {
    icon: "D",
    color: "oklch(0.48 0.1 230)",
    foreground: "oklch(0.98 0.01 60)",
    shortName: "Coding",
  },
  "stash-agent": {
    icon: "S",
    color: "oklch(0.7 0.1 330)",
    foreground: "oklch(0.12 0.01 60)",
    shortName: "Stash",
  },
  "data-curator": {
    icon: "U",
    color: "oklch(0.44 0.02 255)",
    foreground: "oklch(0.98 0.01 60)",
    shortName: "Curator",
  },
};

function resolveAgentMeta(name: string): AgentMeta {
  return agentMeta[name] ?? { ...FALLBACK_AGENT_META, icon: name[0]?.toUpperCase() ?? "?", shortName: name };
}

export function AgentCrewBar({ onAgentFilter }: { onAgentFilter?: (agent: string | null) => void } = {}) {
  const { data } = useSystemStream();
  const { config } = useLens();
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [filteredAgent, setFilteredAgent] = useState<string | null>(null);

  const agents = data?.agents.names ?? [];
  const isOnline = data?.agents.online ?? false;

  const lensAgents = config.agents;
  const hasLensFilter = lensAgents.length > 0;

  if (agents.length === 0) {
    return null;
  }

  const selectedMeta = selectedAgent
    ? resolveAgentMeta(selectedAgent)
    : { ...FALLBACK_AGENT_META, icon: "", color: "", foreground: "", shortName: "" };

  return (
    <>
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-hide sm:gap-2">
        <span className="shrink-0 text-[10px] font-medium text-muted-foreground sm:text-xs">Crew</span>
        <div className="flex items-center gap-1 sm:gap-1.5 sm:flex-wrap">
          {agents.map((name) => {
            const meta = resolveAgentMeta(name);
            const isLensHighlighted = hasLensFilter && lensAgents.includes(name);
            const isDimmed = hasLensFilter && !lensAgents.includes(name);

            return (
              <button
                key={name}
                onClick={() => {
                  if (onAgentFilter) {
                    const next = filteredAgent === name ? null : name;
                    setFilteredAgent(next);
                    onAgentFilter(next);
                  } else {
                    setSelectedAgent(name);
                  }
                }}
                onDoubleClick={() => setSelectedAgent(name)}
                className={cn(
                  "group relative flex shrink-0 items-center justify-center rounded-full font-bold transition-all",
                  "h-8 w-8 text-[10px] sm:h-9 sm:w-9 sm:text-xs",
                  "hover:scale-110 hover:ring-2 hover:ring-primary/50",
                  "active:scale-95",
                  isOnline && !isDimmed ? "opacity-100" : "opacity-40",
                  isLensHighlighted && "ring-2 ring-primary/60 animate-pulse",
                  filteredAgent === name && "ring-2 ring-primary scale-110"
                )}
                style={{ backgroundColor: meta.color, color: meta.foreground }}
                title={`${meta.shortName} - ${isOnline ? "online" : "offline"}`}
              >
                {meta.icon}
                {isOnline && (
                  <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full border-[1.5px] border-background bg-green-500 sm:h-2.5 sm:w-2.5 sm:border-2" />
                )}
                <span className="pointer-events-none absolute -bottom-6 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-popover px-1.5 py-0.5 text-[10px] text-popover-foreground opacity-0 shadow transition-opacity group-hover:opacity-100">
                  {meta.shortName}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <AgentDetailPanel
        agentName={selectedAgent}
        agentColor={selectedMeta.color}
        agentIcon={selectedMeta.icon}
        onClose={() => setSelectedAgent(null)}
      />
    </>
  );
}
