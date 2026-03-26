# Skills 使用指南

> 版本：v2.0 | 最后更新：2026-03-26 | 适用技能：S1-S7

智能评估 Agent 系统，将船舶服务需求邮件自动转换为结构化评估报告。

## 📊 核心流程

```
需求解析 (S5) → 历史检索 (S1) → 评估推理 (S2) → 报告生成 (S6) → 意图检测 (S4) → 学习飞轮 (S3)
```

## 快速开始

### 前置要求

| Skill | 运行环境 | 依赖服务 |
|-------|----------|----------|
| S5 ParseRequirementSkill | Python 3.8+ | 无 |
| S1 SearchHistoryCasesSkill | Node.js 18+ | PostgreSQL 9.5+ (带 pg_trgm) |
| S2 AssessmentReasoningSkill | Python 3.8+ | PostgreSQL (可选) |
| S6 GenerateReportSkill | Python 3.8+ | 无 |
| S4 DialogIntentDetector | Python 3.8+ | Redis |
| S3 LearningFlywheelSkill | Python 3.8+ | PostgreSQL |

### 一键测试

**S5 测试**:
```bash
cd .opencode/skills/parse-requirement-skill
uv run python scripts/main.py --action parse \
  --input "主机异常振动，需要检修" \
  --refs references/r2-enums.json --pretty
```

**S1 测试**:
```bash
cd .opencode/skills/search-history-cases-skill
npm run search
```

**S2 测试**:
```bash
cd .opencode/skills/assessment-reasoning-skill
uv run python scripts/main.py --action reason_assessment \
  --json-input-file samples/sample-input.json --refs-dir references --pretty
```

**S6 测试**:
```bash
cd .opencode/skills/generate-report-skill
uv run python scripts/main.py --action generate_report \
  --json-input-file samples/sample-input.json --pretty
```

**S4 测试**:
```bash
cd .opencode/skills/s4-dialog-intent-detector
uv run python dialog_intent_detector.py "好的，确认"
```

**S3 测试**:
```bash
cd .opencode/skills/learning-flywheel-skill
uv run python scripts/main.py --action learn_from_revision \
  --initial-draft samples/initial.md \
  --final-draft samples/final.md \
  --refs-dir references --pretty
```

### 环境配置

#### 1. Python 环境（S5/S2/S6/S3/S4）

```bash
# 安装 uv（如果未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows PowerShell:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 同步依赖（各 Skill 目录内执行）
uv sync
```

#### 2. Node.js 环境（S1）

```bash
cd search-history-cases-skill
npm install
cp .env.example .env
# 编辑 .env 配置数据库连接
```

#### 3. PostgreSQL 配置（S1/S2/S3）

```sql
-- 启用 pg_trgm 扩展
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 创建索引（可选，提升性能）
CREATE INDEX IF NOT EXISTS idx_fault_description_trgm 
ON assessment_history USING gin (fault_description gin_trgm_ops);
```

#### 4. Redis 配置（S4）

```bash
# 启动 Redis
redis-server

# 验证连接
redis-cli ping  # 应返回 PONG
```

---

## S5 ParseRequirementSkill - 需求解析

将自然语言邮件解析为结构化需求单。

### 执行逻辑

```
输入：原始需求单 / 邮件文本
  ↓
Step 1：结构化字段解析（枚举合法性校验）
  ↓
Step 2：备注 NLU（提取关键信息、语言识别）
  ↓
Step 3：交互确认闭环（parse → revise → confirm）
  ↓
输出：结构化解析结果 + NLU 摘要 + 状态
```

### 输出示例

```json
{
  "success": true,
  "data": {
    "ship_info": {
      "ship_name": "远洋 1 号",
      "ship_id": "YH-2024-001",
      "ship_type": "货轮"
    },
    "service_items": [
      {
        "item_id": "SI-001",
        "service_type": "主机检修",
        "equipment_type": "主发动机",
        "fault_description": "异常振动",
        "priority": "high",
        "estimated_urgency": "24h"
      }
    ]
  },
  "confidence": 0.92,
  "error": null
}
```

### 错误处理

| 错误码 | 触发条件 | 处理方式 |
|--------|---------|---------|
| `FILE_NOT_FOUND` | 枚举文件不存在 | 返回错误，提示检查文件路径 |
| `PARSE_FAILED` | 无法解析输入文本 | 返回错误，请求更详细描述 |
| `AMBIGUOUS_INPUT` | 匹配到多个服务类型 | 返回候选列表，请求确认 |

📖 详细文档：[parse-requirement-skill/SKILL.md](parse-requirement-skill/SKILL.md)

---

## S1 SearchHistoryCasesSkill - 历史检索

