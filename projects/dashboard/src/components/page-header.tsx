import type { ReactNode } from "react";
import { RouteAttentionChip } from "@/components/route-attention-chip";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description: string;
  actions?: ReactNode;
  children?: ReactNode;
  className?: string;
  attentionHref?: string;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  children,
  className,
  attentionHref,
}: PageHeaderProps) {
  return (
    <section className={cn("space-y-4", className)}>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-2">
          {eyebrow && (
            <p className="page-eyebrow">{eyebrow}</p>
          )}
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="font-heading text-3xl font-medium tracking-[-0.03em] text-foreground sm:text-4xl">
                {title}
              </h1>
              {attentionHref ? <RouteAttentionChip routeHref={attentionHref} /> : null}
            </div>
            <p className="max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)] sm:text-base">
              {description}
            </p>
          </div>
        </div>

        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>

      {children}
    </section>
  );
}
