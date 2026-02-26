"use client";

import { useLens } from "@/hooks/use-lens";
import { PullToRefresh } from "@/components/pull-to-refresh";
import type { SectionId } from "@/lib/lens";
import type { ReactNode } from "react";

interface HomeSectionsProps {
  sections: Record<SectionId, ReactNode>;
}

export function HomeSections({ sections }: HomeSectionsProps) {
  const { config } = useLens();

  return (
    <PullToRefresh>
      <div className="space-y-6">
        {config.sections.map((id) => {
          const node = sections[id];
          if (!node) return null;
          return <div key={id}>{node}</div>;
        })}
      </div>
    </PullToRefresh>
  );
}
