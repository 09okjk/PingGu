---
name: assessment-reasoning-skill
description: 基于结构化需求、历史案例和业务规则，完成风险识别、工时估算与人力配置推理
version: 1.1.0
changelog: |
  ## [1.1.0] - 工种职级体系升级
  - 更新 manpower_level_cover_rules 表结构（使用代码而非名称）
  - 新增 work_types 和 job_levels 基础数据表支持
  - manpower_engine 支持 ET*/MT*/D* 等新职级代码格式
  - 自动生成 1146 条职级覆盖规则（25 工种 × 193 职级）
  ## [1.0.1] - Windows 兼容性修复
  - 修复 Windows 控制台 UTF-8 编码问题
  - 优化输出编码处理逻辑
  ## [1.0.0] - 初始版本
  - 整合原 S2/S3/S4 功能
  - 支持风险识别、工时估算、人力推理
  - 支持 JSON 本地模式和 PostgreSQL 模式
metadata:
  clawdbot:
    emoji: 🧠
    requires:
      bins: ["python3"]
      env: ["PINGGU_USE_DB", "PINGGU_DB_HOST"]
    os: ["linux", "darwin", "win32"]
---

## Setup

### 快速测试（推荐）

**完整评估链路**:
```bash
cd {baseDir}
python scripts/main.py --action reason_assessment \
  --json-input samples/sample-input.json \
  --refs-dir references \
  --pretty
```

**仅风险识别**:
```bash
python scripts/main.py --action match_risks \
  --json-input samples/sample-input.json \
  --refs-dir references \
  --pretty
```

**仅工时估算**:
```bash
python scripts/main.py --action estimate_workhours \
  --json-input samples/sample-input.json \
  --refs-dir references \
  --pretty
```

**仅人力推理**:
```bash
python scripts/main.py --action estimate_manpower \
  --json-input samples/sample-input.json \
  --refs-dir references \
  --pretty
```

### Windows 兼容性说明

本 Skill 已修复 Windows 控制台编码问题，支持直接运行：

```powershell
# PowerShell
python scripts/main.py --action reason_assessment \
  --json-input samples/sample-input.json \
  --refs-dir references \
  --pretty
```

如遇编码问题，可设置环境变量：
```powershell
$env:PYTHONUTF8=1
python scripts/main.py --action reason_assessment \
  --json-input samples/sample-input.json \
  --refs-dir references \
  --pretty
```

### JSON 本地模式（默认）

无需数据库，直接从文件读取规则：

```bash
python scripts/main.py --action reason_assessment \
  --json-input samples/sample-input.json \
  --refs-dir references \
  --pretty
```

### PostgreSQL 模式（可选）

先安装依赖：
```bash
pip install psycopg2-binary
```

配置环境变量：
```bash
cp .env.example .env
```

编辑 `.env`：
```env
PINGGU_USE_DB=true
PINGGU_DB_HOST=192.168.124.126
PINGGU_DB_PORT=5432
PINGGU_DB_NAME=pinggu
PINGGU_DB_USER=postgres
PINGGU_DB_PASSWORD=wk888
PINGGU_DB_SSLMODE=disable
```

运行：
```bash
python scripts/main.py --action reason_assessment \
  --json-input samples/sample-input.json \
  --refs-dir references \
  --pretty
```

### 数据库表说明

PostgreSQL 模式需要以下表：

**必需表**:
- `risk_rules` - 风险识别规则
- `workhour_rules` - 工时估算规则
- `manpower_global_rules` - 全局规则
- `manpower_level_cover_rules` - 职级覆盖规则（使用工种/职级代码）

**可选表** (用于数据完整性):
- `work_types` - 工种配置 (25 条)
- `job_levels` - 职级配置 (193 条)

  详见 `README.md` 中的表结构说明。

---

## Input Contract（输入契约）

### 输入结构

