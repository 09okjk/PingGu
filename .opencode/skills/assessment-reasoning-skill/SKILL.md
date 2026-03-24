---
name: assessment-reasoning-skill
description: 基于结构化需求、历史案例和业务规则，完成风险识别、工时估算与人力配置推理
version: 1.0.0
changelog: |
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
PINGGU_DB_HOST=localhost
PINGGU_DB_PORT=5432
PINGGU_DB_NAME=pinggu
PINGGU_DB_USER=postgres
PINGGU_DB_PASSWORD=your_password
PINGGU_DB_SSLMODE=disable
```

运行：
```bash
python scripts/main.py --action reason_assessment \
  --json-input samples/sample-input.json \
  --refs-dir references \
  --pretty
```