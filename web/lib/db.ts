import { Pool } from "@neondatabase/serverless";

let _pool: Pool | null = null;

function getPool(): Pool {
  if (!_pool) {
    const connectionString = process.env.DATABASE_URL;
    if (!connectionString) {
      throw new Error("DATABASE_URL environment variable is not set");
    }
    // Cap per-instance connections so we don't exhaust the Supavisor
    // pooler under concurrent load. Idle connections close after 10s
    // so serverless invocations don't leak sockets. Per Nox A-6 / PERF-014.
    _pool = new Pool({
      connectionString,
      max: 3,
      idleTimeoutMillis: 10_000,
    });
  }
  return _pool;
}

/**
 * Execute a parameterized SQL query against the Supabase PostgreSQL database.
 * Uses @neondatabase/serverless Pool which is pg-compatible and works with
 * Supabase Supavisor pooler over WebSockets.
 */
export async function query<T = Record<string, unknown>>(
  text: string,
  params?: unknown[]
): Promise<T[]> {
  const pool = getPool();
  const result = await pool.query(text, params);
  return result.rows as T[];
}
