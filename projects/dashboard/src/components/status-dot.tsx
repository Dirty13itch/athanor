import { cn } from "@/lib/utils";

type StatusTone = "success" | "healthy" | "warning" | "danger" | "muted";

const toneClasses: Record<StatusTone, string> = {
  success: "bg-emerald-500",
  healthy: "bg-emerald-500",
  warning: "bg-amber-400",
  danger: "bg-red-500",
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
