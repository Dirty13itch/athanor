export type RouteFamilyId =
  | "command_center"
  | "operate"
  | "build"
  | "domains"
  | "catalog";

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
  | "governor"
  | "pipeline"
  | "projects"
  | "routing"
  | "topology"
  | "models"
  | "offline";

export type RouteClass = "canonical" | "compatibility_redirect" | "compatibility_shell";

export interface RouteDefinition {
  href: string;
  label: string;
  shortLabel?: string;
  description: string;
  family: RouteFamilyId;
  icon: RouteIconKey;
  primary: boolean;
  mobile: boolean;
  routeClass?: RouteClass;
}

export interface RouteFamilyDefinition {
  id: RouteFamilyId;
  label: string;
  description: string;
}

export interface RouteSelectionOptions {
  includeCompatibility?: boolean;
}

export const ROUTE_FAMILIES: RouteFamilyDefinition[] = [
  {
    id: "command_center",
    label: "Command Center",
    description: "Canonical front door for system posture, autonomy state, incidents, and launch surfaces.",
  },
  {
    id: "operate",
    label: "Operate",
    description: "Tasks, approvals, services, topology, runtime controls, and operator execution surfaces.",
  },
  {
    id: "build",
    label: "Build",
    description: "Chat, agents, models, routing, projects, and review surfaces for active system work.",
  },
  {
    id: "domains",
    label: "Domains",
    description: "Domain-specific consoles for media, home, and creative work.",
  },
  {
    id: "catalog",
    label: "Catalog",
    description: "Launchpad, route index, operator memory, and system-discovery surfaces.",
  },
];

