---
name: Search History Cases
slug: search-history-cases
version: 1.0.0
description: 根据服务需求单，从历史评估数据库中渐进式检索最相似的 Top-K 历史评估案例（S1 Skill）
metadata:
  clawdbot:
    emoji: 🔍
    requires:
      bins: ["python3"]
      env:
        required:
          - PINGGU_DB_HOST
          - PINGGU_DB_NAME
          - PINGGU_DB_USER
          - PINGGU_DB_PASSWORD
        optional:
          - PINGGU_DB_PORT
          - PINGGU_DB_POOL_MIN
          - PINGGU_DB_POOL_MAX
          - S1_DEFAULT_TOP_K
          - S1_CANDIDATE_LIMIT
          - S1_CANDIDATE_THRESHOLD
          - S1_REMARK_SIM_THRESHOLD
          - S1_RECENCY_TIER1_YEARS
          - S1_RECENCY_TIER2_YEARS
    os: ["linux", "darwin", "win32"]
---

# Search History Cases 🔍

根据服务需求单的结构化字段（业务归口、服务描述、设备型号等），
从 8000 条历史评估记录中执行**渐进式 Agentic 检索**，返回 Top-K 最相似案例。
检索结果包含完整的人员工时明细、工具耗材清单、风险描述，供后续评估报告生成使用。

## When to Use（何时使用）

✅ 适用场景：
- 用户/Agent 说"查找类似案例"、"找参考评估"、"搜索历史记录"时
- 需要为当前服务需求单寻找历史参考数据时
- GenerateReportSkill 需要历史案例作为生成报告的依据时
- 上层 Agent 需要动态调整 Top-K 数量时

## When NOT to Use（何时不用）

❌ 不适用场景：
- 查询单条具体案例（直接用 service_order_no 查数据库）
- 统计分析类查询（如工时分布、人力配置规律），请使用 S3/S4 Skill
- 风险匹配，请使用 S2 MatchRisksSkill
- 数据库尚未完成初始化导入时

## Setup（安装配置）

### 1. 安装 Python 依赖

```bash
pip install asyncpg>=0.29.0 pydantic>=2.6.0
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写数据库连接信息：

```bash
cp .env.example .env
# 编辑 .env 填写真实配置
```

### 3. 初始化数据库（首次使用）

确保 PostgreSQL 已启用 `pg_trgm` 扩展，并已按 `references/ddl.sql` 建表导入数据：

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### 4. 运行检索

```bash
python3 {baseDir}/scripts/search.py \
  --business-type "轮机" \
  --service-desc-code "RS0000000001" \
  --service-type-code "CS0017" \
  --equipment-model-code "ET000000000826" \
  --task-description "主机坞修保养" \
  --top-k 5
```

## Options（选项说明）

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--business-type` | string | ✅ | - | 业务归口：`电气` / `轮机` |
| `--service-desc-code` | string | ✅ | - | 服务描述编码，如 `RS0000000001` |
| `--service-type-code` | string | ❌ | null | 服务类型编码，如 `CS0017` |
| `--equipment-model-code` | string | ❌ | null | 设备型号编码，有则精确加权 |
| `--task-description` | string | ❌ | null | 施工任务描述，用于 pg_trgm 排序 |
| `--remark` | string | ❌ | null | 备注文本，用于相似度补充标注 |
| `--top-k` | int | ❌ | 5 | 返回案例数（1~20），上层 Agent 可动态传入 |
| `--output` | string | ❌ | stdout | 输出目标：`stdout` / 文件路径 |
| `--format` | string | ❌ | json | 输出格式：`json` / `pretty` |

## Core Rules（核心规则）

### 渐进式检索策略（4步）

```
Step 1  精确粗筛：business_type + service_desc_code + service_type_code（OR NULL）
        → 候选集 >= threshold（默认5）时跳到 Step 2A
Step 2B 条件放宽：去掉 service_type_code，重新粗筛
        → 结果标注 "⚠️ 服务类型条件已放宽"
Step 2A 取 Top-K：按「设备型号命中 > trgm相似度 > 时间衰减」排序后截取
        → 批量拉取人员明细子表
Step 3  备注补充：仅当输入有 remark 时，计算相似度并附加到结果（不改变排序）
```

### 排序优先级

1. **设备型号精确命中**（equipment_model_code 一致 → 权重最高）
2. **任务描述 trgm 相似度**（pg_trgm similarity 降序）
3. **时间衰减**（近2年 > 近3年 > 更早，可通过环境变量调整）

### 工作制枚举含义

| 值 | 含义 | 备注 |
|----|------|------|
| 1 | 8小时/日 | 仅非航修任务填写，航修任务此字段为 NULL |
| 2 | 9小时/日 | |
| 3 | 10小时/日 | |
| 4 | 11小时/日 | |
| 5 | 12小时/日 | |
| 6 | 24小时/日 | |

### 物料清单字段差异

三类物料（需求工具 / 耗材 / 专用工具）JSON 结构不同，应用层需分别解析：
- **需求工具**：有 `toolTypeNo`（有值），无 `model`
- **耗材 / 专用工具**：有 `model`（型号），`toolTypeNo` 固定为 null

详见 `references/ddl.sql` 注释。

## Security & Privacy（安全说明）

- 所有数据库连接信息通过**环境变量**传入，不硬编码在代码中
- Skill 为**只读操作**，不执行任何 INSERT / UPDATE / DELETE
- 使用 asyncpg **参数化查询**，防止 SQL 注入
- `.env` 文件已加入 `.gitignore`，不会被提交到版本库

## Related Skills（相关技能）

- **S2 MatchRisksSkill**：使用本 Skill 返回的 `risk_description` 和 `remark` 进行风险匹配
- **S3 EstimateWorkHoursSkill**：使用本 Skill 返回的 `personnel` 明细进行工时统计
- **S4 SchedulePersonnelSkill**：使用本 Skill 返回的 `total_persons` / `work_schedule` 进行人力调度推理

## Feedback（反馈）

- 检索结果不符合预期时，优先检查 `business_type` + `service_desc_code` 是否填写正确
- 候选集为空时，确认数据库已完成初始化导入
- 性能问题时，确认 `references/ddl.sql` 中的索引已全部创建