import { NextResponse } from "next/server";
import { query, queryOne } from "@/lib/db";
import { ULRICH_FIXTURE_MODE } from "@/lib/fixture-mode";
import { createFixtureProject, listFixtureProjects } from "@/lib/fixtures";
import type { Project, CreateProjectRequest } from "@/types/project";

type DbRow = {
  id: string;
  name: string;
  client_id: string;
  client_name: string | null;
  client_company: string | null;
  client_email: string | null;
  client_phone: string | null;
  client_created_at: string | null;
  address_street: string;
  address_city: string;
  address_state: string;
  address_zip: string;
  property_type: string;
  builder_name: string;
  status: string;
  inspection_count: string;
  created_at: string;
  updated_at: string;
};

function rowToProject(r: DbRow): Project {
  return {
    id: r.id,
    name: r.name,
    clientId: r.client_id,
    client: r.client_name
      ? {
          id: r.client_id,
          name: r.client_name,
          company: r.client_company ?? undefined,
          email: r.client_email ?? "",
          phone: r.client_phone ?? undefined,
          createdAt: r.client_created_at ?? "",
        }
      : undefined,
    address: {
      street: r.address_street,
      city: r.address_city,
      state: r.address_state,
      zip: r.address_zip,
    },
    propertyType: r.property_type as Project["propertyType"],
    builderName: r.builder_name,
    status: r.status as Project["status"],
    inspectionCount: parseInt(r.inspection_count, 10),
    createdAt: r.created_at,
    updatedAt: r.updated_at,
  };
}

export async function GET() {
  if (ULRICH_FIXTURE_MODE) {
    return NextResponse.json({ projects: listFixtureProjects() });
  }
  try {
    const rows = await query<DbRow>(`
      SELECT p.*,
             c.name AS client_name, c.company AS client_company,
             c.email AS client_email, c.phone AS client_phone,
             c.created_at AS client_created_at,
             COUNT(i.id)::text AS inspection_count
      FROM projects p
      LEFT JOIN clients c ON p.client_id = c.id
      LEFT JOIN inspections i ON i.project_id = p.id
      GROUP BY p.id, c.id
      ORDER BY p.updated_at DESC
    `);
    return NextResponse.json({ projects: rows.map(rowToProject) });
  } catch (err) {
    console.error("GET /api/projects error:", err);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  const body = (await request.json()) as CreateProjectRequest;

  if (!body.name || !body.address || !body.propertyType || !body.builderName) {
    return NextResponse.json(
      { error: "name, address, propertyType, and builderName are required" },
      { status: 400 },
    );
  }

  if (ULRICH_FIXTURE_MODE) {
    return NextResponse.json({ project: createFixtureProject(body) }, { status: 201 });
  }

  try {
    let clientId = body.clientId;

    // Create client inline if clientId not provided
    if (!clientId && body.clientName) {
      const clientRow = await queryOne<{ id: string }>(
        `INSERT INTO clients (name, email) VALUES ($1, $2) RETURNING id`,
        [body.clientName, body.clientEmail ?? null],
      );
      clientId = clientRow?.id;
    }

    if (!clientId) {
      return NextResponse.json(
        { error: "clientId or clientName is required" },
        { status: 400 },
      );
    }

    const row = await queryOne<DbRow>(`
      INSERT INTO projects
        (name, client_id, address_street, address_city, address_state, address_zip,
         property_type, builder_name)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
      RETURNING *,
        0::text AS inspection_count,
        NULL::text AS client_name,
        NULL::text AS client_company,
        NULL::text AS client_email,
        NULL::text AS client_phone,
        NULL::text AS client_created_at
    `, [
      body.name, clientId,
      body.address.street, body.address.city, body.address.state, body.address.zip,
      body.propertyType, body.builderName,
    ]);

    if (!row) throw new Error("Insert returned no row");

    return NextResponse.json({ project: rowToProject(row) }, { status: 201 });
  } catch (err) {
    console.error("POST /api/projects error:", err);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}
