import { NextResponse } from "next/server";
import { queryOne, withTransaction } from "@/lib/db";
import { ULRICH_FIXTURE_MODE } from "@/lib/fixture-mode";
import { deleteFixtureInspection, getFixtureInspection, updateFixtureInspection } from "@/lib/fixtures";
import type { Inspection, FoundationType, DuctTestMethod } from "@/types/inspection";

type DbRow = {
  id: string;
  project_id: string | null;
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
  photos: unknown[];
  created_at: string;
  updated_at: string;
};

function rowToInspection(r: DbRow): Inspection {
  return {
    id: r.id,
    projectId: r.project_id ?? "",
    address: r.address,
    builder: r.builder,
    inspector: r.inspector,
    status: r.status as Inspection["status"],
    createdAt: r.created_at,
    updatedAt: r.updated_at,
    ...(r.sqft !== null
      ? {
          buildingEnvelope: {
            orientation: r.orientation ?? "",
            sqft: r.sqft,
            ceilingHeight: r.ceiling_height ?? 9,
            stories: r.stories ?? 1,
            foundationType: (r.foundation_type ?? "slab") as FoundationType,
          },
        }
      : {}),
    ...(r.blower_cfm50 !== null
      ? {
          blowerDoor: {
            cfm50: r.blower_cfm50,
            ach50: r.blower_ach50 ?? 0,
            enclosureArea: r.blower_enclosure_area ?? 0,
            passFail: r.blower_pass_fail ?? false,
          },
        }
      : {}),
    ...(r.duct_cfm25_total !== null
      ? {
          ductLeakage: {
            cfm25Total: r.duct_cfm25_total,
            cfm25Outside: r.duct_cfm25_outside ?? 0,
            testMethod: (r.duct_test_method ?? "total_leakage") as DuctTestMethod,
          },
        }
      : {}),
    insulation: (r.insulation ?? []) as Inspection["insulation"],
    windows: (r.windows ?? []) as Inspection["windows"],
    hvacSystems: (r.hvac_systems ?? []) as Inspection["hvacSystems"],
    photos: (r.photos ?? []) as Inspection["photos"],
  };
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  if (ULRICH_FIXTURE_MODE) {
    const inspection = getFixtureInspection(id);
    if (!inspection) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    return NextResponse.json({ inspection });
  }
  try {
    const row = await queryOne<DbRow>(
      `SELECT * FROM inspections WHERE id = $1`,
      [id],
    );
    if (!row) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    return NextResponse.json({ inspection: rowToInspection(row) });
  } catch (err) {
    console.error("GET /api/inspections/[id] error:", err);
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
    const inspection = updateFixtureInspection(id, body as Partial<Inspection>);
    if (!inspection) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    return NextResponse.json({ inspection });
  }

  // Map TypeScript field names to DB column names for the fields we support updating
  const fieldMap: Record<string, string> = {
    status: "status",
    hersIndex: "hers_index",
    // Building envelope
    "buildingEnvelope.orientation": "orientation",
    "buildingEnvelope.sqft": "sqft",
    "buildingEnvelope.ceilingHeight": "ceiling_height",
    "buildingEnvelope.stories": "stories",
    "buildingEnvelope.foundationType": "foundation_type",
    // Blower door
    "blowerDoor.cfm50": "blower_cfm50",
    "blowerDoor.ach50": "blower_ach50",
    "blowerDoor.enclosureArea": "blower_enclosure_area",
    "blowerDoor.passFail": "blower_pass_fail",
    // Duct leakage
    "ductLeakage.cfm25Total": "duct_cfm25_total",
    "ductLeakage.cfm25Outside": "duct_cfm25_outside",
    "ductLeakage.testMethod": "duct_test_method",
    // JSONB arrays
    insulation: "insulation",
    windows: "windows",
    hvacSystems: "hvac_systems",
    photos: "photos",
  };

  const setClauses: string[] = [];
  const values: unknown[] = [];

  // Flatten body fields
  function flattenAndMap(obj: Record<string, unknown>, prefix = "") {
    for (const [key, val] of Object.entries(obj)) {
      const path = prefix ? `${prefix}.${key}` : key;
      if (val !== null && typeof val === "object" && !Array.isArray(val) && !fieldMap[path]) {
        flattenAndMap(val as Record<string, unknown>, path);
      } else if (fieldMap[path] !== undefined) {
        values.push(typeof val === "object" ? JSON.stringify(val) : val);
        setClauses.push(`${fieldMap[path]} = $${values.length}`);
      }
    }
  }

  flattenAndMap(body);

  if (setClauses.length === 0) {
    return NextResponse.json({ error: "No updatable fields provided" }, { status: 400 });
  }

  values.push(new Date().toISOString());
  setClauses.push(`updated_at = $${values.length}`);
  values.push(id);

  try {
    const row = await queryOne<DbRow>(
      `UPDATE inspections SET ${setClauses.join(", ")} WHERE id = $${values.length} RETURNING *`,
      values,
    );
    if (!row) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    return NextResponse.json({ inspection: rowToInspection(row) });
  } catch (err) {
    console.error("PUT /api/inspections/[id] error:", err);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  if (ULRICH_FIXTURE_MODE) {
    if (!deleteFixtureInspection(id)) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    return NextResponse.json({ deleted: id });
  }
  try {
    await withTransaction(async (client) => {
      await client.query(`DELETE FROM reports WHERE inspection_id = $1`, [id]);
      await client.query(`DELETE FROM inspections WHERE id = $1`, [id]);
    });
    return NextResponse.json({ deleted: id });
  } catch (err) {
    console.error("DELETE /api/inspections/[id] error:", err);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}
