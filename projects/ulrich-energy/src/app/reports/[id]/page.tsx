"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useApiData } from "@/hooks/use-api-data";
import type { Report } from "@/types/report";

type ReportResponse = {
  report?: Report;
  error?: string;
};

export default function ReportDetailPage() {
  const params = useParams<{ id: string }>();
  const reportId = typeof params.id === "string" ? params.id : params.id?.[0];
  const { data, loading, error } = useApiData<ReportResponse>(`/api/reports/${reportId}`, {});
  const report = data.report;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Report Detail</h1>
          <p className="text-muted-foreground">
            Generated homeowner-facing report narrative and recommendations.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/reports"
            className="rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
          >
            Back to Reports
          </Link>
          {report && (
            <>
              <a
                href={`/api/reports/${reportId}/pdf`}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
              >
                View PDF
              </a>
              <Link
                href={`/inspections/${report.inspectionId}`}
                className="rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
              >
                Open Inspection
              </Link>
            </>
          )}
        </div>
      </div>

      {loading && (
        <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
          Loading report...
        </div>
      )}

      {(error || data.error) && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error ?? data.error}
        </div>
      )}

      {report && (
        <>
          <div className="rounded-lg border border-border bg-card p-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold">Inspection {report.inspectionId}</h2>
                <p className="text-sm text-muted-foreground">
                  Status {report.status} · Generated {report.generatedAt ?? "Pending"}
                </p>
              </div>
              <div className="rounded-full bg-success/15 px-3 py-1 text-xs font-medium text-success">
                HERS {report.hersIndex ?? "--"}
              </div>
            </div>
          </div>

          <section className="rounded-lg border border-border bg-card p-5">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Narrative
            </h3>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-7">{report.narrative}</p>
          </section>

          <section className="rounded-lg border border-border bg-card p-5">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Recommendations
            </h3>
            <div className="mt-3 space-y-3">
              {report.recommendations.length > 0 ? (
                report.recommendations.map((recommendation) => (
                  <div key={recommendation.id} className="rounded-md border border-border/70 bg-background p-4">
                    <div className="flex items-center justify-between gap-4">
                      <p className="font-medium">{recommendation.description}</p>
                      <span className="rounded-full bg-warning/15 px-2 py-1 text-xs font-medium text-warning">
                        {recommendation.priority}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {recommendation.category} · {recommendation.estimatedCost} · {recommendation.estimatedSavings}
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">
                  Recommendations will appear after generation completes.
                </p>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
