import { NextRequest, NextResponse } from "next/server";
import type { Client, ClientCreateInput, ApiResult } from "@/types";

// GET /api/clients — List all clients (builders, homeowners)
export async function GET(_request: NextRequest) {
  // TODO: Query PostgreSQL clients table
  const clients: Client[] = [];

  return NextResponse.json({ data: clients } satisfies ApiResult<Client[]>);
}

// POST /api/clients — Create new client
export async function POST(request: NextRequest) {
  try {
    const body: ClientCreateInput = await request.json();

    if (!body.name) {
      return NextResponse.json(
        { error: "Client name is required" },
        { status: 400 }
      );
    }

    // TODO: Insert into PostgreSQL
    const client: Client = {
      id: crypto.randomUUID(),
      name: body.name,
      company: body.company ?? null,
      email: body.email ?? null,
      phone: body.phone ?? null,
      created_at: new Date().toISOString(),
    };

    return NextResponse.json({ data: client } satisfies ApiResult<Client>, {
      status: 201,
    });
  } catch {
    return NextResponse.json(
      { error: "Failed to create client" },
      { status: 500 }
    );
  }
}
