import { NextRequest, NextResponse } from "next/server";
import { generateReportNarrative } from "@/lib/litellm";
import type { Report, ApiResult } from "@/types";

// POST /api/reports/generate — Generate report via LLM for a given job
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { job_id } = body as { job_id: string };

    if (!job_id) {
      return NextResponse.json(
        { error: "job_id is required" },
        { status: 400 }
      );
    }

    // TODO: Fetch full inspection data from PostgreSQL
    // TODO: Validate all required fields are present before generation

    // Placeholder inspection data — replace with DB query
    const inspectionData = { job_id, placeholder: true };

    const narrative = await generateReportNarrative(inspectionData);

    // TODO: Generate PDF from narrative
    // TODO: Store report in PostgreSQL

    const report: Report = {
      job_id,
      hers_index: null, // Calculated separately
      narrative,
      pdf_path: null, // Set after PDF generation
      generated_at: new Date().toISOString(),
      status: "complete",
    };

    return NextResponse.json({ data: report } satisfies ApiResult<Report>, {
      status: 201,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json(
      { error: "Report generation failed", details: message },
      { status: 500 }
    );
  }
}
