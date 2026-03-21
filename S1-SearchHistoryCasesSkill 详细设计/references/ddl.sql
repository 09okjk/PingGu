-- ============================================================
-- Search History Cases Skill — 数据库建表语句
-- 参考文档：S1 - SearchHistoryCasesSkill 详细设计.md 第五节
-- ============================================================

-- 启用 pg_trgm 扩展（pg_trgm 索引依赖此扩展）
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================
-- 主表：evaluation_records
-- 1条记录 = 1个历史评估案例
-- ============================================================
CREATE TABLE IF NOT EXISTS evaluation_records (

    -- 主键与业务标识
    id                      BIGSERIAL PRIMARY KEY,
    inquiry_no              VARCHAR(50) NOT NULL,
    service_order_no        VARCHAR(50) NOT NULL UNIQUE,

    -- 检索侧：主维度（必建索引）
    business_type           VARCHAR(20) NOT NULL,           -- 电气 / 轮机
    service_desc_code       VARCHAR(50),
    service_desc_name       VARCHAR(100),
    service_type_code       VARCHAR(50),                    -- 允许 NULL（~5% 无值）
    service_type_name       VARCHAR(100),

    -- 检索侧：设备维度（允许 NULL，有则加权匹配）
    equipment_model_code    VARCHAR(50),
    equipment_model_name    VARCHAR(200),
    equipment_manufacturer  VARCHAR(200),
    equipment_part_model    VARCHAR(200),
    equipment_qty           INTEGER,
    equipment_unit          VARCHAR(20),

    -- 检索侧：文本（pg_trgm 模糊匹配）
    task_description        TEXT,
    device_content          VARCHAR(200),

    -- 输出侧：风险
    risk_description        TEXT,

    -- 输出侧：工时与人力
    construction_hours      DECIMAL(8,1),
    inspection_hours        DECIMAL(8,1),
    total_persons           INTEGER,                        -- 填写率 ~80%
    total_days              DECIMAL(6,1),                   -- 填写率 ~80%
    work_schedule           SMALLINT,
    -- 工作制枚举（仅非航修任务填写，填写率 ~60%，允许 NULL）：
    --   1 = 8小时/日
    --   2 = 9小时/日
    --   3 = 10小时/日
    --   4 = 11小时/日
    --   5 = 12小时/日
    --   6 = 24小时/日

    -- 输出侧：三类物料清单 JSONB（三类结构不同，应用层分别解析）
    tools_content           JSONB,
    -- 需求工具结构：
    -- [{toolName, toolTypeNo(有值), quantity, unitMeasurement:{no,zhName}}]

    materials_content       JSONB,
    -- 耗材结构（含 model 型号，toolTypeNo 固定 null）：
    -- [{toolName, model, quantity, toolTypeNo:null, unitMeasurement:{no,zhName}}]

    special_tools_content   JSONB,
    -- 专用工具结构（与耗材相同）：
    -- [{toolName, model, quantity, toolTypeNo:null, unitMeasurement:{no,zhName}}]

    -- 辅助参考字段
    main_valve_assessment   VARCHAR(50),                    -- 不需要 / 需要
    third_party_type        VARCHAR(20),                    -- 儒海 / 第三方
    remark                  TEXT,                           -- 填写率 ~50%，不用于检索
    assessment_description  TEXT,
    assessment_remark       TEXT,
    evaluator_name          VARCHAR(50),
    reviewer_name           VARCHAR(50),
    evaluated_at            TIMESTAMP,
    created_at              TIMESTAMP DEFAULT NOW()
);

-- ── 索引 ──────────────────────────────────────────────────────

-- 单列索引：高频过滤字段
CREATE INDEX IF NOT EXISTS idx_er_business_type
    ON evaluation_records(business_type);

CREATE INDEX IF NOT EXISTS idx_er_service_desc
    ON evaluation_records(service_desc_code);

CREATE INDEX IF NOT EXISTS idx_er_service_type
    ON evaluation_records(service_type_code);

CREATE INDEX IF NOT EXISTS idx_er_equipment_model
    ON evaluation_records(equipment_model_code);

CREATE INDEX IF NOT EXISTS idx_er_evaluated_at
    ON evaluation_records(evaluated_at DESC);

-- 组合索引：最常用三维度过滤
CREATE INDEX IF NOT EXISTS idx_er_core_search
    ON evaluation_records(business_type, service_desc_code, service_type_code);

-- pg_trgm 索引：文本模糊匹配
CREATE INDEX IF NOT EXISTS idx_er_task_trgm
    ON evaluation_records USING GIN(task_description gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_er_device_trgm
    ON evaluation_records USING GIN(device_content gin_trgm_ops);

-- ============================================================
-- 人员子表：evaluation_personnel
-- 从 记录内容_人员内容 JSON 数组逐条展开
-- 1条记录 = 1个「工种 + 职级 + 人数 + 工时 + 任务描述」条目
-- ============================================================
CREATE TABLE IF NOT EXISTS evaluation_personnel (

    id                            BIGSERIAL PRIMARY KEY,
    record_id                     BIGINT NOT NULL
                                      REFERENCES evaluation_records(id)
                                      ON DELETE CASCADE,

    work_type_code                VARCHAR(20),  -- 工种编码，如 JN0001
    work_type_name                VARCHAR(50),  -- 工种名称，如 电气工程师
    job_level_code                VARCHAR(20),  -- 职级编码，如 RN0009
    job_level_name                VARCHAR(50),  -- 职级名称，如 中级工程师(T4)
    quantity                      INTEGER,      -- 所需人数
    construction_hour             DECIMAL(6,1), -- 工时（小时）

    detailed_job_responsibilities TEXT,
    -- 任务分组键：相同描述的条目属于同一施工任务
    -- 是 S4 人力调度推理的任务分组依据
    -- 允许 NULL（历史数据中存在未填写情况）

    sort_order                    INTEGER       -- 保留原始 JSON 数组顺序
);

-- ── 索引 ──────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_ep_record_id
    ON evaluation_personnel(record_id);

CREATE INDEX IF NOT EXISTS idx_ep_work_type
    ON evaluation_personnel(work_type_code);

CREATE INDEX IF NOT EXISTS idx_ep_job_level
    ON evaluation_personnel(job_level_code);

CREATE INDEX IF NOT EXISTS idx_ep_job_resp_trgm
    ON evaluation_personnel
    USING GIN(detailed_job_responsibilities gin_trgm_ops);