export const ROUTES: RouteDefinition[] = [
  {
    href: "/",
    label: "Command Center",
    shortLabel: "Command",
    description: "System posture, autonomy state, incidents, and operator launch context.",
    family: "command_center",
    icon: "dashboard",
    primary: true,
    mobile: true,
  },
  {
    href: "/services",
    label: "Services",
    description: "Health, history, and drill-down actions for the service fleet.",
    family: "operate",
    icon: "services",
    primary: true,
    mobile: true,
  },
  {
    href: "/gpu",
    label: "GPU Metrics",
    description: "GPU load, thermal pressure, range history, and node comparison.",
    family: "operate",
    icon: "gpu",
    primary: true,
    mobile: true,
  },
  {
    href: "/workplanner",
    label: "Work Planner",
    description: "Compatibility redirect to the canonical backlog surface.",
    family: "operate",
    icon: "workplanner",
    primary: false,
    mobile: false,
    routeClass: "compatibility_redirect",
  },
  {
    href: "/ideas",
    label: "Ideas",
    description: "Low-commitment idea intake and promotion before work becomes a todo, backlog item, or project.",
    family: "operate",
    icon: "goals",
    primary: false,
    mobile: true,
  },
  {
    href: "/inbox",
    label: "Inbox",
    description: "Operator alerts, decisions, and conversion candidates distinct from the old notification lane.",
    family: "operate",
    icon: "notifications",
    primary: false,
    mobile: true,
  },
  {
    href: "/todos",
    label: "Todos",
    description: "Finite operator work distinct from the agent task queue.",
    family: "operate",
    icon: "tasks",
    primary: false,
    mobile: true,
  },
  {
    href: "/backlog",
    label: "Backlog",
    description: "Agent-eligible work capture, dispatch, and blocking state separate from the execution queue.",
    family: "operate",
    icon: "workplanner",
    primary: false,
    mobile: true,
  },
  {
    href: "/runs",
    label: "Runs",
    description: "Execution lineage, attempts, steps, and approval holds projected from canonical run truth.",
    family: "operate",
    icon: "pipeline",
    primary: false,
    mobile: true,
  },
  {
    href: "/tasks",
    label: "Tasks",
    description: "Compatibility redirect to the canonical runs surface.",
    family: "operate",
    icon: "tasks",
    primary: false,
    mobile: false,
    routeClass: "compatibility_redirect",
  },
  {
    href: "/governor",
    label: "Governor",
    description: "Runtime control plane for lanes, capacity, presence, and autonomy levels.",
    family: "operate",
    icon: "governor",
    primary: true,
    mobile: true,
  },
  {
    href: "/workforce",
    label: "Workforce Overview",
    shortLabel: "Workforce",
    description: "Aggregate workforce posture across tasks, goals, trust, and schedules.",
    family: "operate",
    icon: "dashboard",
    primary: false,
    mobile: false,
    routeClass: "compatibility_shell",
  },
  {
    href: "/goals",
    label: "Goals",
    description: "Compatibility redirect to the canonical todos surface.",
    family: "operate",
    icon: "goals",
    primary: false,
    mobile: false,
    routeClass: "compatibility_redirect",
  },
  {
    href: "/notifications",
    label: "Notifications",
    description: "Compatibility redirect to the canonical inbox surface.",
    family: "operate",
    icon: "notifications",
    primary: false,
    mobile: false,
    routeClass: "compatibility_redirect",
  },
  {
    href: "/operator",
    label: "Operator",
    description: "Meta-orchestrator chat, approval queue, and control posture.",
    family: "operate",
    icon: "chat",
    primary: false,
    mobile: true,
  },
  {
    href: "/terminal",
    label: "Terminal",
    description: "Operator terminal access and cluster escape hatch.",
    family: "operate",
    icon: "terminal",
    primary: false,
    mobile: true,
  },
  {
    href: "/monitoring",
    label: "Monitoring",
    shortLabel: "Monitoring",
    description: "Deep cluster monitoring with Grafana-linked drill-downs.",
    family: "operate",
    icon: "monitoring",
    primary: true,
    mobile: true,
  },
  {
    href: "/topology",
    label: "Topology",
    description: "Live system map for nodes, GPUs, models, agents, and service connections.",
    family: "operate",
    icon: "topology",
    primary: true,
    mobile: true,
  },
  {
    href: "/digest",
    label: "Digest",
    description: "Morning briefing for pending approvals, overnight results, and stalled projects.",
    family: "operate",
    icon: "notifications",
    primary: false,
    mobile: true,
  },
  {
    href: "/chat",
    label: "Direct Chat",
    description: "Operator chat sessions against configured model backends.",
    family: "build",
    icon: "chat",
    primary: true,
    mobile: true,
  },
  {
    href: "/agents",
    label: "Agent Console",
    shortLabel: "Agents",
    description: "Agent roster, tool use, threads, and live orchestration context.",
    family: "build",
    icon: "agents",
    primary: true,
    mobile: true,
  },
  {
    href: "/agents/workbench",
    label: "Agent Workbench",
    shortLabel: "Workbench",
    description: "Real-time agent control with live tasks, step traces, and direct steering.",
    family: "build",
    icon: "agents",
    primary: false,
    mobile: true,
  },
  {
    href: "/subscriptions",
    label: "Subscriptions",
    shortLabel: "Subs",
    description: "Canonical home for provider burn posture, spend tracking, lease tracking, and execution history.",
    family: "build",
    icon: "routing",
    primary: true,
    mobile: true,
  },
  {
    href: "/routing",
    label: "Routing",
    description: "Execution-lane visibility and provider health; burn posture lives in Subscriptions.",
    family: "build",
    icon: "routing",
    primary: false,
    mobile: true,
  },
  {
    href: "/models",
    label: "Models",
    description: "Local models, routing intelligence, and assignment matrix; provider economics live in Subscriptions.",
    family: "build",
    icon: "models",
    primary: true,
    mobile: true,
  },
  {
    href: "/projects",
    label: "Projects",
    shortLabel: "Projects",
    description: "Milestone tracking, autonomous continuation, and stall detection.",
    family: "build",
    icon: "projects",
    primary: false,
    mobile: true,
  },
  {
    href: "/bootstrap",
    label: "Bootstrap",
    description: "Recursive builder programs, relay posture, integration queue state, and takeover readiness.",
    family: "build",
    icon: "projects",
    primary: false,
    mobile: true,
  },
  {
    href: "/workspace",
    label: "Workspace",
    description: "Shared workspace state, subscriptions, and cross-agent coordination.",
    family: "build",
    icon: "workspace",
    primary: false,
    mobile: true,
  },
  {
    href: "/pipeline",
    label: "Pipeline",
    description: "Work pipeline flow from intent mining through execution and outcomes.",
    family: "build",
    icon: "pipeline",
    primary: false,
    mobile: true,
  },
  {
    href: "/review",
    label: "Review",
    description: "Approval queue, code/output inspection, and operator review context.",
    family: "build",
    icon: "review",
    primary: false,
    mobile: true,
  },
  {
    href: "/insights",
    label: "Insights",
    description: "Pattern detection, recommendations, and project-aware signals.",
    family: "build",
    icon: "insights",
    primary: false,
    mobile: true,
  },
  {
    href: "/learning",
    label: "Learning",
    description: "Learning health, benchmark posture, and improvement telemetry.",
    family: "build",
    icon: "learning",
    primary: false,
    mobile: true,
  },
  {
    href: "/improvement",
    label: "Improvement",
    description: "Nightly optimization, prompt variants, and benchmark health.",
    family: "build",
    icon: "learning",
    primary: false,
    mobile: true,
  },
  {
    href: "/activity",
    label: "Activity",
    description: "Agent action feed with project, agent, and status filtering.",
    family: "build",
    icon: "activity",
    primary: false,
    mobile: true,
  },
  {
    href: "/conversations",
    label: "Conversations",
    description: "Conversation history, transcripts, and linked execution context.",
    family: "build",
    icon: "conversations",
    primary: false,
    mobile: true,
  },
  {
    href: "/outputs",
    label: "Outputs",
    description: "Agent-generated files, previews, and review handoff links.",
    family: "build",
    icon: "outputs",
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
    href: "/catalog",
    label: "Catalog",
    shortLabel: "Catalog",
    description: "Canonical launchpad for approved tools, domain apps, routes, and runbooks.",
    family: "catalog",
    icon: "more",
    primary: true,
    mobile: true,
  },
  {
    href: "/more",
    label: "All Pages",
    shortLabel: "Pages",
    description: "Complete route index for every command-center page and fallback launcher.",
    family: "catalog",
    icon: "more",
    primary: false,
    mobile: true,
  },
  {
    href: "/preferences",
    label: "Preferences",
    shortLabel: "Preferences",
    description: "Operator memory, preference capture, and notification controls.",
    family: "catalog",
    icon: "preferences",
    primary: false,
    mobile: true,
  },
  {
    href: "/personal-data",
    label: "Personal Data",
    shortLabel: "Personal Data",
    description: "Semantic search, graph memory, and indexed personal knowledge.",
    family: "catalog",
    icon: "personal-data",
    primary: false,
    mobile: true,
  },
  {
    href: "/offline",
    label: "Offline",
    description: "Fallback page when the command center cannot reach the cluster.",
    family: "catalog",
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

function isCompatibilityRoute(route: RouteDefinition): boolean {
  return route.routeClass === "compatibility_redirect" || route.routeClass === "compatibility_shell";
}

export function getPrimaryRoutes() {
  return ROUTES.filter((route) => route.primary && !isCompatibilityRoute(route));
}

export function getMobileRoutes() {
  return ROUTES.filter((route) => route.mobile && !isCompatibilityRoute(route));
}

export function getRoutesForFamily(family: RouteFamilyId, options: RouteSelectionOptions = {}) {
  return ROUTES.filter((route) => {
    if (route.family !== family) {
      return false;
    }
    return options.includeCompatibility ? true : !isCompatibilityRoute(route);
  });
}

export function getRouteFamiliesWithRoutes(options: RouteSelectionOptions = {}) {
  return ROUTE_FAMILIES.map((family) => ({
    ...family,
    routes: getRoutesForFamily(family.id, options),
  })).filter((family) => family.routes.length > 0);
}

export function getCompatibilityRoutes() {
  return ROUTES.filter((route) => isCompatibilityRoute(route));
}
