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