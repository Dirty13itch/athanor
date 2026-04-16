import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Bell,
  Bot,
  Brain,
  Boxes,
  CircuitBoard,
  Clock3,
  Cpu,
  Database,
  Diff,
  Film,
  FolderKanban,
  GalleryHorizontalEnd,
  GitBranch,
  Home,
  LayoutDashboard,
  ListChecks,
  MessageSquare,
  MessagesSquare,
  Network,
  Package,
  SearchCheck,
  Server,
  ShieldCheck,
  SlidersHorizontal,
  Target,
  TerminalSquare,
  WifiOff,
  Workflow,
  Zap,
  MoreHorizontal,
} from "lucide-react";
import type { RouteIconKey } from "@/lib/navigation";

const iconMap: Record<RouteIconKey, LucideIcon> = {
  dashboard: LayoutDashboard,
  services: Server,
  gpu: Cpu,
  workplanner: FolderKanban,
  chat: MessageSquare,
  agents: Bot,
  tasks: ListChecks,
  governor: ShieldCheck,
  goals: Target,
  notifications: Bell,
  workspace: Zap,
  activity: Clock3,
  conversations: MessagesSquare,
  outputs: Package,
  insights: SearchCheck,
  learning: Brain,
  review: Diff,
  preferences: SlidersHorizontal,
  "personal-data": Database,
  projects: GitBranch,
  pipeline: Workflow,
  routing: Network,
  topology: Boxes,
  models: CircuitBoard,
  monitoring: Activity,
  media: Film,
  gallery: GalleryHorizontalEnd,
  home: Home,
  terminal: TerminalSquare,
  more: MoreHorizontal,
  offline: WifiOff,
};

export function RouteIcon({
  icon,
  className,
}: {
  icon: RouteIconKey;
  className?: string;
}) {
  const Icon = iconMap[icon];
  return <Icon className={className} />;
}
