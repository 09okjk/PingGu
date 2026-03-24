# AGENTS.md - 智能评估 Agent 开发指南

> 最后更新：2026-03-24 | 适用版本：S1/S2/S5

## 项目概述

智能评估 Agent 系统，将船舶服务需求邮件自动转换为结构化评估报告。

**核心流程**: 需求解析 (S5) → 历史检索 (S1) → 风险评估 (S2) → 报告生成

## 快速命令 (使用 uv 虚拟环境)

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

## 数据库配置

**PostgreSQL 9.5+** (需 pg_trgm 扩展):
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_task_description_trgm 
  ON evaluation_records USING gin (task_description gin_trgm_ops);
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

### Node.js 规范

**ES Modules** (`.mjs`):
```javascript
import pg from 'pg';

export async function searchHistoryCases(input) {
  if (!input.business_type) {
    throw new Error("business_type is required");
  }
  const { rows } = await pool.query(sql, [input.business_type]);
  return rows;
}
```

### JSON 规范

- 缩进：2 空格 | 编码：UTF-8 | 键名：`snake_case`
```json
{
  "success": true,
  "data": {
    "requirement_id": "req-001",
    "business_type": {"code": "BT0001", "name": "轮机"}
  },
  "error": null
}
```

## 测试指南

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
```

### 测试检查清单
- [ ] 输出包含 `success: true/false`
- [ ] 错误包含 `code` 和 `message`
- [ ] 中文正常显示（无乱码）
- [ ] JSON 格式正确

## 项目结构

```
PingGu/
├── .opencode/skills/
│   ├── parse-requirement-skill/     # S5
│   ├── search-history-cases-skill/  # S1
│   └── assessment-reasoning-skill/  # S2
├── 设计方案及规范/
└── AGENTS.md
```

## Skill 开发规范

**核心要求**:
1. **SKILL.md 必需** (含 frontmatter)
2. **name**: 小写连字符 (`parse-requirement-skill`)
3. **目录**: `scripts/` 代码，`references/` 配置
4. **环境变量**: 提供 `.env.example`
5. **Windows 兼容**: UTF-8 编码处理

## 常见问题

**Q: Windows 编码错误**  
A: S2 已修复，添加 UTF-8 包装器 (见 `main.py:6-9`)

**Q: 数据库连接失败**  
A: 检查 `.env` 配置，确认 PostgreSQL 服务运行

**Q: 字段为 null**  
A: 检查 `references/*.json` 枚举配置，添加别名

## 相关文档

- `.opencode/skills/*/SKILL.md` - Skill 使用说明
- `.opencode/skills/README.md` - Skills 总览
- `设计方案及规范/` - 详细设计文档

## 注意事项

1. 统一使用 uv 虚拟环境 (`uv run python ...`)
2. S1/S2 共用 PostgreSQL，不同表
3. 多用户同步使用 DB 模式 (`PINGGU_USE_DB=true`)
4. 输出必须包含 `confidence` 字段
5. 错误码使用大写蛇形 (`FILE_NOT_FOUND`)
