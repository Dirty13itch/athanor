import { NextResponse } from "next/server";
import type { InspectionListItem, CreateInspectionRequest } from "@/types/inspection";

const mockInspections: InspectionListItem[] = [
  {
    id: "insp-001",
    address: "1234 Oak Street, Maple Grove, MN 55369",
    builder: "Lennar Homes",
    inspector: "Shaun",
    status: "draft",
    createdAt: "2026-03-07T09:00:00Z",
  },
  {
    id: "insp-002",
    address: "5678 Elm Ave, Plymouth, MN 55447",
    builder: "Pulte Homes",
    inspector: "Shaun",
    status: "reported",
    createdAt: "2026-03-05T14:30:00Z",
    hersIndex: 52,
  },
  {
    id: "insp-003",
    address: "910 Birch Lane, Eden Prairie, MN 55344",
    builder: "David Weekley",
    inspector: "Shaun",
    status: "delivered",
    createdAt: "2026-03-01T10:00:00Z",
    hersIndex: 48,
  },
];

export async function GET() {
  return NextResponse.json({ inspections: mockInspections });
}

export async function POST(request: Request) {
  const body = (await request.json()) as CreateInspectionRequest;
  const newInspection: InspectionListItem = {
    id: `insp-${Date.now()}`,
    address: body.address,
    builder: body.builder,
    inspector: body.inspector ?? "Shaun",
    status: "draft",
    createdAt: new Date().toISOString(),
  };
  return NextResponse.json({ inspection: newInspection }, { status: 201 });
}
