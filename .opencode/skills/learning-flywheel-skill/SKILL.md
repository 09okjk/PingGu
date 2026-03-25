---
name: learning-flywheel-skill
slug: learning-flywheel-skill
version: 1.1.0
author: "09okjk"
description: 从评估初稿到人工终稿的修订过程中提取差异、归因标签、学习样本、候选规则与输出偏好，并可写入 PostgreSQL。
changelog: |
  ## [1.1.0] - 数据库接入版
  - 新增 PostgreSQL 存储支持
  - 新增 learning_* 表写入逻辑
  - 新增 learning-tables.sql 建表脚本
  - 保留本地文件存储能力作为开发调试补充
metadata:
  clawdbot:
    emoji: 🔄
    requires:
      bins: ["python3"]
      env: ["LOG_LEVEL", "S3_ENABLE_DB", "S3_DB_HOST"]
    os: ["linux", "darwin", "win32"]
---

# LearningFlywheelSkill

S3 学习飞轮 Skill，用于在“初稿 → 人工修订 → 最终确认”完成后，自动提取差异、分析修订原因，并沉淀未来可复用的学习资产。

## When to Use

✅ 适用场景：

- 已存在评估初稿与最终确认稿，想提取修订差异时
- 需要分析人工为什么修改报告时
- 需要把修订过程转成学习样本、规则候选、偏好候选时
- 需要将学习结果写入 PostgreSQL 时
- 需要为后续 S1 / S2 / S6 提供可复用经验时

## When NOT to Use

❌ 不适用场景：

- 还没有最终确认稿时
- 想直接生成评估报告时（请使用 `generate-report-skill`）
- 想做风险 / 工时 / 人数推理时（请使用 `assessment-reasoning-skill`）
- 想解析原始需求邮件时（请使用 `parse-requirement-skill`）

## Setup

### 快速测试（不写数据库）

```bash
cd {baseDir}

uv run python scripts/main.py --action learn_from_revision \
  --json-input-file samples/sample-input.json \
  --pretty
```

### PostgreSQL 模式测试

先安装依赖：

```bash
uv pip install psycopg2-binary python-dotenv
```

配置环境变量：

```bash
cp .env.example .env
```

编辑 `.env` 后运行：

```bash
uv run python scripts/main.py --action learn_from_revision \
  --json-input-file samples/sample-input.json \
  --pretty
```

### Windows 兼容性说明

本 Skill 包含 Windows UTF-8 输出兼容处理，可直接运行：

```powershell
uv run python scripts/main.py --action learn_from_revision `
  --json-input-file samples/sample-input.json `
  --pretty
```

如遇编码问题，可设置：

```powershell
$env:PYTHONUTF8=1
uv run python scripts/main.py --action learn_from_revision `
  --json-input-file samples/sample-input.json `
  --pretty
```

## 故障排查

### 数据库连接失败

检查 `.env` 配置：
```bash
S3_ENABLE_DB=true
S3_DB_HOST=192.168.124.126
S3_DB_PORT=5432
S3_DB_NAME=pinggu
S3_DB_USER=postgres
S3_DB_PASSWORD=your_password
```

### 唯一约束冲突

重复运行测试时可能报错 `duplicate key violates unique constraint`，清理测试数据：

```sql
DELETE FROM learning_report_preferences WHERE preference_id LIKE 'PF-%';
DELETE FROM learning_rule_candidates WHERE candidate_rule_id LIKE 'CR-%';
DELETE FROM learning_samples WHERE sample_id LIKE 'LF-%';
DELETE FROM learning_feedback_tags;
DELETE FROM learning_revision_records;
```

### 表不存在

执行建表脚本：
```bash
psql -h <host> -U <user> -d pinggu -f samples/learning-tables.sql
```

### 缺少 python-dotenv

报错 `ModuleNotFoundError: No module named 'dotenv'` 时：
```bash
uv pip install python-dotenv
```

## Options

### 通用选项

| 选项 | 说明 | 必需 |
|------|------|------|
| `--action` | 当前仅支持 `learn_from_revision` | ✅ |
| `--json-input` | 直接传 JSON 字符串 | ❌ |
| `--json-input-file` | 从文件读取 JSON 输入 | ❌ |
| `--pretty` | 格式化输出 JSON | ❌ |

## Core Rules

1. 不直接修改当前评估结论
2. 输出必须包含 `success`, `data`, `error`
3. 候选知识与已生效知识必须分离
4. 无 `edit_actions` 时，也必须支持从初稿与终稿中提取 diff
5. 所有输出尽量结构化，便于存储和后续统计
6. 所有学习输出都应可追溯到 `task_id` / `versions`
7. 单次修订默认只产生候选资产，不直接生效
8. `confidence` 字段必须保留在核心输出对象中
9. PostgreSQL 存储为可选能力，不应阻塞本地调试

## Output Contract

统一输出：

```json
{
  "success": true,
  "data": {
    "revision_diff": [],
    "feedback_tags": [],
    "learning_sample": {},
    "rule_candidates": [],
    "report_preference_candidates": [],
    "next_step_actions": []
  },
  "error": null
}
```

## Security & Privacy

- 默认本地运行，不主动联网
- 数据库写入为可选
- 建议由上层系统控制长期存储与脱敏
- 建议对 `user_id`、对话日志等敏感字段做脱敏后再进入长期存储

### 环境变量

```bash
LOG_LEVEL=INFO

# 可选：本地文件存储
S3_ENABLE_FILE_STORAGE=false
S3_STORAGE_DIR=./runtime-data

# 可选：PostgreSQL 存储
S3_ENABLE_DB=false
S3_DB_HOST=127.0.0.1
S3_DB_PORT=5432
S3_DB_NAME=pinggu
S3_DB_USER=postgres
S3_DB_PASSWORD=
S3_DB_SSLMODE=disable
```

## Related Skills

- `parse-requirement-skill`: 需求解析
- `search-history-cases-skill`: 历史案例检索
- `assessment-reasoning-skill`: 评估推理
- `generate-report-skill`: 报告合成