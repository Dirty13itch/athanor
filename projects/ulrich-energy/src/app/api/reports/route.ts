import { NextResponse } from "next/server";
import type { ReportListItem, GenerateReportRequest } from "@/types/report";

const mockReports: ReportListItem[] = [
  {
    id: "rpt-001",
    inspectionId: "insp-002",
    address: "5678 Elm Ave, Plymouth, MN 55447",
    hersIndex: 52,
    status: "generated",
    generatedAt: "2026-03-05T16:00:00Z",
  },
  {
    id: "rpt-002",
    inspectionId: "insp-003",
    address: "910 Birch Lane, Eden Prairie, MN 55344",
    hersIndex: 48,
    status: "delivered",
    generatedAt: "2026-03-01T12:00:00Z",
  },
];

export async function GET() {
  return NextResponse.json({ reports: mockReports });
}

export async function POST(request: Request) {
  const body = (await request.json()) as GenerateReportRequest;
  const newReport: ReportListItem = {
    id: `rpt-${Date.now()}`,
    inspectionId: body.inspectionId,
    address: "Pending address lookup",
    hersIndex: null,
    status: "draft",
    generatedAt: null,
  };
  return NextResponse.json({ report: newReport }, { status: 201 });
}
