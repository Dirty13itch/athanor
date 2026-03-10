import { NextRequest, NextResponse } from "next/server";
import { queryOne } from "@/lib/db";
import { generateReportNarrative } from "@/lib/litellm";
import { ULRICH_FIXTURE_MODE } from "@/lib/fixture-mode";
import { generateFixtureReport } from "@/lib/fixtures";
import type { ComplianceStandard, Report } from "@/types/report";

type InspectionRow = {
  id: string;
  address: string;
  builder: string;
  inspector: string;
  status: string;
  hers_index: number | null;
  orientation: string | null;
  sqft: number | null;
  ceiling_height: number | null;
  stories: number | null;
  foundation_type: string | null;
  blower_cfm50: number | null;
  blower_ach50: number | null;
  blower_enclosure_area: number | null;
  blower_pass_fail: boolean | null;
  duct_cfm25_total: number | null;
  duct_cfm25_outside: number | null;
  duct_test_method: string | null;
  insulation: unknown[];
  windows: unknown[];
  hvac_systems: unknown[];
};

type ReportRow = {
  id: string;
  inspection_id: string;
  hers_index: number | null;
  narrative: string | null;
  pdf_path: string | null;
  compliance_standard: string;
  template_id: string;
  status: string;
  generated_at: string | null;
  delivered_at: string | null;
  recipient_email: string | null;
  recommendations: unknown[];
};

// POST /api/reports/generate
// Fetches full inspection, generates AI narrative, stores result.
// Body: { inspectionId, reportId?, complianceStandard?, templateId? }
// If reportId provided: updates existing draft. Otherwise: inserts new report.
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const {
      inspectionId,
      reportId,
      complianceStandard = "minnesota_energy_code",
      templateId = "standard",
    } = body as {
      inspectionId: string;
      reportId?: string;
      complianceStandard?: string;
      templateId?: string;
    };

    if (!inspectionId) {
      return NextResponse.json(
        { error: "inspectionId is required" },
        { status: 400 },
      );
    }

    if (ULRICH_FIXTURE_MODE) {
      const report = generateFixtureReport({
        inspectionId,
        reportId,
        complianceStandard: complianceStandard as ComplianceStandard | undefined,
        templateId,
      });
      if (!report) {
        return NextResponse.json({ error: "Inspection not found" }, { status: 404 });
      }
      return NextResponse.json({ report }, { status: 201 });
    }

    const inspection = await queryOne<InspectionRow>(
      `SELECT * FROM inspections WHERE id = $1`,
      [inspectionId],
    );

    if (!inspection) {
      return NextResponse.json({ error: "Inspection not found" }, { status: 404 });
    }

    // Build structured data for the LLM
    const inspectionData: Record<string, unknown> = {
      address: inspection.address,
      builder: inspection.builder,
      inspector: inspection.inspector,
      hers_index: inspection.hers_index,
    };

    if (inspection.sqft !== null) {
      inspectionData.building_envelope = {
        orientation: inspection.orientation,
        sqft: inspection.sqft,
        ceiling_height: inspection.ceiling_height,
        stories: inspection.stories,
        foundation_type: inspection.foundation_type,
      };
    }

    if (inspection.blower_cfm50 !== null) {
      inspectionData.blower_door = {
        cfm50: inspection.blower_cfm50,
        ach50: inspection.blower_ach50,
        enclosure_area: inspection.blower_enclosure_area,
        pass_fail: inspection.blower_pass_fail,
      };
    }

    if (inspection.duct_cfm25_total !== null) {
      inspectionData.duct_leakage = {
        cfm25_total: inspection.duct_cfm25_total,
        cfm25_outside: inspection.duct_cfm25_outside,
        test_method: inspection.duct_test_method,
      };
    }

    if ((inspection.insulation as unknown[]).length > 0) {
      inspectionData.insulation = inspection.insulation;
    }
    if ((inspection.windows as unknown[]).length > 0) {
      inspectionData.windows = inspection.windows;
    }
    if ((inspection.hvac_systems as unknown[]).length > 0) {
      inspectionData.hvac_systems = inspection.hvac_systems;
    }

    const narrative = await generateReportNarrative(inspectionData);
    const generatedAt = new Date().toISOString();

    let row: ReportRow | null;

    if (reportId) {
      row = await queryOne<ReportRow>(
        `UPDATE reports
         SET narrative = $1, status = 'generated', generated_at = $2,
             compliance_standard = $3, template_id = $4
         WHERE id = $5
         RETURNING *`,
        [narrative, generatedAt, complianceStandard, templateId, reportId],
      );
    } else {
      row = await queryOne<ReportRow>(
        `INSERT INTO reports
           (inspection_id, narrative, compliance_standard, template_id, status, generated_at)
         VALUES ($1, $2, $3, $4, 'generated', $5)
         RETURNING *`,
        [inspectionId, narrative, complianceStandard, templateId, generatedAt],
      );
    }

    if (!row) throw new Error("Report upsert returned no row");

    const report: Report = {
      id: row.id,
      inspectionId: row.inspection_id,
      hersIndex: row.hers_index,
      narrative: row.narrative ?? "",
      pdfPath: row.pdf_path,
      complianceStandard: row.compliance_standard as Report["complianceStandard"],
      templateId: row.template_id,
      status: row.status as Report["status"],
      generatedAt: row.generated_at,
      deliveredAt: row.delivered_at,
      recipientEmail: row.recipient_email,
      recommendations: (row.recommendations ?? []) as Report["recommendations"],
    };

    return NextResponse.json({ report }, { status: 201 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("POST /api/reports/generate error:", err);
    return NextResponse.json(
      { error: "Report generation failed", details: message },
      { status: 500 },
    );
  }
}
