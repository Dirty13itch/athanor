import type { ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type StatTone = "default" | "success" | "warning" | "danger";

const toneClasses: Record<StatTone, string> = {
  default: "text-foreground",
  success: "text-emerald-400",
  warning: "text-amber-300",
  danger: "text-red-400",
};

interface StatCardProps {
  label: string;
  value: string;
  detail?: string;
  icon?: ReactNode;
  tone?: StatTone;
}

export function StatCard({
  label,
  value,
  detail,
  icon,
  tone = "default",
}: StatCardProps) {
  return (
    <Card className="border-border/70 bg-card/70">
      <CardContent className="flex items-start justify-between gap-4 p-4">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">{label}</p>
          <p className={cn("text-2xl font-semibold tracking-tight", toneClasses[tone])}>{value}</p>
          {detail && <p className="text-sm text-muted-foreground">{detail}</p>}
        </div>

        {icon && (
          <div className="rounded-md border border-border/70 bg-background/40 p-2 text-muted-foreground">
            {icon}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
