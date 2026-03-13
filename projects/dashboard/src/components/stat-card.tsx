import type { ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type StatTone = "default" | "success" | "warning" | "danger";

const toneClasses: Record<StatTone, string> = {
  default: "text-foreground",
  success: "text-[color:var(--signal-success)]",
  warning: "text-[color:var(--signal-warning)]",
  danger: "text-[color:var(--signal-danger)]",
};

interface StatCardProps {
  label: string;
  value: string;
  detail?: string;
  icon?: ReactNode;
  tone?: StatTone;
  valueVolatile?: boolean;
  detailVolatile?: boolean;
}

export function StatCard({
  label,
  value,
  detail,
  icon,
  tone = "default",
  valueVolatile = false,
  detailVolatile = false,
}: StatCardProps) {
  return (
    <Card className="surface-stat">
      <CardContent className="flex items-start justify-between gap-4 p-4">
        <div className="space-y-1">
          <p className="text-[11px] uppercase tracking-[0.24em] text-[color:var(--text-muted)]">{label}</p>
          <p
            className={cn("text-2xl font-semibold tracking-tight", toneClasses[tone])}
            data-volatile={valueVolatile ? "true" : undefined}
          >
            {value}
          </p>
          {detail && (
            <p
              className="text-sm text-muted-foreground"
              data-volatile={detailVolatile ? "true" : undefined}
            >
              {detail}
            </p>
          )}
        </div>

        {icon && (
          <div className="surface-metric rounded-xl border p-2.5 text-[color:var(--text-secondary)]">
            {icon}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