```json
{
  "requirement": {
    "requirement_id": "REQ-001",
    "business_type": {"code": "BT001", "name": "轮机"},
    "service_desc": {"code": "RS0000001761", "name": "火警系统"},
    "service_type": {"code": "CS0001", "name": "维修"},
    "service_location_type": {"code": "SL001", "name": "港口"},
    "equipment_name": {"code": "EN0001", "name": "主机"},
    "equipment_model": {"code": "ET000826", "name": "MAN B&W-9S90ME-C9.2-TII"},
    "equipment_quantity": 1,
    "equipment_unit": {"code": "UM0005", "name": "台"},
    "remark": "内含船厂常规工作，可能存在交叉作业"
  },
  "history_cases": [
    {
      "case_id": "RH-2025-0009611001",
      "task_description": "主机常规坞修保养工作",
      "personnel": [...],
      "tools": [...],
      "materials": [...],
      "special_tools": [...]
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `requirement` | object | ✅ | 结构化需求单 |
| `requirement.business_type` | object | ✅ | 业务归口（code + name） |
| `requirement.service_desc` | object | ✅ | 服务描述（code + name） |
| `requirement.service_type` | object | ❌ | 服务类型 |
| `requirement.equipment_name` | object | ❌ | 设备名称 |
| `requirement.remark` | string | ❌ | 备注信息（用于风险触发） |
| `history_cases` | array | ❌ | 历史案例列表（来自 S1） |

## Output Contract（输出契约）

### 输出结构

```json
{
  "success": true,
  "data": {
    "risk_results": [
      {
        "risk_id": "RISK-001",
        "risk_name": "船厂交叉作业导致工期延误",
        "risk_level": "high",
        "confidence": "high",
        "trigger_basis": [
          "remark_keyword:交叉作业",
          "history_case:RH-2025-0009611001"
        ],
        "description": "现场存在交叉作业时，可能导致施工窗口受限与工期延误。",
        "suggested_action": "建议预留工期缓冲，并提前确认现场作业窗口。"
      }
    ],
    "workhour_results": [
      {
        "task_tag": "主机常规坞修保养工作",
        "suggested_hours": 110,
        "confidence": "medium",
        "basis": [
          "history_case_avg",
          "r5_rule:WH-001",
          "risk_adjustment:交叉作业"
        ],
        "note": "当前为单值估算结果，后续可升级为区间估算。"
      }
    ],
    "manpower_result": {
      "total_persons": 3,
      "confidence": "medium",
      "basis": [
        "serial_reuse:true",
        "job_level_cover:true"
      ],
      "explanation": "高职级人员可在串行任务中复用承担低职级任务，因此最小总人数为 3。"
    },
    "confidence_summary": {
      "risk": "high",
      "workhour": "medium",
      "manpower": "medium"
    }
  },
  "error": null
}
```

### 字段说明

#### 风险推理结果

| 字段 | 类型 | 说明 |
|------|------|------|
| `risk_id` | string | 风险 ID（如 RISK-001） |
| `risk_name` | string | 风险名称 |
| `risk_level` | string | 风险等级（high/medium/low） |
| `confidence` | string | 置信度（high/medium/low） |
| `trigger_basis` | array | 触发依据列表（remark_keyword, history_case, r3_rule 等） |
| `description` | string | 风险描述 |
| `suggested_action` | string | 建议措施 |

#### 工时估算结果

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_tag` | string | 任务标签/名称 |
| `suggested_hours` | number | 建议工时（小时） |
| `confidence` | string | 置信度（high/medium/low） |
| `basis` | array | 估算依据（history_case_avg, r5_rule, risk_adjustment 等） |
| `note` | string | 说明备注 |

#### 人力配置结果

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_persons` | number | 理论最小总人数 |
| `confidence` | string | 置信度（high/medium/low） |
| `basis` | array | 推理依据（serial_reuse, job_level_cover 等） |
| `explanation` | string | 推理过程说明 |

#### 置信度汇总

| 字段 | 类型 | 说明 |
|------|------|------|
| `risk` | string | 风险推理置信度 |
| `workhour` | string | 工时估算置信度 |
| `manpower` | string | 人力配置置信度 |

### 错误示例

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_INPUT",
    "message": "requirement.business_type 缺失，无法执行风险识别"
  }
}
```

## Error Codes（错误码）

| 错误码 | 说明 | 触发条件 |
|--------|------|---------|
| `INVALID_INPUT` | 输入格式错误 | 缺少必填字段或 JSON 格式错误 |
| `RISK_RULES_MISSING` | 风险规则缺失 | 无法加载风险规则库 |
| `WORKHOUR_RULES_MISSING` | 工时规则缺失 | 无法加载工时规则库 |
| `MANPOWER_RULES_MISSING` | 人力规则缺失 | 无法加载人力配置规则库 |
| `DB_CONNECTION_FAILED` | 数据库连接失败 | PostgreSQL 模式无法连接数据库 |

## Options（选项说明）

| 选项 | 说明 | 是否必填 | 示例 |
|------|------|----------|------|
| `--action` | 执行动作 | ✅ | `reason_assessment`, `match_risks`, `estimate_workhours`, `estimate_manpower` |
| `--json-input` | JSON 输入（字符串） | ❌ | `--json-input '{"requirement":{...}}'` |
| `--json-input-file` | JSON 输入文件路径 | ❌ | `--json-input-file samples/sample-input.json` |
| `--refs-dir` | Reference 文件目录 | ✅ | `--refs-dir references` |
| `--pretty` | 格式化输出 JSON | ❌ | `--pretty` |

## Actions（动作说明）

### reason_assessment（完整评估）

执行风险识别、工时估算、人力配置推理的完整流程。

```bash
python scripts/main.py --action reason_assessment \
  --json-input-file samples/sample-input.json \
  --refs-dir references \
  --pretty
```

### match_risks（仅风险识别）

仅执行风险识别。

```bash
python scripts/main.py --action match_risks \
  --json-input-file samples/sample-input.json \
  --refs-dir references \
  --pretty
```

### estimate_workhours（仅工时估算）

仅执行工时估算。

```bash
python scripts/main.py --action estimate_workhours \
  --json-input-file samples/sample-input.json \
  --refs-dir references \
  --pretty
```

### estimate_manpower（仅人力推理）

仅执行人力配置推理。

```bash
python scripts/main.py --action estimate_manpower \
  --json-input-file samples/sample-input.json \
  --refs-dir references \
  --pretty
```