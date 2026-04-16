"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useApiData } from "@/hooks/use-api-data";
import type { InspectionListItem } from "@/types/inspection";

const statusColors: Record<string, string> = {
  draft: "bg-muted-foreground/20 text-muted-foreground",
  submitted: "bg-warning/20 text-warning",
  reported: "bg-success/20 text-success",
  delivered: "bg-primary/20 text-primary",
};

export function InspectionsPageClient() {
  const searchParams = useSearchParams();
  const query = new URLSearchParams(searchParams.toString());
  const url = query.toString() ? `/api/inspections?${query}` : "/api/inspections";
  const { data, loading, error } = useApiData<{ inspections: InspectionListItem[] }>(url, {
    inspections: [],
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Inspections</h1>
          <p className="text-muted-foreground">All inspection jobs</p>
        </div>
        <Link
          href="/inspections/new"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          New
        </Link>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
          Loading inspections...
        </div>
      ) : (
        <div className="space-y-2">
          {data.inspections.map((insp) => (
            <Link
              key={insp.id}
              href={`/inspections/${insp.id}`}
              className="flex items-center justify-between rounded-lg border border-border bg-card p-4 transition-colors hover:bg-accent tap-highlight"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{insp.address}</p>
                <p className="text-sm text-muted-foreground">{insp.builder} · {new Date(insp.createdAt).toLocaleDateString()}</p>
              </div>
              <div className="ml-3 flex items-center gap-2">
                {insp.hersIndex !== undefined && (
                  <span className="text-sm font-mono font-medium">{insp.hersIndex}</span>
                )}
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[insp.status]}`}>
                  {insp.status}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
