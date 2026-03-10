import type { Client } from "@/types";
import type { CreateInspectionRequest, Inspection, InspectionListItem } from "@/types/inspection";
import type { CreateProjectRequest, Project } from "@/types/project";
import type { GenerateReportRequest, Report, ReportListItem } from "@/types/report";

type AnalyticsPayload = {
  inspections_by_status: Record<string, number>;
  total_inspections: number;
  avg_hers_index: number | null;
  avg_hers_by_builder: Array<{ builder: string; avg_hers: number; count: number }>;
  blower_door: {
    total_tests: number;
    fail_rate: number;
    avg_cfm50: number | null;
    avg_ach50: number | null;
  };
  duct_leakage: {
    avg_cfm25_total: number | null;
  };
  revenue: {
    rate_per_inspection: number;
    completed_count: number;
    estimated_this_month: number;
  };
};

type FixtureStore = {
  clients: Client[];
  projects: Project[];
  inspections: Inspection[];
  reports: Report[];
};

const STORE_KEY = "__ATHANOR_ULRICH_FIXTURE_STORE__";

function getStore(): FixtureStore {
  const target = globalThis as Record<string, unknown>;
  if (!(STORE_KEY in target)) {
    target[STORE_KEY] = createInitialStore();
  }
  return target[STORE_KEY] as FixtureStore;
}

