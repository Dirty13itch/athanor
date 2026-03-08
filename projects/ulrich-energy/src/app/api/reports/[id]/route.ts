import { NextResponse } from "next/server";
import type { Report } from "@/types/report";

const mockReport: Report = {
  id: "rpt-001",
  inspectionId: "insp-002",
  hersIndex: 52,
  narrative: "This home demonstrates good overall energy performance with a HERS Index of 52, meaning it is 48% more energy efficient than the reference home. The blower door test result of 1,850 CFM50 (3.2 ACH50) indicates adequate air sealing. Duct leakage of 32 CFM25 to outside is well within acceptable limits.",
  pdfPath: null,
  complianceStandard: "minnesota_energy_code",
  templateId: "tpl-standard",
  status: "generated",
  generatedAt: "2026-03-05T16:00:00Z",
  deliveredAt: null,
  recipientEmail: null,
  recommendations: [
    {
      id: "rec-1",
      category: "Air Sealing",
      description: "Seal rim joist area with spray foam for improved envelope performance",
      estimatedCost: "$400-600",
      estimatedSavings: "$120/year",
      priority: "high",
    },
    {
      id: "rec-2",
      category: "Insulation",
      description: "Add R-10 rigid foam to basement walls",
      estimatedCost: "$1,200-1,800",
      estimatedSavings: "$180/year",
      priority: "medium",
    },
  ],
};

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return NextResponse.json({ report: { ...mockReport, id } });
}

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await request.json();
  return NextResponse.json({ report: { ...mockReport, id, ...body } });
}
