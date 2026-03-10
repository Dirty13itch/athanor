export type RouteFamilyId =
  | "core"
  | "workforce"
  | "history"
  | "intelligence"
  | "memory"
  | "domains"
  | "support";

export type RouteIconKey =
  | "dashboard"
  | "services"
  | "gpu"
  | "workplanner"
  | "chat"
  | "agents"
  | "tasks"
  | "goals"
  | "notifications"
  | "workspace"
  | "activity"
  | "conversations"
  | "outputs"
  | "insights"
  | "learning"
  | "review"
  | "preferences"
  | "personal-data"
  | "monitoring"
  | "media"
  | "gallery"
  | "home"
  | "terminal"
  | "more"
  | "offline";

export interface RouteDefinition {
  href: string;
  label: string;
  shortLabel?: string;
  description: string;
  family: RouteFamilyId;
  icon: RouteIconKey;
  primary: boolean;
  mobile: boolean;
}

export interface RouteFamilyDefinition {
  id: RouteFamilyId;
  label: string;
  description: string;
}

export const ROUTE_FAMILIES: RouteFamilyDefinition[] = [
  {
    id: "core",
    label: "Command Center",
    description: "Cluster posture, services, GPUs, direct chat, and agent operations.",
  },
  {
    id: "workforce",
    label: "Workforce",
    description: "Tasks, goals, notifications, workspace, and project planning.",
  },
  {
    id: "history",
    label: "History / Handoff",
    description: "Recent activity, conversations, outputs, and operator handoff trails.",
  },
  {
    id: "intelligence",
    label: "Intelligence",
    description: "Insights, learning health, benchmarks, and review queues.",
  },
  {
    id: "memory",
    label: "Memory",
    description: "Preferences, semantic search, graph memory, and personal data.",
  },
  {
    id: "domains",
    label: "Domain Consoles",
    description: "Monitoring, media, gallery, home, and operator utility surfaces.",
  },
  {
    id: "support",
    label: "Support",
    description: "Fallback and route index surfaces.",
  },
];