根据结构化需求检索相似历史案例。

### 执行逻辑

```
输入：标准化服务需求单
  ↓
Step 1：加载数据库配置（.env）
  ↓
Step 2：构建查询向量
  ↓
Step 3：执行渐进式检索（精确→模糊→语义）
  ↓
Step 4：计算相似度分数（pg_trgm）
  ↓
输出：Top-K 相似案例（LIMIT 5）
```

### SQL 查询示例

```sql
SELECT 
  project_name, service_type, equipment_type,
  fault_description, work_hours, risk_factors,
  similarity(fault_description, $1::text) AS score
FROM assessment_history
WHERE service_type = $2
ORDER BY score DESC
LIMIT 5;
```

### 输出示例

```json
{
  "success": true,
  "data": {
    "cases": [
      {
        "case_id": "AH-2024-089",
        "project_name": "远洋 1 号主机检修",
        "service_type": "主机检修",
        "fault_description": "主机运转时异常振动",
        "work_hours": 3.5,
        "risk_factors": ["技术难点", "备件供应"],
        "similarity_score": 0.87
      }
    ],
    "search_metadata": {
      "total_matches": 23,
      "returned": 5,
      "search_rounds": 2
    }
  },
  "confidence": 0.87,
  "error": null
}
```

### 错误处理

| 错误码 | 触发条件 | 处理方式 |
|--------|---------|---------|
| `DB_CONNECTION_FAILED` | PostgreSQL 连接失败 | 返回错误，检查 .env 配置 |
| `EXTENSION_MISSING` | pg_trgm 未启用 | 返回错误，提示创建扩展 |
| `NO_CASES_FOUND` | 无相似案例 | 返回空数组，confidence=0.3 |

📖 详细文档：[search-history-cases-skill/SKILL.md](search-history-cases-skill/SKILL.md)

---

## S2 AssessmentReasoningSkill - 评估推理

统一执行风险识别、工时估算与人力配置推理。

### 执行逻辑

```
输入：需求单 + 历史案例
  ↓
Step 1：加载业务规则（risk_rules.json）
  ↓
Step 2：风险识别（技术难点/作业环境/备件供应）
  ↓
Step 3：工时估算（基于历史案例 + 风险系数调整）
  ↓
Step 4：人力配置（人员级别匹配 + 专业技能要求）
  ↓
输出：风险评估 + 工时估算 + 人力配置
```

### 输出示例

```json
{
  "success": true,
  "data": {
    "risk_assessment": [
      {
        "risk_id": "R-001",
        "risk_type": "技术难点",
        "description": "主机振动原因需进一步诊断",
        "level": "high",
        "mitigation": "准备振动分析仪器，预留诊断时间"
      }
    ],
    "work_hours": {
      "base_hours": 2.0,
      "risk_adjustment": 1.5,
      "total_hours": 3.0,
      "unit": "人天"
    },
    "staff_allocation": [
      {
        "level": "高级工程师",
        "count": 1,
        "skills": ["主机检修", "振动分析"],
        "rate_category": "senior"
      }
    ]
  },
  "confidence": 0.85,
  "error": null
}
```

### 错误处理

| 错误码 | 触发条件 | 处理方式 |
|--------|---------|---------|
| `RULES_FILE_MISSING` | 规则文件不存在 | 返回错误，检查 references 目录 |
| `DB_CONNECTION_FAILED` | PostgreSQL 连接失败 | 返回错误，检查 .env 配置 |
| `INVALID_INPUT` | 输入格式错误 | 返回错误，提示检查输入 JSON |

📖 详细文档：[assessment-reasoning-skill/SKILL.md](assessment-reasoning-skill/SKILL.md)

---

## S6 GenerateReportSkill - 报告生成

整合所有输入数据，生成 Markdown 评估报告。

### 执行逻辑

```
输入：需求单 + 历史案例 + 评估推理结果
  ↓
Step 1：整合所有输入数据
  ↓
Step 2：生成报告结构（项目概述/技术评估/风险识别）
  ↓
Step 3：格式化输出（Markdown 格式）
  ↓
Step 4：支持编辑操作（apply_edit）
  ↓
输出：Markdown 评估报告（人类可读）
```

### 报告模板

```markdown
# 评估报告：{project_name}

## 1. 项目概述
- 船舶信息：{ship_name}, {ship_id}
- 服务类型：{service_type}
- 作业地点：{location}

## 2. 技术评估
### 2.1 设备信息
| 项目 | 详情 |
|------|------|
| 设备型号 | {...} |
| 故障描述 | {...} |

## 3. 风险识别 ⚠️
| 风险项 | 等级 | 缓解建议 |
|--------|------|---------|
| {risk} | {level} | {mitigation} |

## 4. 工作量估算
- 基础工时：**{base_hours} 人天**
- 总计工时：**{total_hours} 人天**

## 5. 人力配置
| 级别 | 人数 | 技能要求 |
|------|------|---------|
| {level} | {count} | {skills} |
```

