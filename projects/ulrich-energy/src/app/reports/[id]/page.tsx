"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useApiData } from "@/hooks/use-api-data";
import type { Report } from "@/types/report";

type ReportResponse = {
  report?: Report;
  error?: string;
};

export default function ReportDetailPage() {
  const params = useParams<{ id: string }>();
  const reportId = typeof params.id === "string" ? params.id : params.id?.[0];
  const { data, loading, error, refresh } = useApiData<ReportResponse>(`/api/reports/${reportId}`, {});
  const report = data.report;
  const [sendEmail, setSendEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<string | null>(null);

  async function handleSend() {
    if (!sendEmail.includes("@")) return;
    setSending(true);
    setSendResult(null);
    try {
      const resp = await fetch(`/api/reports/${reportId}/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ recipientEmail: sendEmail }),
      });
      const payload = await resp.json();
      if (payload.sent) {
        setSendResult(`Report sent to ${sendEmail}`);
      } else if (payload.queued) {
        setSendResult(`Delivery recorded for ${sendEmail} (SMTP not configured)`);
      } else {
        setSendResult(payload.error ?? "Send failed");
      }
      refresh();
    } catch {
      setSendResult("Network error");
    } finally {
      setSending(false);
    }
  }

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

          {/* Email delivery */}
          <section className="rounded-lg border border-border bg-card p-5">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Deliver to Client
            </h3>
            {report.deliveredAt ? (
              <p className="mt-3 text-sm text-muted-foreground">
                Delivered to {report.recipientEmail} on{" "}
                {new Date(report.deliveredAt).toLocaleDateString()}
              </p>
            ) : (
              <div className="mt-3 flex gap-2">
                <input
                  type="email"
                  value={sendEmail}
                  onChange={(e) => setSendEmail(e.target.value)}
                  placeholder="client@email.com"
                  className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
                <button
                  type="button"
                  onClick={() => void handleSend()}
                  disabled={sending || !sendEmail.includes("@")}
                  className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-60"
                >
                  {sending ? "Sending..." : "Send"}
                </button>
              </div>
            )}
            {sendResult && (
              <p className="mt-2 text-sm text-muted-foreground">{sendResult}</p>
            )}
          </section>
        </>
      )}
    </div>
  );
}
