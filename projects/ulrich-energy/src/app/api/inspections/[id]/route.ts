import { NextResponse } from "next/server";
import type { Inspection } from "@/types/inspection";

const mockInspection: Inspection = {
  id: "insp-001",
  projectId: "proj-001",
  address: "1234 Oak Street, Maple Grove, MN 55369",
  builder: "Lennar Homes",
  inspector: "Shaun",
  status: "draft",
  createdAt: "2026-03-07T09:00:00Z",
  updatedAt: "2026-03-07T09:00:00Z",
  buildingEnvelope: {
    orientation: "south",
    sqft: 2400,
    ceilingHeight: 9,
    stories: 2,
    foundationType: "basement",
  },
  blowerDoor: {
    cfm50: 1850,
    ach50: 3.2,
    enclosureArea: 5800,
    passFail: true,
  },
  ductLeakage: {
    cfm25Total: 48,
    cfm25Outside: 32,
    testMethod: "both",
  },
  insulation: [
    {
      id: "ins-1",
      location: "attic",
      rValue: 49,
      type: "blown_cellulose",
      depth: 14,
      notes: "Even coverage throughout",
    },
    {
      id: "ins-2",
      location: "exterior_walls",
      rValue: 21,
      type: "fiberglass_batt",
      depth: 5.5,
    },
  ],
  windows: [
    {
      id: "win-1",
      location: "south",
      uFactor: 0.27,
      shgc: 0.25,
      frameType: "vinyl",
      count: 6,
      area: 18,
    },
  ],
  hvacSystems: [
    {
      id: "hvac-1",
      systemType: "furnace",
      model: "Carrier 59TP6",
      capacity: "80,000 BTU",
      efficiencyRating: "96 AFUE",
      ductLocation: "conditioned_space",
    },
    {
      id: "hvac-2",
      systemType: "ac",
      model: "Carrier 24ACC6",
      capacity: "3 ton",
      efficiencyRating: "16 SEER",
      ductLocation: "conditioned_space",
    },
  ],
  photos: [],
};

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return NextResponse.json({ inspection: { ...mockInspection, id } });
}

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await request.json();
  return NextResponse.json({ inspection: { ...mockInspection, id, ...body } });
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return NextResponse.json({ deleted: id });
}
