import { Pool, type PoolClient } from "pg";

const DATABASE_URL =
  process.env.DATABASE_URL ||
  "postgresql://ulrich:athanor2026@192.168.1.203:5432/ulrich_energy";

// Module-level pool — reused across requests (Next.js keeps module in memory)
let pool: Pool | null = null;

function getPool(): Pool {
  if (!pool) {
    pool = new Pool({
      connectionString: DATABASE_URL,
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
