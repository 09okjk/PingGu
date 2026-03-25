#!/usr/bin/env node
import fs from "fs";
import path from "path";
import { pool, closePool, fetchLearningSamples } from "./db.mjs";

function parseArgs(argv) {
  const args = { pretty: false, topk: undefined, threshold: undefined };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--input") args.input = argv[++i];
    else if (a === "--topk") args.topk = Number(argv[++i]);
    else if (a === "--threshold") args.threshold = Number(argv[++i]);
    else if (a === "--pretty") args.pretty = true;
  }
  return args;
}

function validateInput(input) {
  if (!input?.business_type) throw new Error("business_type is required");
  if (!input?.service_desc_code) throw new Error("service_desc_code is required");
}

function buildMatchReason(c, req, relaxed) {
  const parts = [];
  parts.push(`业务归口 (${c.business_type || "-"})`);
  parts.push(`服务描述 (${c.service_desc_name || req.service_desc_code})`);

  if (c.service_type_name) parts.push(`服务类型 (${c.service_type_name})`);
  else parts.push("服务类型 (NULL 兼容)");

  if (req.equipment_model_code && c.equipment_model_code === req.equipment_model_code) {
    parts.push(`设备型号命中 (${c.equipment_model_name || c.equipment_model_code})`);
  }

  const tail = [`任务相似度：${Number(c.task_sim_score || 0).toFixed(3)}`];
  if (relaxed) tail.push("⚠️ 服务类型条件已放宽");

  return `命中：${parts.join(" + ")} | ${tail.join(" | ")}`;
}

function buildScenarioMatchReason(scenario, req) {
  const parts = [];
  if (scenario?.business_type) parts.push(`业务归口 (${scenario.business_type})`);
  if (scenario?.service_desc_code) parts.push(`服务描述 (${scenario.service_desc_code})`);
  if (scenario?.service_type_code) parts.push(`服务类型 (${scenario.service_type_code})`);
  else parts.push("服务类型");
  return `命中：${parts.join(" + ")}`;
}

async function queryCandidates(req, withServiceType, limit = 20) {
  if (withServiceType) {
    const sql = `
      SELECT
        er.id, er.service_order_no, er.business_type, er.service_desc_name,
        er.service_type_name, er.equipment_model_code, er.equipment_model_name,
        er.equipment_qty, er.equipment_unit, er.task_description, er.device_content,
        er.risk_description, er.total_persons, er.total_days, er.work_schedule,
        er.construction_hours, er.inspection_hours, er.evaluated_at,
        er.tools_content, er.materials_content, er.special_tools_content,
        CASE WHEN COALESCE($5, '') != '' THEN similarity(er.task_description, $5) ELSE 0 END AS task_sim_score
      FROM evaluation_records er
      WHERE er.business_type = $1 AND er.service_desc_code = $2
        AND (COALESCE($3, '') = '' OR er.service_type_code IS NULL OR er.service_type_code = $3)
      ORDER BY
        CASE WHEN COALESCE($4, '') != '' AND er.equipment_model_code = $4 THEN 0 ELSE 1 END ASC,
        task_sim_score DESC,
        CASE WHEN er.evaluated_at > NOW() - INTERVAL '2 years' THEN 0 WHEN er.evaluated_at > NOW() - INTERVAL '3 years' THEN 1 ELSE 2 END ASC,
        er.evaluated_at DESC
      LIMIT ${limit}
    `;
    const { rows } = await pool.query(sql, [
      req.business_type || "",
      req.service_desc_code || "",
      req.service_type_code || "",
      req.equipment_model_code || "",
      req.task_description || ""
    ]);
    return rows;
  } else {
    const sql = `
      SELECT
        er.id, er.service_order_no, er.business_type, er.service_desc_name,
        er.service_type_name, er.equipment_model_code, er.equipment_model_name,
        er.equipment_qty, er.equipment_unit, er.task_description, er.device_content,
        er.risk_description, er.total_persons, er.total_days, er.work_schedule,
        er.construction_hours, er.inspection_hours, er.evaluated_at,
        er.tools_content, er.materials_content, er.special_tools_content,
        CASE WHEN COALESCE($4, '') != '' THEN similarity(er.task_description, $4) ELSE 0 END AS task_sim_score
      FROM evaluation_records er
      WHERE er.business_type = $1 AND er.service_desc_code = $2
      ORDER BY
        CASE WHEN COALESCE($3, '') != '' AND er.equipment_model_code = $3 THEN 0 ELSE 1 END ASC,
        task_sim_score DESC,
        CASE WHEN er.evaluated_at > NOW() - INTERVAL '2 years' THEN 0 WHEN er.evaluated_at > NOW() - INTERVAL '3 years' THEN 1 ELSE 2 END ASC,
        er.evaluated_at DESC
      LIMIT ${limit}
    `;
    const { rows } = await pool.query(sql, [
      req.business_type || "",
      req.service_desc_code || "",
      req.equipment_model_code || "",
      req.task_description || ""
    ]);
    return rows;
  }
}

