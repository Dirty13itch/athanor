"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { startTransition, useState } from "react";
import { useApiData } from "@/hooks/use-api-data";
import type { Inspection } from "@/types/inspection";

type InspectionResponse = {
  inspection?: Inspection;
  error?: string;
};

export default function InspectionDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const inspectionId = typeof params.id === "string" ? params.id : params.id?.[0];
  const { data, loading, error } = useApiData<InspectionResponse>(
    `/api/inspections/${inspectionId}`,
    {},
  );
  const [generating, setGenerating] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const inspection = data.inspection;

  async function generateReport() {
    if (!inspection) {
      return;
    }

    setGenerating(true);
    setActionError(null);
    try {
      const response = await fetch("/api/reports/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ inspectionId: inspection.id }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.report?.id) {
        throw new Error(payload.error ?? `HTTP ${response.status}`);
      }
      startTransition(() => {
        router.push(`/reports/${payload.report.id}`);
      });
    } catch (requestError) {
      setActionError(
        requestError instanceof Error ? requestError.message : "Failed to generate report",
      );
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Inspection Detail</h1>
          <p className="text-muted-foreground">
            Review field data, then generate the client-facing report.
          </p>
        </div>
        <Link
          href="/inspections"
          className="rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
        >
          Back to Inspections
        </Link>
      </div>

      {loading && (
        <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
          Loading inspection...
        </div>
      )}

      {(error || data.error) && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error ?? data.error}
        </div>
      )}

      {inspection && (
        <>
          <div className="rounded-lg border border-border bg-card p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold">{inspection.address}</h2>
                <p className="text-sm text-muted-foreground">
                  {inspection.builder} · Inspector {inspection.inspector}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="rounded-full bg-primary/15 px-3 py-1 text-xs font-medium text-primary">
                  {inspection.status}
                </span>
                <button
                  type="button"
                  onClick={() => void generateReport()}
                  disabled={generating}
                  className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-60"
                >
                  {generating ? "Generating..." : "Generate Report"}
                </button>
              </div>
            </div>
            {actionError && <p className="mt-3 text-sm text-destructive">{actionError}</p>}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <section className="rounded-lg border border-border bg-card p-5">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Building Envelope
              </h3>
              {inspection.buildingEnvelope ? (
                <dl className="mt-3 space-y-2 text-sm">
                  <div className="flex justify-between gap-4">
                    <dt className="text-muted-foreground">Orientation</dt>
                    <dd>{inspection.buildingEnvelope.orientation}</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-muted-foreground">Sq Ft</dt>
                    <dd>{inspection.buildingEnvelope.sqft}</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-muted-foreground">Stories</dt>
                    <dd>{inspection.buildingEnvelope.stories}</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-muted-foreground">Foundation</dt>
                    <dd>{inspection.buildingEnvelope.foundationType}</dd>
                  </div>
                </dl>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">
                  Envelope data has not been recorded yet.
                </p>
              )}
            </section>

            <section className="rounded-lg border border-border bg-card p-5">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Test Results
              </h3>
              <div className="mt-3 space-y-3 text-sm">
                <div>
                  <p className="font-medium">Blower Door</p>
                  {inspection.blowerDoor ? (
                    <p className="text-muted-foreground">
                      {inspection.blowerDoor.cfm50} CFM50 · ACH50 {inspection.blowerDoor.ach50}
                    </p>
                  ) : (
                    <p className="text-muted-foreground">Not captured yet.</p>
                  )}
                </div>
                <div>
                  <p className="font-medium">Duct Leakage</p>
                  {inspection.ductLeakage ? (
                    <p className="text-muted-foreground">
                      {inspection.ductLeakage.cfm25Total} CFM25 total · {inspection.ductLeakage.cfm25Outside} outside
                    </p>
                  ) : (
                    <p className="text-muted-foreground">Not captured yet.</p>
                  )}
                </div>
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
