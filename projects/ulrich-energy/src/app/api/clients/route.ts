import { NextRequest, NextResponse } from "next/server";
import { query, queryOne } from "@/lib/db";
import type { Client, ClientCreateInput, ApiResult } from "@/types";

type DbRow = {
  id: string;
  name: string;
  company: string | null;
  email: string | null;
  phone: string | null;
  created_at: string;
};

export async function GET(_request: NextRequest) {
  try {
    const rows = await query<DbRow>(
      `SELECT id, name, company, email, phone, created_at FROM clients ORDER BY created_at DESC`,
    );
    const clients: Client[] = rows.map((r) => ({
      id: r.id,
      name: r.name,
      company: r.company,
      email: r.email,
      phone: r.phone,
      created_at: r.created_at,
    }));
    return NextResponse.json({ data: clients } satisfies ApiResult<Client[]>);
  } catch (err) {
    console.error("GET /api/clients error:", err);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body: ClientCreateInput = await request.json();

    if (!body.name) {
      return NextResponse.json(
        { error: "Client name is required" },
        { status: 400 },
      );
    }

    const row = await queryOne<DbRow>(
      `INSERT INTO clients (name, company, email, phone)
       VALUES ($1, $2, $3, $4)
       RETURNING id, name, company, email, phone, created_at`,
      [body.name, body.company ?? null, body.email ?? null, body.phone ?? null],
    );

    if (!row) throw new Error("Insert returned no row");

    const client: Client = {
      id: row.id,
      name: row.name,
      company: row.company,
      email: row.email,
      phone: row.phone,
      created_at: row.created_at,
    };

    return NextResponse.json({ data: client } satisfies ApiResult<Client>, {
      status: 201,
    });
  } catch (err) {
    console.error("POST /api/clients error:", err);
    return NextResponse.json(
      { error: "Failed to create client" },
      { status: 500 },
    );
  }
}
