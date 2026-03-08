import { NextResponse } from "next/server";
import type { Project, CreateProjectRequest } from "@/types/project";

const mockProjects: Project[] = [
  {
    id: "proj-001",
    name: "Oak Street New Construction",
    clientId: "client-001",
    client: {
      id: "client-001",
      name: "John Builder",
      company: "Lennar Homes",
      email: "john@lennarhomes.example.com",
      phone: "612-555-0100",
      createdAt: "2026-01-15T10:00:00Z",
    },
    address: {
      street: "1234 Oak Street",
      city: "Maple Grove",
      state: "MN",
      zip: "55369",
    },
    propertyType: "single_family",
    builderName: "Lennar Homes",
    status: "active",
    inspectionCount: 1,
    createdAt: "2026-02-20T10:00:00Z",
    updatedAt: "2026-03-07T09:00:00Z",
  },
  {
    id: "proj-002",
    name: "Elm Ave Townhome Phase 2",
    clientId: "client-002",
    client: {
      id: "client-002",
      name: "Sarah Manager",
      company: "Pulte Homes",
      email: "sarah@pultehomes.example.com",
      createdAt: "2026-01-10T08:00:00Z",
    },
    address: {
      street: "5678 Elm Ave",
      city: "Plymouth",
      state: "MN",
      zip: "55447",
    },
    propertyType: "townhome",
    builderName: "Pulte Homes",
    status: "active",
    inspectionCount: 3,
    createdAt: "2026-01-20T10:00:00Z",
    updatedAt: "2026-03-05T14:30:00Z",
  },
];

export async function GET() {
  return NextResponse.json({ projects: mockProjects });
}

export async function POST(request: Request) {
  const body = (await request.json()) as CreateProjectRequest;
  const newProject: Project = {
    id: `proj-${Date.now()}`,
    name: body.name,
    clientId: body.clientId ?? `client-${Date.now()}`,
    address: body.address,
    propertyType: body.propertyType,
    builderName: body.builderName,
    status: "active",
    inspectionCount: 0,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  return NextResponse.json({ project: newProject }, { status: 201 });
}
