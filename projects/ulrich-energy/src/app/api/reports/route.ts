import { NextResponse } from "next/server";
import { query, queryOne } from "@/lib/db";
import { ULRICH_FIXTURE_MODE } from "@/lib/fixture-mode";
import { createFixtureReportDraft, listFixtureReports } from "@/lib/fixtures";
import type { ReportListItem, GenerateReportRequest } from "@/types/report";

type DbRow = {
  id: string;
  inspection_id: string;
  address: string;
  hers_index: number | null;
  status: string;
  generated_at: string | null;
};

export async function GET() {
  if (ULRICH_FIXTURE_MODE) {
    return NextResponse.json({ reports: listFixtureReports() });
  }
  try {
    const rows = await query<DbRow>(`
      SELECT r.id, r.inspection_id, i.address, r.hers_index, r.status, r.generated_at
      FROM reports r
      JOIN inspections i ON r.inspection_id = i.id
      ORDER BY r.created_at DESC
      LIMIT 100
    `);
    const reports: ReportListItem[] = rows.map((r) => ({
      id: r.id,
      inspectionId: r.inspection_id,
      address: r.address,
      hersIndex: r.hers_index,
      status: r.status as ReportListItem["status"],
      generatedAt: r.generated_at,
    }));
    return NextResponse.json({ reports });
  } catch (err) {
    console.error("GET /api/reports error:", err);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  const body = (await request.json()) as GenerateReportRequest;

  if (!body.inspectionId) {
    return NextResponse.json(
      { error: "inspectionId is required" },
      { status: 400 },
    );
  }

  if (ULRICH_FIXTURE_MODE) {
    const report = createFixtureReportDraft(body);
    if (!report) {
      return NextResponse.json({ error: "Inspection not found" }, { status: 404 });
    }
    return NextResponse.json(
      {
        report: {
          id: report.id,
          inspectionId: report.inspectionId,
          address: listFixtureReports().find((entry) => entry.id === report.id)?.address ?? "Unknown address",
          hersIndex: report.hersIndex,
          status: report.status,
          generatedAt: report.generatedAt,
        },
      },
      { status: 201 },
    );
  }

  try {
    const row = await queryOne<DbRow>(`
      INSERT INTO reports (inspection_id, compliance_standard, template_id, status)
      VALUES ($1, $2, $3, 'draft')
      RETURNING id, inspection_id, status, hers_index, generated_at,
                (SELECT address FROM inspections WHERE id = $1) AS address
    `, [
      body.inspectionId,
      body.complianceStandard ?? "minnesota_energy_code",
      body.templateId ?? "standard",
    ]);

    if (!row) throw new Error("Insert returned no row");

    const report: ReportListItem = {
      id: row.id,
      inspectionId: row.inspection_id,
      address: row.address,
      hersIndex: row.hers_index,
      status: row.status as ReportListItem["status"],
      generatedAt: row.generated_at,
    };

    return NextResponse.json({ report }, { status: 201 });
  } catch (err) {
    console.error("POST /api/reports error:", err);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}