export const ROUTES: RouteDefinition[] = [
  {
    href: "/",
    label: "Command Center",
    shortLabel: "Dashboard",
    description: "System posture, workforce status, project context, and active priorities.",
    family: "core",
    icon: "dashboard",
    primary: true,
    mobile: true,
  },
  {
    href: "/services",
    label: "Services",
    description: "Health, history, and drill-down actions for the service fleet.",
    family: "core",
    icon: "services",
    primary: true,
    mobile: true,
  },
  {
    href: "/gpu",
    label: "GPU Metrics",
    description: "GPU load, thermal pressure, range history, and node comparison.",
    family: "core",
    icon: "gpu",
    primary: true,
    mobile: true,
  },
  {
    href: "/workplanner",
    label: "Work Planner",
    description: "Project-first planning and current workplan posture.",
    family: "core",
    icon: "workplanner",
    primary: true,
    mobile: true,
  },
  {
    href: "/chat",
    label: "Direct Chat",
    description: "Operator chat sessions against configured model backends.",
    family: "core",
    icon: "chat",
    primary: true,
    mobile: true,
  },
  {
    href: "/agents",
    label: "Agent Console",
    shortLabel: "Agents",
    description: "Agent roster, tool use, threads, and live orchestration context.",
    family: "core",
    icon: "agents",
    primary: true,
    mobile: true,
  },
  {
    href: "/tasks",
    label: "Tasks",
    description: "Queued, running, failed, and approval-bound workforce tasks.",
    family: "workforce",
    icon: "tasks",
    primary: false,
    mobile: true,
  },
  {
    href: "/goals",
    label: "Goals",
    description: "Agent goals, focus lanes, and project-aligned intent.",
    family: "workforce",
    icon: "goals",
    primary: false,
    mobile: true,
  },
  {
    href: "/notifications",
    label: "Notifications",
    description: "Escalations, approvals, and action-worthy operator notices.",
    family: "workforce",
    icon: "notifications",
    primary: false,
    mobile: true,
  },
  {
    href: "/workspace",
    label: "Workspace",
    description: "Shared workspace state, subscriptions, and cross-agent coordination.",
    family: "workforce",
    icon: "workspace",
    primary: false,
    mobile: true,
  },
  {
    href: "/activity",
    label: "Activity",
    description: "Agent action feed with project, agent, and status filtering.",
    family: "history",
    icon: "activity",
    primary: false,
    mobile: true,
  },
  {
    href: "/conversations",
    label: "Conversations",
    description: "Conversation history, transcripts, and linked execution context.",
    family: "history",
    icon: "conversations",
    primary: false,
    mobile: true,
  },
  {
    href: "/outputs",
    label: "Outputs",
    description: "Agent-generated files, previews, and review handoff links.",
    family: "history",
    icon: "outputs",
    primary: false,
    mobile: true,
  },
  {
    href: "/insights",
    label: "Insights",
    description: "Pattern detection, recommendations, and project-aware signals.",
    family: "intelligence",
    icon: "insights",
    primary: false,
    mobile: true,
  },
  {
    href: "/learning",
    label: "Learning",
    description: "Learning health, benchmark posture, and improvement telemetry.",
    family: "intelligence",
    icon: "learning",
    primary: false,
    mobile: true,
  },
  {
    href: "/review",
    label: "Review",
    description: "Approval queue, code/output inspection, and operator review context.",
    family: "intelligence",
    icon: "review",
    primary: false,
    mobile: true,
  },
  {
    href: "/preferences",
    label: "Preferences",
    shortLabel: "Preferences",
    description: "Operator memory, preference capture, and notification controls.",
    family: "memory",
    icon: "preferences",
    primary: false,
    mobile: true,
  },
  {
    href: "/personal-data",
    label: "Personal Data",
    shortLabel: "Personal Data",
    description: "Semantic search, graph memory, and indexed personal knowledge.",
    family: "memory",
    icon: "personal-data",
    primary: false,
    mobile: true,
  },
  {
    href: "/monitoring",
    label: "Monitoring",
    shortLabel: "Monitoring",
    description: "Deep cluster monitoring with Grafana-linked drill-downs.",
    family: "domains",
    icon: "monitoring",
    primary: false,
    mobile: true,
  },
  {
    href: "/media",
    label: "Media",
    shortLabel: "Media",
    description: "VAULT media operations across Plex, Sonarr, Radarr, and Stash.",
    family: "domains",
    icon: "media",
    primary: false,
    mobile: true,
  },
  {
    href: "/gallery",
    label: "Gallery",
    description: "Creative generation history, queue state, and ComfyUI launch context.",
    family: "domains",
    icon: "gallery",
    primary: false,
    mobile: true,
  },
  {
    href: "/home",
    label: "Home",
    description: "Home Assistant setup, domain readiness, and focused home-control context.",
    family: "domains",
    icon: "home",
    primary: false,
    mobile: true,
  },
  {
    href: "/terminal",
    label: "Terminal",
    description: "Operator terminal access and cluster escape hatch.",
    family: "domains",
    icon: "terminal",
    primary: false,
    mobile: true,
  },
  {
    href: "/more",
    label: "More",
    description: "Family-aware route index and mobile route launcher.",
    family: "support",
    icon: "more",
    primary: false,
    mobile: true,
  },
  {
    href: "/offline",
    label: "Offline",
    description: "Fallback page when the dashboard cannot reach the cluster.",
    family: "support",
    icon: "offline",
    primary: false,
    mobile: false,
  },
];

export function getRouteByHref(href: string): RouteDefinition | undefined {
  return ROUTES.find((route) => route.href === href);
}

export function getRouteLabel(pathname: string): string {
  return getRouteByHref(pathname)?.label ?? "Command Center";
}

export function getPrimaryRoutes() {
  return ROUTES.filter((route) => route.primary);
}

export function getMobileRoutes() {
  return ROUTES.filter((route) => route.mobile);
}

export function getRoutesForFamily(family: RouteFamilyId) {
  return ROUTES.filter((route) => route.family === family);
}

export function getRouteFamiliesWithRoutes() {
  return ROUTE_FAMILIES.map((family) => ({
    ...family,
    routes: getRoutesForFamily(family.id),
  })).filter((family) => family.routes.length > 0);
}
