# AGENTS.md - 智能评估 Agent 开发指南

> 最后更新：2026-03-25 | 适用版本：S1/S2/S5/S6

## 项目概述

智能评估 Agent 系统，将船舶服务需求邮件自动转换为结构化评估报告。

**核心流程**: 需求解析 (S5) → 历史检索 (S1) → 风险评估 (S2) → 报告生成 (S6)

## 快速命令

### S5 - 需求解析 (Python)
```bash
uv run python .opencode/skills/parse-requirement-skill/scripts/main.py \
  --action parse --input "主机异常振动" \
  --refs .opencode/skills/parse-requirement-skill/references/r2-sample-enums.json --pretty
```

### S1 - 历史检索 (Node.js)
```bash
cd .opencode/skills/search-history-cases-skill
npm install && cp .env.example .env  # 首次配置
npm run search  # 测试
```

### S2 - 评估推理 (Python)
```bash
cd .opencode/skills/assessment-reasoning-skill
uv pip install psycopg2-binary  # DB 模式需要
uv run python scripts/main.py --action reason_assessment \
  --json-input samples/sample-input.json --refs-dir references --pretty
```

### S6 - 报告生成 (Python)
```bash
cd .opencode/skills/generate-report-skill
uv run python scripts/main.py --action generate_report \
  --json-input-file samples/sample-input.json --pretty
```

### S6 - 输出 Markdown 格式 (人类可读)
```bash
cd .opencode/skills/generate-report-skill
uv run python scripts/main.py --action generate_report \
  --json-input-file samples/sample-input.json
```
在输入 JSON 的 `options` 中设置 `"output_format": "markdown"` 即可输出 Markdown 格式报告。

### 运行单个测试
```bash
# S5 (Python)
uv run python .opencode/skills/parse-requirement-skill/scripts/main.py \
  --action parse --json-input samples/sample-input.json \
  --refs references/r2-sample-enums.json --pretty

# S1 (Node.js)
cd .opencode/skills/search-history-cases-skill && npm run search

# S2 (Python)
uv run python .opencode/skills/assessment-reasoning-skill/scripts/main.py \
  --action reason_assessment --json-input samples/sample-input.json \
  --refs-dir references --pretty

# S6 (Python)
cd .opencode/skills/generate-report-skill && uv run python scripts/main.py \
  --action generate_report --json-input-file samples/sample-input.json --pretty
```

## 数据库配置

**PostgreSQL 9.5+** (需 pg_trgm 扩展):
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

**连接配置**: 编辑各 Skill 的 `.env` 文件
- S1: `PGHOST=192.168.124.126`, `PGDATABASE=pinggu`
- S2: `PINGGU_USE_DB=true`, `PINGGU_DB_HOST=192.168.124.126`

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

1. 统一使用 uv 虚拟环境 (`uv run python ...`)
2. S1/S2 共用 PostgreSQL，不同表
3. 多用户同步使用 DB 模式 (`PINGGU_USE_DB=true`)
4. 输出必须包含 `confidence` 字段
5. 错误码使用大写蛇形 (`FILE_NOT_FOUND`)
