// Database client placeholder
// Will use pg (node-postgres) connecting to VAULT PostgreSQL
//
// Connection: postgresql://ulrich:PASSWORD@192.168.1.203:5432/ulrich_energy
//
// TODO: Install pg + @types/pg, create connection pool
// TODO: Add migration runner (drizzle-orm or raw SQL files)

export const DATABASE_URL =
  process.env.DATABASE_URL ||
  "postgresql://ulrich:changeme@192.168.1.203:5432/ulrich_energy";

// Placeholder — replace with actual pool when pg is installed
export function getDb() {
  throw new Error(
    "Database not configured. Install pg and set DATABASE_URL env var."
  );
}
