import { cn } from "@/lib/utils";

type StatusTone = "success" | "healthy" | "warning" | "danger" | "muted" | "info" | "review" | "paused";

const toneClasses: Record<StatusTone, string> = {
  success: "bg-[color:var(--signal-success)]",
  healthy: "bg-[color:var(--signal-success)]",
  warning: "bg-[color:var(--signal-warning)]",
  danger: "bg-[color:var(--signal-danger)]",
  info: "bg-[color:var(--signal-info)]",
  review: "bg-[color:var(--signal-review)]",
  paused: "bg-[color:var(--signal-paused)]",
  muted: "bg-muted-foreground/40",
};

interface StatusDotProps {
  tone: StatusTone;
  pulse?: boolean;
  className?: string;
}

export function StatusDot({ tone, pulse = false, className }: StatusDotProps) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "inline-flex h-2.5 w-2.5 rounded-full",
        toneClasses[tone],
        pulse && "animate-pulse",
        className
      )}
    />
  );
}
