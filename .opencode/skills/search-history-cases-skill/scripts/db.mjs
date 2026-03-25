import dotenv from "dotenv";
import pg from "pg";

dotenv.config();

const { Pool } = pg;

export const pool = new Pool({
  host: process.env.PGHOST,
  port: Number(process.env.PGPORT || 5432),
  database: process.env.PGDATABASE,
  user: process.env.PGUSER,
  password: process.env.PGPASSWORD,
  ssl: process.env.PGSSLMODE === "require" ? { rejectUnauthorized: false } : false
});

export async function closePool() {
  await pool.end();
}

export async function fetchLearningSamples(req, limit = 10) {
  const sql = `
    SELECT
      ls.sample_id,
      ls.task_id AS source_task_id,
      ls.scenario,
      ls.revision_summary,
      ls.quality_score,
      ls.status,
      ls.created_at
    FROM learning_samples ls
    WHERE ls.quality_score >= 0.75
      AND ls.status IN ('candidate', 'approved')
      AND (COALESCE($1, '') = '' OR ls.scenario->>'business_type' = $1)
      AND (COALESCE($2, '') = '' OR ls.scenario->>'service_desc_code' = $2)
      AND (COALESCE($3, '') = '' OR ls.scenario->>'service_type_code' IS NULL OR ls.scenario->>'service_type_code' = $3)
    ORDER BY
      CASE WHEN ls.status = 'approved' THEN 0 ELSE 1 END ASC,
      ls.quality_score DESC,
      ls.created_at DESC
    LIMIT ${limit}
  `;
  const { rows } = await pool.query(sql, [
    req.business_type || "",
    req.service_desc_code || "",
    req.service_type_code || ""
  ]);
  return rows.map(r => ({
    sample_id: r.sample_id,
    source_task_id: r.source_task_id,
    scenario: r.scenario,
    revision_summary: r.revision_summary,
    quality_score: Number(r.quality_score || 0),
    status: r.status,
    created_at: r.created_at
  }));
}