# AGENTS.md - 智能评估 Agent 开发指南

> 最后更新：2026-03-27 | 版本：S1-S7

## 项目结构

```
.opencode/skills/
├── parse-requirement-skill/    # S5 - 需求解析 (Python)
├── search-history-cases-skill/ # S1 - 历史检索 (Node.js)
├── assessment-reasoning-skill/ # S2 - 评估推理 (Python)
├── generate-report-skill/      # S6 - 报告生成 (Python)
├── s4-dialog-intent-detector/  # S4 - 意图检测 (Python)
├── learning-flywheel-skill/    # S3 - 学习飞轮 (Python)
└── s7-review-persistence-skill/# S7 - 评审持久化 (Python)
```

## 快速开始

**1. 安装依赖**:
```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows (uv)
curl -LsSf https://astral.sh/uv/install.sh | sh             # Linux/macOS
```

**2. 配置环境变量**:
```bash
cd .opencode/skills
cp search-history-cases-skill/.env.example search-history-cases-skill/.env
# 编辑 .env: PGHOST, PGUSER, PGPASSWORD, PGDATABASE
```

**3. 数据库配置** (PostgreSQL 9.5+):
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

**4. Redis** (S4/S7):
```bash
redis-server && redis-cli ping  # 应返回 PONG
```

## 运行单个测试（核心命令）

| Skill | 命令 |
|-------|------|
| **S5 需求解析** | `uv run python scripts/main.py --action parse --input "主机异常振动" --pretty` |
| **S1 历史检索** | `npm install && npm run search` (或 `search:engine`) |
| **S2 评估推理** | `uv run python scripts/main.py --action reason_assessment --json-input-file samples/sample-input.json --pretty` |
| **S6 报告生成** | `uv run python scripts/main.py --action generate_report --json-input-file samples/sample-input.json --pretty` |
| **S4 意图检测** | `uv run python dialog_intent_detector.py "确认"` |
| **S3 学习飞轮** | `uv run python scripts/main.py --action learn_from_revision --initial-draft samples/initial.md --final-draft samples/final.md --pretty` |
| **S7 评审持久化** | `uv run python -m scripts.main status` |

*注：所有命令需先进入对应 skill 目录 (如 `cd .opencode/skills/parse-requirement-skill`)*

## 代码风格规范

### Python 规范

**导入顺序** (必须遵守):
```python
# 1. 标准库 → 2. 第三方库 → 3. 本地模块
import argparse
import psycopg2
from db import ReferenceRepository
```

**类型注解** (强制要求):
```python
def parse_email(email_text: str, refs: Dict[str, Any]) -> Dict[str, Any]:
    """解析邮件为需求单"""
    ...
```

**命名约定**:
- 函数/变量：`snake_case` | 类：`PascalCase` | 常量：`UPPER_CASE` | 私有：`_prefix`

**错误处理**:
```python
try:
    result = parse_email(email_text, refs)
except FileNotFoundError as e:
    print(dump_json(fail("FILE_NOT_FOUND", str(e)), pretty=True))
```

**Docstring**: 所有公共函数必须包含三引号 docstring

**Windows 兼容性**:
```python
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
```

### Node.js 规范

**ES Modules** (`.mjs`): 使用 `import/export` 语法，参数验证后执行数据库查询

**错误处理**: 输出 `{ success: false, error: { code, message } }`

### JSON 输出规范

- 缩进：2 空格 | 编码：UTF-8 | 键名：`snake_case`
- 必须包含：`success`, `data`, `error`, `confidence`
- 成功：`data` 含结果，`error` 为 `null`；失败：`data` 为 `null`, `error` 含 `code` 和 `message`
- S6 默认输出 Markdown，JSON 需指定 `"output_format": "json"`

### 错误码规范

大写蛇形命名：`FILE_NOT_FOUND`, `UNEXPECTED_ERROR`, `DB_CONNECTION_FAILED`

## 测试检查清单

- [ ] 输出包含 `success: true/false`
- [ ] 错误包含 `code` 和 `message`
- [ ] 中文正常显示（无乱码）
- [ ] JSON 格式正确
- [ ] 类型注解完整

## 注意事项

1. **.env 文件**: 已加入 `.gitignore`，不要提交
2. **数据库**: S1/S2/S3/S6/S7 共用 PostgreSQL，不同表
3. **运行模式**: `PINGGU_USE_DB=false` 单机测试，`true` 多用户
4. **编码**: Windows 乱码时执行 `chcp 65001`
5. **包管理**: Python 用 `uv run`，Node.js 用 `npm`
6. **文件操作**: 使用 `Write` 工具前必须先 `Read`

## 核心流程

需求解析 (S5) → 历史检索 (S1) → 风险评估 (S2) → 报告生成 (S6) → 意图检测 (S4) → 学习飞轮 (S3)
