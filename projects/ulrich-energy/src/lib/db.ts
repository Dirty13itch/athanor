import { Pool, type PoolClient } from "pg";

function getDatabaseUrl(): string {
  const databaseUrl =
    process.env.DATABASE_URL ||
    process.env.ATHANOR_ULRICH_DATABASE_URL ||
    process.env.ULRICH_DATABASE_URL;

  if (!databaseUrl) {
    throw new Error(
      "DATABASE_URL or ATHANOR_ULRICH_DATABASE_URL is required for Ulrich Energy.",
    );
  }

  return databaseUrl;
}

// Module-level pool reused across requests.
let pool: Pool | null = null;

function getPool(): Pool {
  if (!pool) {
    pool = new Pool({
      connectionString: getDatabaseUrl(),
      max: 10,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
    });
    pool.on("error", (err) => {
      console.error("PostgreSQL pool error:", err);
    });
  }
  return pool;
}

export async function query<T = Record<string, unknown>>(
  text: string,
  values?: unknown[],
): Promise<T[]> {
  const client = getPool();
  const result = await client.query(text, values);
  return result.rows as T[];
}

export async function queryOne<T = Record<string, unknown>>(
  text: string,
  values?: unknown[],
): Promise<T | null> {
  const rows = await query<T>(text, values);
  return rows[0] ?? null;
}

export async function withTransaction<T>(
  fn: (client: PoolClient) => Promise<T>,
): Promise<T> {
  const client = await getPool().connect();
  try {
    await client.query("BEGIN");
    const result = await fn(client);
    await client.query("COMMIT");
    return result;
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}
