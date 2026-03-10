"use client";

import Link from "next/link";
import { useApiData } from "@/hooks/use-api-data";
import type { ReportListItem } from "@/types/report";

const statusColors: Record<string, string> = {
  draft: "bg-muted-foreground/20 text-muted-foreground",
  generated: "bg-success/20 text-success",
  reviewed: "bg-warning/20 text-warning",
  delivered: "bg-primary/20 text-primary",
};

export default function ReportsPage() {
  const { data, loading, error } = useApiData<{ reports: ReportListItem[] }>("/api/reports", {
    reports: [],
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Reports</h1>
        <p className="text-muted-foreground">Generated HERS rating reports</p>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
          Loading reports...
        </div>
      ) : (
        <div className="space-y-2">
          {data.reports.map((report) => (
            <Link
              key={report.id}
              href={`/reports/${report.id}`}
              className="flex items-center justify-between rounded-lg border border-border bg-card p-4 transition-colors hover:bg-accent"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{report.address}</p>
                <p className="text-sm text-muted-foreground">
                  HERS Index: {report.hersIndex ?? "--"} · {report.generatedAt ? new Date(report.generatedAt).toLocaleDateString() : "Pending"}
                </p>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[report.status]}`}>
                {report.status}
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
