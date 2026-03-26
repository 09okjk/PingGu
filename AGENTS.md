# AGENTS.md - 智能评估 Agent 开发指南

> 最后更新：2026-03-26 | 适用版本：S1/S2/S3/S4/S5/S6/S7

## 项目结构

```
.opencode/
├── skills/
│   ├── parse-requirement-skill/    # S5 - 需求解析 (Python)
│   ├── search-history-cases-skill/ # S1 - 历史检索 (Node.js)
│   ├── assessment-reasoning-skill/ # S2 - 评估推理 (Python)
│   ├── generate-report-skill/      # S6 - 报告生成 (Python)
│   ├── s4-dialog-intent-detector/  # S4 - 意图检测 (Python)
│   └── learning-flywheel-skill/    # S3 - 学习飞轮 (Python)
└── package.json
```

## 首次配置（新环境）

**0. 安装 uv (Python 包管理)**:
```bash
# 安装 uv（如果未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows PowerShell:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**1. 数据库配置 (S1/S2/S3)**:
```bash
# S1 - 历史检索
cd .opencode/skills/search-history-cases-skill
cp .env.example .env
# 编辑 .env 填入实际数据库信息

# S2 - 评估推理
cd ../assessment-reasoning-skill
cp .env.example .env
# 编辑 .env，单机测试设置 PINGGU_USE_DB=false

# S3 - 学习飞轮
cd ../learning-flywheel-skill
cp .env.example .env
# 编辑 .env 配置数据库连接
```

**2. 安装依赖**:
```bash
# S1 (Node.js)
cd .opencode/skills/search-history-cases-skill
npm install

# Python Skills (S5/S2/S6/S3/S4) - uv 自动管理
# uv 会自动创建虚拟环境并安装 requirements.txt 中的依赖
```

**3. 数据库扩展** (PostgreSQL 9.5+):
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

**4. Redis 配置 (S4)**:
```bash
# 启动 Redis
redis-server

# 验证连接
redis-cli ping  # 应返回 PONG
```

详细部署指南见：`.opencode/skills/DEPLOYMENT.md`

## 项目概述

智能评估 Agent 系统，将船舶服务需求邮件自动转换为结构化评估报告。

**核心流程**: 需求解析 (S5) → 历史检索 (S1) → 风险评估 (S2) → 报告生成 (S6) → 意图检测 (S4) → 学习飞轮 (S3)

## 快速命令

### S5 - 需求解析 (Python)
```bash
cd .opencode/skills/parse-requirement-skill
uv run python scripts/main.py --action parse \
  --input "主机异常振动" \
  --refs references/r2-enums.json --pretty
```

### S1 - 历史检索 (Node.js)
```bash
cd .opencode/skills/search-history-cases-skill
npm run search  # 使用预设输入
npm run search:engine  # 主机案例
npm run search:electrical  # 电气案例
```

### S2 - 评估推理 (Python)
```bash
cd .opencode/skills/assessment-reasoning-skill
# 使用文件输入（推荐）
uv run python scripts/main.py --action reason_assessment \
  --json-input-file samples/sample-input.json --refs-dir references --pretty
```

### S6 - 报告生成 (Python)
```bash
cd .opencode/skills/generate-report-skill
uv run python scripts/main.py --action generate_report \
  --json-input-file samples/sample-input.json --pretty
```

### S6 - 输出 Markdown 格式 (人类可读)
在输入 JSON 的 `options` 中设置 `"output_format": "markdown"` 即可输出 Markdown 格式报告。

### S4 - 意图检测 (Python)
```bash
cd .opencode/skills/s4-dialog-intent-detector
uv run python dialog_intent_detector.py "好的，确认"
```

### S3 - 学习飞轮 (Python)
```bash
cd .opencode/skills/learning-flywheel-skill
uv run python scripts/main.py --action learn_from_revision \
  --initial-draft samples/initial.md \
  --final-draft samples/final.md \
  --refs-dir references --pretty
```

### 运行单个测试
```bash
# S5 (Python) - 需求解析
cd .opencode/skills/parse-requirement-skill
uv run python scripts/main.py --action parse \
  --json-input-file samples/sample-input.json --refs references/r2-enums.json --pretty

# S1 (Node.js) - 历史检索
cd .opencode/skills/search-history-cases-skill && npm run search

# S2 (Python) - 评估推理
cd .opencode/skills/assessment-reasoning-skill
uv run python scripts/main.py --action reason_assessment \
  --json-input-file samples/sample-input.json --refs-dir references --pretty