### 错误处理

| 错误码 | 触发条件 | 处理方式 |
|--------|---------|---------|
| `INVALID_INPUT` | 输入数据不完整 | 返回错误，提示检查输入 |
| `EDIT_FAILED` | 编辑指令无法解析 | 返回错误，请求更明确指令 |
| `TEMPLATE_ERROR` | 报告模板错误 | 返回错误，检查模板文件 |

📖 详细文档：[generate-report-skill/SKILL.md](generate-report-skill/SKILL.md)

---

## S4 DialogIntentDetector - 意图检测

检测工务审核对话中的意图类型。

### 意图类型

| 意图 | 触发词示例 | 状态转换 | 后续动作 |
|------|-----------|---------|---------|
| `CONFIRM` | "好了"/"确认"/"通过" | 待确认 → 交付 | 触发 S3 学习 |
| `EDIT` | "修改"/"调整"/"改成" | 审核中 → 审核中 | 返回 S6 修改 |
| `CANCEL` | "取消"/"放弃"/"算了" | 待确认 → 审核中 | 返回审核状态 |
| `OTHER` | 其他表述 | 保持当前状态 | 继续对话 |

### 状态机

```
        审核中
       /     \
  修改意图    确认意图
     |         |
     v         v
  S6 修改    待确认
     |         |
     +----+----+
          |
          v
     S3 学习飞轮
          |
          v
        交付
```

📖 详细文档：[s4-dialog-intent-detector/SKILL.md](s4-dialog-intent-detector/SKILL.md)

---

## S3 LearningFlywheelSkill - 学习飞轮

采集修订差异，提炼学习资产。

### 执行逻辑

```
输入：初版报告 + 终版报告
  ↓
Step 1：文档差异分析
  ↓
Step 2：差异归因（工时调整/风险重评）
  ↓
Step 3：提取学习样本
  ↓
Step 4：生成规则候选
  ↓
Step 5：更新偏好模型
  ↓
输出：学习样本 + 规则候选 + 偏好模型
```

📖 详细文档：[learning-flywheel-skill/SKILL.md](learning-flywheel-skill/SKILL.md)

---

## 完整工作流

```
客户邮件
    ↓
┌─────────────────┐
│ S5 需求解析      │
│ 输入：自然语言   │
│ 输出：JSON 需求单 │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ S1 历史检索      │◄────│ PostgreSQL      │
│ 输入：需求单     │     │ assessment_     │
│ 输出：Top-K 案例  │     │ history 表      │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ S2 评估推理      │◄────│ PostgreSQL      │
│ 输入：需求单     │     │ risk_rules 表   │
│ + 历史案例      │     │ staff_levels 表 │
│ 输出：风险评估   │     └─────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ S6 报告生成      │
│ 输入：所有数据   │
│ 输出：Markdown   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ S4 对话意图检测  │◄────│ Redis           │
│ 输入：对话文本   │     │ 状态存储         │
│ 输出：意图类型   │     └─────────────────┘
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌─────────────────┐
│ S6 修改  │ │ S3 学习飞轮      │
│ 报告     │ │ 输入：初版 + 终版 │
│         │ │ 输出：学习资产   │
└─────────┘ └────────┬────────┘
                     │
                     ▼
              ┌─────────────────┐
              │ PostgreSQL      │
              │ learning_       │
              │ samples 表       │
              └─────────────────┘
```

---

## 环境检查清单

- [ ] Python 3.8+ 可用 (`python --version`)
- [ ] Node.js 18+ 可用 (`node --version`)
- [ ] PostgreSQL 可连接 (`psql -h <host> -U <user> -d <db>`)
- [ ] pg_trgm 扩展已启用
- [ ] Redis 可连接 (`redis-cli ping`)
- [ ] .env 文件已配置（S1/S2/S3）
- [ ] 依赖已安装（`npm install` / `uv sync`）

---

## 版本信息

| Skill | 当前版本 | 更新日期 |
|-------|----------|----------|
| ParseRequirementSkill | 2.0.0 | 2026-03 |
| SearchHistoryCasesSkill | 1.0.1 | 2026-03 |
| AssessmentReasoningSkill | 1.1.0 | 2026-03 |
| GenerateReportSkill | 1.0.0 | 2026-03 |
| DialogIntentDetector | 1.0.0 | 2026-03 |
| LearningFlywheelSkill | 1.0.0 | 2026-03 |