async function fetchPersonnel(recordIds) {
  if (!recordIds.length) return {};
  const sql = `
    SELECT
      ep.record_id,
      ep.work_type_code,
      ep.work_type_name,
      ep.job_level_code,
      ep.job_level_name,
      ep.quantity,
      ep.construction_hour,
      ep.detailed_job_responsibilities,
      ep.sort_order
    FROM evaluation_personnel ep
    WHERE ep.record_id = ANY($1::bigint[])
    ORDER BY ep.record_id, ep.sort_order
  `;
  const { rows } = await pool.query(sql, [recordIds]);
  const map = {};
  for (const r of rows) {
    if (!map[r.record_id]) map[r.record_id] = [];
    map[r.record_id].push({
      work_type_code: r.work_type_code,
      work_type_name: r.work_type_name,
      job_level_code: r.job_level_code,
      job_level_name: r.job_level_name,
      quantity: r.quantity,
      construction_hour: r.construction_hour,
      task_desc: r.detailed_job_responsibilities
    });
  }
  return map;
}

async function fetchRemarkScores(recordIds, remark) {
  if (!recordIds.length || !remark) return {};
  const sql = `
    SELECT id, similarity(remark, $2::text) AS remark_sim_score
    FROM evaluation_records
    WHERE id = ANY($1::bigint[])
      AND remark IS NOT NULL
      AND similarity(remark, $2::text) > 0.1
    ORDER BY remark_sim_score DESC
  `;
  const { rows } = await pool.query(sql, [recordIds, remark]);
  const map = {};
  for (const r of rows) map[r.id] = Number(r.remark_sim_score);
  return map;
}

async function run() {
  const args = parseArgs(process.argv);
  if (!args.input) throw new Error("Missing --input <path>");

  const inputPath = path.resolve(process.cwd(), args.input);
  const raw = fs.readFileSync(inputPath, "utf-8");
  const req = JSON.parse(raw);

  validateInput(req);

  const topK = Number(args.topk ?? req.top_k ?? 5);
  const threshold = Number(args.threshold ?? 5);

  let candidates = await queryCandidates(req, true, 20);
  let relaxed = false;

  if (candidates.length < threshold) {
    candidates = await queryCandidates(req, false, 20);
    relaxed = true;
  }

  const topCases = candidates.slice(0, topK);
  const ids = topCases.map(c => c.id);

  const personnelMap = await fetchPersonnel(ids);
  const remarkScoreMap = await fetchRemarkScores(ids, req.remark ?? null);
  const learningSamples = await fetchLearningSamples(req, 10);

  const result = topCases.map(c => ({
    case_id: c.service_order_no,
    match_reason: buildMatchReason(c, req, relaxed),
    service_type_relaxed: relaxed,
    task_sim_score: Number(c.task_sim_score || 0),
    remark_sim_score: remarkScoreMap[c.id] ?? null,
    evaluated_at: c.evaluated_at,
    equipment_info: {
      model_code: c.equipment_model_code,
      model_name: c.equipment_model_name,
      qty: c.equipment_qty,
      unit: c.equipment_unit
    },
    risk_description: c.risk_description,
    task_description: c.task_description,
    total_persons: c.total_persons,
    total_days: c.total_days,
    work_schedule: c.work_schedule,
    construction_hours: c.construction_hours,
    inspection_hours: c.inspection_hours,
    personnel: personnelMap[c.id] || [],
    tools: c.tools_content || [],
    materials: c.materials_content || [],
    special_tools: c.special_tools_content || []
  }));

  const output = {
    skill: "SearchHistoryCasesSkill",
    version: "1.0.0",
    input: req,
    top_k: topK,
    candidate_threshold: threshold,
    candidate_count: candidates.length,
    returned_count: result.length,
    service_type_relaxed: relaxed,
    results: result,
    learning_samples: learningSamples.map(s => ({
      sample_id: s.sample_id,
      scenario_match_reason: buildScenarioMatchReason(s.scenario, req),
      quality_score: s.quality_score,
      revision_summary: s.revision_summary,
      source_task_id: s.source_task_id,
      status: s.status
    }))
  };

  console.log(args.pretty ? JSON.stringify(output, null, 2) : JSON.stringify(output));
}

run()
  .catch(err => {
    console.error(`[SearchHistoryCasesSkill] Error: ${err.message}`);
    process.exitCode = 1;
  })
  .finally(async () => {
    await closePool();
  });
