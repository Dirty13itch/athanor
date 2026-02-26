"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { useLens } from "@/hooks/use-lens";
import { LENS_IDS, LENS_CONFIG, type LensId } from "@/lib/lens";

const pages = [
  { href: "/", label: "Dashboard", keywords: "home overview" },
  { href: "/gpu", label: "GPUs", keywords: "gpu vram inference" },
  { href: "/monitoring", label: "Monitoring", keywords: "prometheus grafana metrics" },
  { href: "/agents", label: "Agents", keywords: "agent crew bot" },
  { href: "/chat", label: "Chat", keywords: "message conversation talk" },
  { href: "/gallery", label: "Gallery", keywords: "image photo generation" },
  { href: "/media", label: "Media", keywords: "plex sonarr radarr movie tv" },
  { href: "/home", label: "Home", keywords: "automation homeassistant lights" },
  { href: "/services", label: "Services", keywords: "health status uptime" },
  { href: "/tasks", label: "Tasks", keywords: "queue job worker" },
  { href: "/outputs", label: "Outputs", keywords: "files produced artifacts content" },
  { href: "/workspace", label: "Workspace", keywords: "gwt workspace events" },
  { href: "/conversations", label: "Conversations", keywords: "history chat log" },
  { href: "/activity", label: "Activity", keywords: "log timeline recent" },
  { href: "/notifications", label: "Notifications", keywords: "alert bell push" },
  { href: "/preferences", label: "Preferences", keywords: "settings config" },
];

const agents = [
  { id: "general-assistant", label: "General Assistant", keywords: "general help" },
  { id: "media-agent", label: "Media Agent", keywords: "plex sonarr radarr media" },
  { id: "research-agent", label: "Research Agent", keywords: "research search knowledge" },
  { id: "creative-agent", label: "Creative Agent", keywords: "image video generation comfyui" },
  { id: "knowledge-agent", label: "Knowledge Agent", keywords: "knowledge qdrant documents" },
  { id: "home-agent", label: "Home Agent", keywords: "home assistant automation lights" },
  { id: "coding-agent", label: "Coding Agent", keywords: "code programming development" },
  { id: "stash-agent", label: "Stash Agent", keywords: "stash adult content" },
];

const quickActions = [
  { id: "chat-new", label: "New Chat", href: "/chat", keywords: "new conversation" },
  { id: "task-create", label: "Create Task", href: "/tasks", keywords: "new task submit" },
  { id: "gpu-status", label: "GPU Status", href: "/gpu", keywords: "gpu vram utilization" },
  { id: "services-health", label: "Service Health", href: "/services", keywords: "health check status" },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const { setLens } = useLens();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const runCommand = useCallback(
    (command: () => void) => {
      setOpen(false);
      command();
    },
    []
  );

  return (
    <>
      {/* Mobile trigger button */}
      <button
        onClick={() => setOpen(true)}
        className="fixed right-4 bottom-20 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-transform active:scale-95 md:hidden"
        aria-label="Open command palette"
      >
        <SearchIcon className="h-5 w-5" />
      </button>

      <CommandDialog
        open={open}
        onOpenChange={setOpen}
        title="Command Palette"
        description="Search pages, agents, and actions"
        showCloseButton={false}
      >
        <CommandInput placeholder="Where to? Search pages, agents, actions..." />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>

          <CommandGroup heading="Quick Actions">
            {quickActions.map((action) => (
              <CommandItem
                key={action.id}
                value={`${action.label} ${action.keywords}`}
                onSelect={() =>
                  runCommand(() => router.push(action.href))
                }
              >
                <ZapIcon className="mr-2 h-4 w-4 text-amber" />
                {action.label}
              </CommandItem>
            ))}
          </CommandGroup>

          <CommandSeparator />

          <CommandGroup heading="Pages">
            {pages.map((page) => (
              <CommandItem
                key={page.href}
                value={`${page.label} ${page.keywords}`}
                onSelect={() =>
                  runCommand(() => router.push(page.href))
                }
              >
                <FileIcon className="mr-2 h-4 w-4" />
                {page.label}
              </CommandItem>
            ))}
          </CommandGroup>

          <CommandSeparator />

          <CommandGroup heading="Talk to Agent">
            {agents.map((agent) => (
              <CommandItem
                key={agent.id}
                value={`${agent.label} ${agent.keywords}`}
                onSelect={() =>
                  runCommand(() =>
                    router.push(`/chat?agent=${agent.id}`)
                  )
                }
              >
                <BotIcon className="mr-2 h-4 w-4 text-primary" />
                {agent.label}
              </CommandItem>
            ))}
          </CommandGroup>

          <CommandSeparator />

          <CommandGroup heading="Switch Lens">
            {LENS_IDS.map((id) => {
              const cfg = LENS_CONFIG[id];
              return (
                <CommandItem
                  key={id}
                  value={`lens ${cfg.label} ${id}`}
                  onSelect={() =>
                    runCommand(() => setLens(id as LensId))
                  }
                >
                  <LensIcon className="mr-2 h-4 w-4" style={{ color: cfg.accent }} />
                  {cfg.label}
                </CommandItem>
              );
            })}
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </>
  );
}

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  );
}

function ZapIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z" />
    </svg>
  );
}

function FileIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
      <path d="M14 2v4a2 2 0 0 0 2 2h4" />
    </svg>
  );
}

function BotIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M12 8V4H8" />
      <rect width="16" height="12" x="4" y="8" rx="2" />
      <path d="M2 14h2" /><path d="M20 14h2" />
      <path d="M15 13v2" /><path d="M9 13v2" />
    </svg>
  );
}

function LensIcon({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className} style={style}>
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="4" />
      <line x1="21.17" x2="12" y1="8" y2="8" /><line x1="3.95" x2="8.54" y1="6.06" y2="14" />
      <line x1="10.88" x2="15.46" y1="21.94" y2="14" />
    </svg>
  );
}
