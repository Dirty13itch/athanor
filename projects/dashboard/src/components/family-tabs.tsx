"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";

export interface FamilyTab {
  href: string;
  label: string;
  description?: string;
}

export function FamilyTabs({ tabs }: { tabs: FamilyTab[] }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const query = searchParams.toString();

  return (
    <div className="flex flex-wrap gap-2">
      {tabs.map((tab) => {
        const active = pathname === tab.href;
        const href = query ? `${tab.href}?${query}` : tab.href;
        return (
          <Link
            key={tab.href}
            href={href}
            className={cn(
              "rounded-full border px-3 py-1.5 text-sm transition",
              active
                ? "border-primary bg-primary/10 text-primary"
                : "border-border/70 text-muted-foreground hover:bg-accent"
            )}
          >
            {tab.label}
          </Link>
        );
      })}
    </div>
  );
}