function createInitialStore(): FixtureStore {
  const clients: Client[] = [
    {
      id: "client-lennar",
      name: "Lennar Homes",
      company: "Lennar",
      email: "ops@lennar.example",
      phone: "555-0101",
      created_at: "2026-03-01T09:00:00.000Z",
    },
    {
      id: "client-pulte",
      name: "Pulte Homes",
      company: "Pulte",
      email: "pm@pulte.example",
      phone: "555-0102",
      created_at: "2026-03-02T09:00:00.000Z",
    },
  ];

  const projects: Project[] = [
    {
      id: "proj-001",
      name: "Oak Street New Construction",
      clientId: "client-lennar",
      client: {
        id: "client-lennar",
        name: "Lennar Homes",
        company: "Lennar",
        email: "ops@lennar.example",
        phone: "555-0101",
        createdAt: "2026-03-01T09:00:00.000Z",
      },
      address: { street: "1234 Oak Street", city: "Maple Grove", state: "MN", zip: "55369" },
      propertyType: "single_family",
      builderName: "Lennar Homes",
      status: "active",
      inspectionCount: 1,
      createdAt: "2026-03-01T09:00:00.000Z",
      updatedAt: "2026-03-09T09:00:00.000Z",
    },
    {
      id: "proj-002",
      name: "Elm Ave Townhome Phase 2",
      clientId: "client-pulte",
      client: {
        id: "client-pulte",
        name: "Pulte Homes",
        company: "Pulte",
        email: "pm@pulte.example",
        phone: "555-0102",
        createdAt: "2026-03-02T09:00:00.000Z",
      },
      address: { street: "5678 Elm Ave", city: "Plymouth", state: "MN", zip: "55446" },
      propertyType: "townhome",
      builderName: "Pulte Homes",
      status: "active",
      inspectionCount: 2,
      createdAt: "2026-03-02T09:00:00.000Z",
      updatedAt: "2026-03-09T11:00:00.000Z",
    },
  ];

  const inspections: Inspection[] = [
    {
      id: "insp-001",
      projectId: "proj-001",
      address: "1234 Oak Street, Maple Grove",
      builder: "Lennar Homes",
      inspector: "Shaun",
      status: "draft",
      createdAt: "2026-03-07T15:00:00.000Z",
      updatedAt: "2026-03-07T15:00:00.000Z",
      buildingEnvelope: {
        orientation: "south",
        sqft: 2860,
        ceilingHeight: 9,
        stories: 2,
        foundationType: "basement",
      },
      insulation: [],
      windows: [],
      hvacSystems: [],
      photos: [],
    },
    {
      id: "insp-002",
      projectId: "proj-002",
      address: "5678 Elm Ave, Plymouth",
      builder: "Pulte Homes",
      inspector: "Shaun",
      status: "reported",
      createdAt: "2026-03-05T13:30:00.000Z",
      updatedAt: "2026-03-05T16:00:00.000Z",
      buildingEnvelope: {
        orientation: "east",
        sqft: 2140,
        ceilingHeight: 9,
        stories: 2,
        foundationType: "slab",
      },
      blowerDoor: {
        cfm50: 1260,
        ach50: 2.6,
        enclosureArea: 4520,
        passFail: true,
      },
      ductLeakage: {
        cfm25Total: 42,
        cfm25Outside: 18,
        testMethod: "both",
      },
      insulation: [],
      windows: [],
      hvacSystems: [],
      photos: [],
    },
    {
      id: "insp-003",
      projectId: "proj-002",
      address: "910 Birch Lane, Eden Prairie",
      builder: "Pulte Homes",
      inspector: "Shaun",
      status: "delivered",
      createdAt: "2026-03-01T11:15:00.000Z",
      updatedAt: "2026-03-01T18:00:00.000Z",
      buildingEnvelope: {
        orientation: "west",
        sqft: 2410,
        ceilingHeight: 9,
        stories: 2,
        foundationType: "basement",
      },
      blowerDoor: {
        cfm50: 1410,
        ach50: 2.9,
        enclosureArea: 4880,
        passFail: true,
      },
      ductLeakage: {
        cfm25Total: 57,
        cfm25Outside: 24,
        testMethod: "total_leakage",
      },
      insulation: [],
      windows: [],
      hvacSystems: [],
      photos: [],
    },
  ];

  const reports: Report[] = [
    {
      id: "rpt-001",
      inspectionId: "insp-002",
      hersIndex: 52,
      narrative:
        "Fixture narrative: the envelope performance is within expected range, blower-door leakage passed, and the most cost-effective improvement is reducing duct leakage outside the conditioned envelope.",
      pdfPath: null,
      complianceStandard: "minnesota_energy_code",
      templateId: "standard",
      status: "generated",
      generatedAt: "2026-03-05T16:10:00.000Z",
      deliveredAt: null,
      recipientEmail: "pm@pulte.example",
      recommendations: [
        {
          id: "rec-001",
          category: "ducts",
          description: "Seal the return trunk joints in the attic chase.",
          estimatedCost: "$300-500",
          estimatedSavings: "Moderate",
          priority: "high",
        },
      ],
    },
    {
      id: "rpt-002",
      inspectionId: "insp-003",
      hersIndex: 48,
      narrative:
        "Fixture narrative: the home performs above code baseline, with strongest gains likely coming from targeted envelope sealing and final commissioning of supply balancing.",
      pdfPath: null,
      complianceStandard: "minnesota_energy_code",
      templateId: "standard",
      status: "delivered",
      generatedAt: "2026-03-01T18:10:00.000Z",
      deliveredAt: "2026-03-02T09:30:00.000Z",
      recipientEmail: "pm@pulte.example",
      recommendations: [
        {
          id: "rec-002",
          category: "envelope",
          description: "Air seal the rim joist at the north wall.",
          estimatedCost: "$250-400",
          estimatedSavings: "Low-Moderate",
          priority: "medium",
        },
      ],
    },
  ];

  return { clients, projects, inspections, reports };
}

