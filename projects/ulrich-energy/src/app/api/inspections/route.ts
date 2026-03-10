import { NextResponse } from "next/server";
import { query, queryOne } from "@/lib/db";
import { ULRICH_FIXTURE_MODE } from "@/lib/fixture-mode";
import { createFixtureInspection, listFixtureInspections } from "@/lib/fixtures";
import type { InspectionListItem, CreateInspectionRequest } from "@/types/inspection";

type DbRow = {
  id: string;
  address: string;
  builder: string;
  inspector: string;
  status: string;
  created_at: string;
  hers_index: number | null;
};

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const status = searchParams.get("status");
  const builder = searchParams.get("builder");
  const projectId = searchParams.get("projectId");

  if (ULRICH_FIXTURE_MODE) {
    return NextResponse.json({
      inspections: listFixtureInspections({ status, builder, projectId }),
    });
  }

  let sql = `SELECT id, address, builder, inspector, status, created_at, hers_index
             FROM inspections`;
  const params: string[] = [];
  const conditions: string[] = [];

  if (status) {
    params.push(status);
    conditions.push(`status = $${params.length}`);
  }
  if (builder) {
    params.push(`%${builder}%`);
    conditions.push(`builder ILIKE $${params.length}`);
  }
  if (conditions.length > 0) {
    sql += ` WHERE ${conditions.join(" AND ")}`;
  }
  sql += ` ORDER BY created_at DESC LIMIT 100`;

  try {
    const rows = await query<DbRow>(sql, params);
    const inspections: InspectionListItem[] = rows.map((r) => ({
      id: r.id,
      address: r.address,
      builder: r.builder,
      inspector: r.inspector,
      status: r.status as InspectionListItem["status"],
      createdAt: r.created_at,
      ...(r.hers_index !== null ? { hersIndex: r.hers_index } : {}),
    }));
    return NextResponse.json({ inspections });
  } catch (err) {
    console.error("GET /api/inspections error:", err);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  const body = (await request.json()) as CreateInspectionRequest;

  if (!body.address || !body.builder) {
    return NextResponse.json(
      { error: "address and builder are required" },
      { status: 400 },
    );
  }

  if (ULRICH_FIXTURE_MODE) {
    return NextResponse.json(
      { inspection: createFixtureInspection(body) },
      { status: 201 },
    );
  }

  try {
    const row = await queryOne<DbRow>(
      `INSERT INTO inspections (project_id, address, builder, inspector)
       VALUES ($1, $2, $3, $4)
       RETURNING id, address, builder, inspector, status, created_at, hers_index`,
      [body.projectId ?? null, body.address, body.builder, body.inspector ?? "Shaun"],
    );

    if (!row) throw new Error("Insert returned no row");

    const inspection: InspectionListItem = {
      id: row.id,
      address: row.address,
      builder: row.builder,
      inspector: row.inspector,
      status: "draft",
      createdAt: row.created_at,
    };
    return NextResponse.json({ inspection }, { status: 201 });
  } catch (err) {
    console.error("POST /api/inspections error:", err);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}
