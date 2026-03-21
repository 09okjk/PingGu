"""
Search History Cases Skill — SQL 集中管理
所有查询语句统一在此维护，使用 asyncpg 的 $N 位置参数风格。
"""

# ─────────────────────────────────────────────────────────────
# 公共 SELECT 字段列表
# ─────────────────────────────────────────────────────────────
_MAIN_COLUMNS = """
    er.id,
    er.service_order_no,
    er.business_type,
    er.service_desc_name,
    er.service_type_name,
    er.equipment_model_code,
    er.equipment_model_name,
    er.equipment_qty,
    er.equipment_unit,
    er.task_description,
    er.device_content,
    er.risk_description,
    er.total_persons,
    er.total_days,
    er.work_schedule,
    er.construction_hours,
    er.inspection_hours,
    er.evaluated_at,
    er.tools_content,
    er.materials_content,
    er.special_tools_content
"""

# ─────────────────────────────────────────────────────────────
# Step 1：精确粗筛（含 service_type_code 条件）
#
# 参数顺序：
#   $1  business_type        (str)
#   $2  service_desc_code    (str)
#   $3  service_type_code    (str | None)
#   $4  equipment_model_code (str | None)   → 排序用
#   $5  input_task_desc      (str | None)   → trgm 相似度
#   $6  recency_tier1_years  (str)          → 时间衰减第一档
#   $7  recency_tier2_years  (str)          → 时间衰减第二档
#   $8  limit                (int)
# ─────────────────────────────────────────────────────────────
SEARCH_WITH_SERVICE_TYPE = f"""
SELECT
    {_MAIN_COLUMNS},
    CASE
        WHEN $5::text IS NOT NULL AND er.task_description IS NOT NULL
        THEN similarity(er.task_description, $5::text)
        ELSE 0.0
    END AS task_sim_score
FROM evaluation_records er
WHERE
    er.business_type = $1
    AND er.service_desc_code = $2
    AND (
        $3::text IS NULL
        OR er.service_type_code IS NULL
        OR er.service_type_code = $3::text
    )
ORDER BY
    CASE
        WHEN $4::text IS NOT NULL
             AND er.equipment_model_code = $4::text
        THEN 0 ELSE 1
    END ASC,
    task_sim_score DESC,
    CASE
        WHEN er.evaluated_at > NOW() - ($6 || ' years')::interval THEN 0
        WHEN er.evaluated_at > NOW() - ($7 || ' years')::interval THEN 1
        ELSE 2
    END ASC,
    er.evaluated_at DESC NULLS LAST
LIMIT $8
"""

# ─────────────────────────────────────────────────────────────
# Step 2B：放宽条件重查（去掉 service_type_code 条件）
#
# 参数顺序：
#   $1  business_type        (str)
#   $2  service_desc_code    (str)
#   $3  equipment_model_code (str | None)
#   $4  input_task_desc      (str | None)
#   $5  recency_tier1_years  (str)
#   $6  recency_tier2_years  (str)
#   $7  limit                (int)
# ─────────────────────────────────────────────────────────────
SEARCH_WITHOUT_SERVICE_TYPE = f"""
SELECT
    {_MAIN_COLUMNS},
    CASE
        WHEN $4::text IS NOT NULL AND er.task_description IS NOT NULL
        THEN similarity(er.task_description, $4::text)
        ELSE 0.0
    END AS task_sim_score
FROM evaluation_records er
WHERE
    er.business_type = $1
    AND er.service_desc_code = $2
ORDER BY
    CASE
        WHEN $3::text IS NOT NULL
             AND er.equipment_model_code = $3::text
        THEN 0 ELSE 1
    END ASC,
    task_sim_score DESC,
    CASE
        WHEN er.evaluated_at > NOW() - ($5 || ' years')::interval THEN 0
        WHEN er.evaluated_at > NOW() - ($6 || ' years')::interval THEN 1
        ELSE 2
    END ASC,
    er.evaluated_at DESC NULLS LAST
LIMIT $7
"""

# ─────────────────────────────────────────────────────────────
# Step 2A：批量拉取人员明细
#
# 参数：$1 record_ids (bigint[])
# ─────────────────────────────────────────────────────────────
FETCH_PERSONNEL = """
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
"""

# ─────────────────────────────────────────────────────────────
# Step 3：备注相似度补充（可选）
#
# 参数：
#   $1 record_ids   (bigint[])
#   $2 input_remark (str)
#   $3 threshold    (float)
# ─────────────────────────────────────────────────────────────
FETCH_REMARK_SIMILARITY = """
SELECT
    id,
    similarity(remark, $2::text) AS remark_sim_score
FROM evaluation_records
WHERE
    id = ANY($1::bigint[])
    AND remark IS NOT NULL
    AND similarity(remark, $2::text) > $3::float
ORDER BY remark_sim_score DESC
"""