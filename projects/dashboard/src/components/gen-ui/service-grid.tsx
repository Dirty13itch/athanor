"use client";

import type { ServiceHealthParsed } from "@/lib/generative-ui";

export function ServiceGrid({ services }: { services: ServiceHealthParsed[] }) {
  const up = services.filter((s) => s.status === "up").length;
  const total = services.length;

  return (
    <div className="space-y-2">
      <div className="text-xs font-medium">
        <span className="text-green-500">{up}</span>
        <span className="text-muted-foreground">/{total} services up</span>
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {services.map((s, i) => (
          <div key={i} className="flex items-center gap-1 text-xs">
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                s.status === "up" ? "bg-green-500" : "bg-red-500"
              }`}
            />
            <span className="text-foreground/80">{s.name}</span>
            {s.node && (
              <span className="text-muted-foreground text-[10px]">({s.node})</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
