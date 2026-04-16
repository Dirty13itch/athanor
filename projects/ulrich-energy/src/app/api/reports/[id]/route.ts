import { NextResponse } from "next/server";
import { queryOne } from "@/lib/db";
import { ULRICH_FIXTURE_MODE } from "@/lib/fixture-mode";
import { getFixtureReport, updateFixtureReport } from "@/lib/fixtures";
import type { Report } from "@/types/report";

type DbRow = {
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

function rowToReport(r: DbRow): Report {
  return {
    id: r.id,
    inspectionId: r.inspection_id,
    hersIndex: r.hers_index,
    narrative: r.narrative ?? "",
    pdfPath: r.pdf_path,
    complianceStandard: r.compliance_standard as Report["complianceStandard"],
    templateId: r.template_id,
    status: r.status as Report["status"],
    generatedAt: r.generated_at,
    deliveredAt: r.delivered_at,
    recipientEmail: r.recipient_email,
    recommendations: (r.recommendations ?? []) as Report["recommendations"],
  };
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  if (ULRICH_FIXTURE_MODE) {
    const report = getFixtureReport(id);
    if (!report) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    return NextResponse.json({ report });
  }
  try {
    const row = await queryOne<DbRow>(
      `SELECT * FROM reports WHERE id = $1`,
      [id],
    );
    if (!row) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    return NextResponse.json({ report: rowToReport(row) });
  } catch (err) {
    console.error("GET /api/reports/[id] error:", err);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const body = await request.json();

  if (ULRICH_FIXTURE_MODE) {
    const report = updateFixtureReport(id, body as Partial<Report>);
    if (!report) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    return NextResponse.json({ report });
  }

  const fieldMap: Record<string, string> = {
    status: "status",
    hersIndex: "hers_index",
    narrative: "narrative",
    pdfPath: "pdf_path",
    complianceStandard: "compliance_standard",
    templateId: "template_id",
    generatedAt: "generated_at",
    deliveredAt: "delivered_at",
    recipientEmail: "recipient_email",
    recommendations: "recommendations",
  };

  const setClauses: string[] = [];
  const values: unknown[] = [];

  for (const [key, val] of Object.entries(body)) {
    if (fieldMap[key] !== undefined) {
      values.push(typeof val === "object" && val !== null ? JSON.stringify(val) : val);
      setClauses.push(`${fieldMap[key]} = $${values.length}`);
    }
  }

  if (setClauses.length === 0) {
    return NextResponse.json({ error: "No updatable fields" }, { status: 400 });
  }

  values.push(id);

  try {
    const row = await queryOne<DbRow>(
      `UPDATE reports SET ${setClauses.join(", ")} WHERE id = $${values.length} RETURNING *`,
      values,
    );
    if (!row) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    return NextResponse.json({ report: rowToReport(row) });
  } catch (err) {
    console.error("PUT /api/reports/[id] error:", err);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}
