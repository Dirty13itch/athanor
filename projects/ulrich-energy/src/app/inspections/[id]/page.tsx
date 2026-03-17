"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { startTransition, useCallback, useState } from "react";
import { useApiData } from "@/hooks/use-api-data";
import type { Inspection } from "@/types/inspection";
import {
  BuildingEnvelopeSection,
  BlowerDoorSection,
  DuctLeakageSection,
  InsulationSection,
  WindowsSection,
  HvacSection,
  PhotosSection,
} from "@/components/inspection-sections";

type InspectionResponse = {
  inspection?: Inspection;
  error?: string;
};

export default function InspectionDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const inspectionId = typeof params.id === "string" ? params.id : params.id?.[0];
  const { data, loading, error, refresh } = useApiData<InspectionResponse>(
    `/api/inspections/${inspectionId}`,
    {},
  );
  const [generating, setGenerating] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const inspection = data.inspection;

  const handleSectionSave = useCallback(
    async (sectionData: Partial<Inspection>) => {
      const response = await fetch(`/api/inspections/${inspectionId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(sectionData),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(
          (payload as { error?: string }).error ?? `HTTP ${response.status}`,
        );
      }
      refresh();
    },
    [inspectionId, refresh],
  );

  async function generateReport() {
    if (!inspection) return;
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
        requestError instanceof Error
          ? requestError.message
          : "Failed to generate report",
      );
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Inspection Detail
          </h1>
          <p className="text-muted-foreground">
            Record field data section by section, then generate the report.
          </p>
        </div>
        <Link
          href="/inspections"
          className="rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
        >
          Back
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
          {/* Header card */}
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
            {actionError && (
              <p className="mt-3 text-sm text-destructive">{actionError}</p>
            )}
          </div>

          {/* Section completion tracker */}
          <div className="flex flex-wrap gap-2">
            {[
              { label: "Envelope", done: !!inspection.buildingEnvelope },
              { label: "Blower Door", done: !!inspection.blowerDoor },
              { label: "Duct Leakage", done: !!inspection.ductLeakage },
              {
                label: "Insulation",
                done: inspection.insulation.length > 0,
              },
              { label: "Windows", done: inspection.windows.length > 0 },
              { label: "HVAC", done: inspection.hvacSystems.length > 0 },
            ].map(({ label, done }) => (
              <span
                key={label}
                className={`rounded-full px-3 py-1 text-xs font-medium ${
                  done
                    ? "bg-emerald-500/15 text-emerald-600"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {done ? "\u2713" : "\u25CB"} {label}
              </span>
            ))}
          </div>

          {/* Editable sections */}
          <div className="grid gap-4 md:grid-cols-2">
            <BuildingEnvelopeSection
              inspection={inspection}
              onSave={handleSectionSave}
            />
            <BlowerDoorSection
              inspection={inspection}
              onSave={handleSectionSave}
            />
            <DuctLeakageSection
              inspection={inspection}
              onSave={handleSectionSave}
            />
            <HvacSection
              inspection={inspection}
              onSave={handleSectionSave}
            />
          </div>

          {/* Full-width sections for lists */}
          <InsulationSection
            inspection={inspection}
            onSave={handleSectionSave}
          />
          <WindowsSection
            inspection={inspection}
            onSave={handleSectionSave}
          />
          <PhotosSection
            inspection={inspection}
            onSave={handleSectionSave}
          />
        </>
      )}
    </div>
  );
}