# S6 (Python) - 报告生成
cd .opencode/skills/generate-report-skill && uv run python scripts/main.py \
  --action generate_report --json-input-file samples/sample-input.json --pretty

# S4 (Python) - 意图检测
cd .opencode/skills/s4-dialog-intent-detector
uv run python dialog_intent_detector.py "确认"

# S3 (Python) - 学习飞轮
cd .opencode/skills/learning-flywheel-skill
uv run python scripts/main.py --action learn_from_revision \
  --initial-draft samples/initial.md --final-draft samples/final.md \
  --refs-dir references --pretty
```

## 数据库配置

**PostgreSQL 9.5+** (需 pg_trgm 扩展):
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

**连接配置**: 编辑各 Skill 的 `.env` 文件（从 `.env.example` 复制）

| Skill | 配置项 | 说明 |
|-------|--------|------|
| S1 | `PGDATABASE=pinggu` | 数据库名 |
| S2 | `PINGGU_USE_DB=false` | 单机测试设为 false |
| S3 | `PGDATABASE=pinggu` | 学习资产存储 |

> ⚠️ **注意**: `.env` 文件已加入 `.gitignore`，不要提交到版本控制

## 代码风格规范

### Python 规范

**导入顺序**:
```python
# 1. 标准库 → 2. 第三方库 → 3. 本地模块
import argparse
import json
from typing import Any, Dict, List

import psycopg2

from db import ReferenceRepository
```

**类型注解** (必须):
```python
def parse_email(email_text: str, refs: Dict[str, Any]) -> Dict[str, Any]:
    """解析邮件为需求单"""
    ...
```

**命名约定**:
- 函数/变量：`snake_case` (`parse_email`, `risk_rules`)
- 类：`PascalCase` (`ReferenceRepository`)
- 常量：`UPPER_CASE` (`PINGGU_USE_DB`)
- 私有方法/变量：`_prefix` (`_internal_cache`)

**错误处理**:
```python
try:
    result = parse_email(email_text, refs)
    print(dump_json(ok(result), pretty=True))
except FileNotFoundError as e:
    print(dump_json(fail("FILE_NOT_FOUND", str(e)), pretty=True))
except Exception as e:
    print(dump_json(fail("UNEXPECTED_ERROR", str(e)), pretty=True))
```

**Docstring 规范**: 所有公共函数必须包含三引号 docstring

**文件保存**: 使用 `Write` 工具前必须先 `Read` 文件

**Windows 兼容性**:
```python
# Windows 编码修复 (main.py 开头)
if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", line_buffering=True
        )
```

### Node.js 规范

**ES Modules** (`.mjs`): 使用 `import/export` 语法，参数验证后执行数据库查询

**错误处理**: 捕获异常后输出 `{ success: false, error: { code, message } }`

### JSON 规范

- 缩进：2 空格 | 编码：UTF-8 | 键名：`snake_case`

**输出规范**:
- 所有 Skill 输出必须包含 `success`, `data`, `error` 字段
- 成功时 `data` 包含结果，`error` 为 `null`
- 失败时 `data` 为 `null`, `error` 包含 `code` 和 `message`
- 所有输出必须包含 `confidence` 字段
- **S6 报告生成默认输出 Markdown 格式**（人类可读），JSON 格式需显式指定 `"output_format": "json"`

## 测试检查清单
- [ ] 输出包含 `success: true/false`
- [ ] 错误包含 `code` 和 `message`
- [ ] 中文正常显示（无乱码）
- [ ] JSON 格式正确

## 注意事项

1. **环境配置**: 首次使用需复制 `.env.example` 为 `.env` 并配置数据库
2. **敏感信息**: `.env` 文件已加入 `.gitignore`，不要提交
3. **数据库**: S1/S2/S3 共用 PostgreSQL，不同表；数据库名默认为 `pinggu`
4. **运行模式**: 单机测试设置 `PINGGU_USE_DB=false`，多用户使用 `true`
5. **输出规范**: 所有输出必须包含 `success`, `data`, `error`, `confidence` 字段
6. **错误码**: 使用大写蛇形命名 (`FILE_NOT_FOUND`, `UNEXPECTED_ERROR`)
7. **编码**: Windows 用户如遇乱码，设置控制台为 UTF-8 (`chcp 65001`)
8. **包管理**: Python 使用 `uv`，Node.js 使用 `npm`
9. **S7 Skill**: 评审持久化功能，使用 PostgreSQL 存储评审结果
10. **S4 Skill**: 对话意图检测，使用 Redis 存储状态机