function toClientProject(client: Client | undefined) {
  if (!client) {
    return undefined;
  }

  return {
    id: client.id,
    name: client.name,
    company: client.company ?? undefined,
    email: client.email ?? "",
    phone: client.phone ?? undefined,
    createdAt: client.created_at,
  };
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function nextId(prefix: string): string {
  return `${prefix}-${crypto.randomUUID().slice(0, 8)}`;
}

export function listFixtureClients(): Client[] {
  return clone(getStore().clients);
}

export function createFixtureClient(input: Pick<Client, "name" | "company" | "email" | "phone">): Client {
  const store = getStore();
  const client: Client = {
    id: nextId("client"),
    name: input.name,
    company: input.company ?? null,
    email: input.email ?? null,
    phone: input.phone ?? null,
    created_at: new Date().toISOString(),
  };
  store.clients.unshift(client);
  return clone(client);
}

export function listFixtureProjects(): Project[] {
  const store = getStore();
  return clone(
    store.projects.map((project) => ({
      ...project,
      client: toClientProject(store.clients.find((client) => client.id === project.clientId)),
      inspectionCount: store.inspections.filter((inspection) => inspection.projectId === project.id).length,
    })),
  );
}

export function createFixtureProject(input: CreateProjectRequest): Project {
  const store = getStore();
  let clientId = input.clientId;

  if (!clientId) {
    const client = createFixtureClient({
      name: input.clientName ?? "New Client",
      company: null,
      email: input.clientEmail ?? null,
      phone: null,
    });
    clientId = client.id;
  }

  const project: Project = {
    id: nextId("proj"),
    name: input.name,
    clientId,
    client: toClientProject(store.clients.find((client) => client.id === clientId)),
    address: input.address,
    propertyType: input.propertyType,
    builderName: input.builderName,
    status: "active",
    inspectionCount: 0,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  store.projects.unshift(project);
  return clone(project);
}

function toInspectionListItem(inspection: Inspection): InspectionListItem {
  const report = getStore().reports.find((entry) => entry.inspectionId === inspection.id);
  return {
    id: inspection.id,
    address: inspection.address,
    builder: inspection.builder,
    inspector: inspection.inspector,
    status: inspection.status,
    createdAt: inspection.createdAt,
    ...(report?.hersIndex !== null && report?.hersIndex !== undefined ? { hersIndex: report.hersIndex } : {}),
  };
}

export function listFixtureInspections(filters?: { status?: string | null; builder?: string | null; projectId?: string | null }): InspectionListItem[] {
  const store = getStore();
  let inspections = [...store.inspections];
  if (filters?.status) {
    inspections = inspections.filter((inspection) => inspection.status === filters.status);
  }
  if (filters?.builder) {
    const builderNeedle = filters.builder.toLowerCase();
    inspections = inspections.filter((inspection) => inspection.builder.toLowerCase().includes(builderNeedle));
  }
  if (filters?.projectId) {
    inspections = inspections.filter((inspection) => inspection.projectId === filters.projectId);
  }
  return clone(inspections.map(toInspectionListItem));
}

export function getFixtureInspection(id: string): Inspection | null {
  const inspection = getStore().inspections.find((entry) => entry.id === id);
  return inspection ? clone(inspection) : null;
}

export function createFixtureInspection(input: CreateInspectionRequest): Inspection {
  const store = getStore();
  const inspection: Inspection = {
    id: nextId("insp"),
    projectId: input.projectId ?? "",
    address: input.address,
    builder: input.builder,
    inspector: input.inspector ?? "Shaun",
    status: "draft",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    insulation: [],
    windows: [],
    hvacSystems: [],
    photos: [],
  };
  store.inspections.unshift(inspection);
  return clone(inspection);
}

export function updateFixtureInspection(id: string, updates: Partial<Inspection>): Inspection | null {
  const store = getStore();
  const inspection = store.inspections.find((entry) => entry.id === id);
  if (!inspection) {
    return null;
  }
  Object.assign(inspection, updates, { updatedAt: new Date().toISOString() });
  return clone(inspection);
}

export function deleteFixtureInspection(id: string): boolean {
  const store = getStore();
  const before = store.inspections.length;
  store.inspections = store.inspections.filter((entry) => entry.id !== id);
  store.reports = store.reports.filter((entry) => entry.inspectionId !== id);
  return store.inspections.length !== before;
}

export function listFixtureReports(): ReportListItem[] {
  const store = getStore();
  return clone(
    store.reports.map((report) => ({
      id: report.id,
      inspectionId: report.inspectionId,
      address: store.inspections.find((inspection) => inspection.id === report.inspectionId)?.address ?? "Unknown address",
      hersIndex: report.hersIndex,
      status: report.status,
      generatedAt: report.generatedAt,
    })),
  );
}

export function getFixtureReport(id: string): Report | null {
  const report = getStore().reports.find((entry) => entry.id === id);
  return report ? clone(report) : null;
}

export function createFixtureReportDraft(input: GenerateReportRequest): Report | null {
  const store = getStore();
  const inspection = store.inspections.find((entry) => entry.id === input.inspectionId);
  if (!inspection) {
    return null;
  }
  const report: Report = {
    id: nextId("rpt"),
    inspectionId: input.inspectionId,
    hersIndex: null,
    narrative: "",
    pdfPath: null,
    complianceStandard: input.complianceStandard ?? "minnesota_energy_code",
    templateId: input.templateId ?? "standard",
    status: "generated",
    generatedAt: new Date().toISOString(),
    deliveredAt: null,
    recipientEmail: null,
    recommendations: [],
  };
  store.reports.unshift(report);
  return clone(report);
}

export function generateFixtureReport(input: GenerateReportRequest & { reportId?: string }): Report | null {
  const store = getStore();
  const inspection = store.inspections.find((entry) => entry.id === input.inspectionId);
  if (!inspection) {
    return null;
  }

  const report =
    (input.reportId
      ? store.reports.find((entry) => entry.id === input.reportId)
      : store.reports.find((entry) => entry.inspectionId === input.inspectionId)) ??
    {
      id: nextId("rpt"),
      inspectionId: input.inspectionId,
      hersIndex: null,
      narrative: "",
      pdfPath: null,
      complianceStandard: input.complianceStandard ?? "minnesota_energy_code",
      templateId: input.templateId ?? "standard",
      status: "generated" as const,
      generatedAt: null,
      deliveredAt: null,
      recipientEmail: null,
      recommendations: [],
    };

  report.hersIndex = inspection.id === "insp-002" ? 52 : inspection.id === "insp-003" ? 48 : 56;
  report.narrative = `Fixture narrative for ${inspection.address}: blower-door and duct leakage results were reviewed, the envelope is broadly code-compliant, and the next recommendation is to tighten the remaining leakage paths before final delivery.`;
  report.generatedAt = new Date().toISOString();
  report.status = "generated";
  report.complianceStandard = input.complianceStandard ?? report.complianceStandard;
  report.templateId = input.templateId ?? report.templateId;
  report.recommendations = [
    {
      id: nextId("rec"),
      category: "air-sealing",
      description: "Seal accessible leakage points at the attic hatch and top plates.",
      estimatedCost: "$350-600",
      estimatedSavings: "Moderate",
      priority: "high",
    },
  ];

  if (!store.reports.some((entry) => entry.id === report.id)) {
    store.reports.unshift(report);
  }

  return clone(report);
}

export function updateFixtureReport(id: string, updates: Partial<Report>): Report | null {
  const store = getStore();
  const report = store.reports.find((entry) => entry.id === id);
  if (!report) {
    return null;
  }
  Object.assign(report, updates);
  return clone(report);
}

export function getFixtureAnalytics(): AnalyticsPayload {
  const reports = listFixtureReports();
  const inspections = listFixtureInspections();
  const totalInspections = inspections.length;
  const counts = inspections.reduce<Record<string, number>>((acc, inspection) => {
    acc[inspection.status] = (acc[inspection.status] ?? 0) + 1;
    return acc;
  }, {});

  const hersValues = reports.map((report) => report.hersIndex).filter((value): value is number => value !== null);
  const avgHers = hersValues.length > 0
    ? hersValues.reduce((sum, value) => sum + value, 0) / hersValues.length
    : null;

  const builders = new Map<string, number[]>();
  for (const inspection of inspections) {
    if (inspection.hersIndex === undefined) {
      continue;
    }
    const bucket = builders.get(inspection.builder) ?? [];
    bucket.push(inspection.hersIndex);
    builders.set(inspection.builder, bucket);
  }

  const avgByBuilder = Array.from(builders.entries()).map(([builder, values]) => ({
    builder,
    avg_hers: values.reduce((sum, value) => sum + value, 0) / values.length,
    count: values.length,
  }));

  return {
    inspections_by_status: counts,
    total_inspections: totalInspections,
    avg_hers_index: avgHers,
    avg_hers_by_builder: avgByBuilder,
    blower_door: {
      total_tests: 2,
      fail_rate: 0,
      avg_cfm50: 1335,
      avg_ach50: 2.75,
    },
    duct_leakage: {
      avg_cfm25_total: 49.5,
    },
    revenue: {
      rate_per_inspection: 350,
      completed_count: (counts.reported ?? 0) + (counts.delivered ?? 0),
      estimated_this_month: ((counts.reported ?? 0) + (counts.delivered ?? 0)) * 350,
    },
  };
}
