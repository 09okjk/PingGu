---
name: parse-requirement-skill
slug: parse-requirement-skill
version: 2.0.0
description: 将自然语言邮件解析为一个或多个标准化服务需求项，并通过 parse / revise / confirm 三阶段交互闭环完成需求确认。
changelog: |
  ## [2.0.0] - 交互闭环版
  - 新增 parse / revise / confirm 三阶段支持
  - 新增 session_id 和 revision_history 支持
  - 新增 next_questions 自动生成
  - 支持多服务项拆分
  ## [1.0.0] - 初始版本
  - 基础解析功能
metadata:
  clawdbot:
    emoji: 🧩
    requires:
      bins: ["python3"]
      env: []
    os: ["linux", "darwin", "win32"]
---

# ParseRequirementSkill

这是一个面向智能评估 Agent 的前置 Skill，用于把用户原始自然语言邮件解析、拆分并逐步确认成标准化需求单。

支持三个阶段：

- `parse`：初始解析，输出需求项草稿
- `revise`：根据用户反馈修改草稿
- `confirm`：确认最终需求单，结束交互

---

## When to Use

✅ 适用于：

- 输入是自然语言邮件，而不是标准表单
- 一封邮件可能包含多个服务项
- 需要在进入历史案例检索前先标准化输入
- 需要通过交互确认逐步修正需求单
- 希望记录用户修订轨迹，为后续飞轮优化提供数据

---

## When NOT to Use

❌ 不适用于：

- 输入已经是标准化且已确认的需求单
- 只做历史检索，不做需求解析
- 只做文本翻译
- 只做最终报告生成

---

## Setup

### 基础用法

```bash
# 从 JSON 文件读取输入
python3 {baseDir}/scripts/main.py \
  --action parse \
  --json-input-file "{baseDir}/samples/sample-input.json" \
  --refs "{baseDir}/references/r2-sample-enums.json" \
  --pretty
```

### 快速测试（4 种方式）

**方式 1: 命令行直接输入文本**
```bash
python3 scripts/main.py --action parse \
  --input "The main engine shows abnormal vibration" \
  --refs references/r2-sample-enums.json \
  --pretty
```

**方式 2: 从文件读取文本**
```bash
python3 scripts/main.py --action parse \
  --input-file sample-email.txt \
  --refs references/r2-sample-enums.json \
  --pretty
```

**方式 3: JSON payload（命令行）**
```bash
python3 scripts/main.py --action parse \
  --json-input '{"email_text": "Engine needs inspection"}' \
  --refs references/r2-sample-enums.json \
  --pretty
```

**方式 4: JSON payload（文件）**
```bash
python3 scripts/main.py --action parse \
  --json-input-file samples/sample-input.json \
  --refs references/r2-sample-enums.json \
  --pretty
```

### 修订和确认

**修订阶段**:
```bash
python3 scripts/main.py --action revise \
  --json-input '{"session_id": "sess-xxx", "current_requirements": [...], "user_feedback": "改成维修"}' \
  --refs references/r2-sample-enums.json \
  --pretty
```

**确认阶段**:
```bash
python3 scripts/main.py --action confirm \
  --json-input '{"session_id": "sess-xxx", "current_requirements": [...]}' \
  --refs references/r2-sample-enums.json \
  --pretty
```

---

## Options

### 通用选项

| 选项 | 说明 | parse | revise | confirm |
|------|------|-------|--------|---------|
| `--action` | 指定执行阶段 | ✅ | ✅ | ✅ |
| `--refs` | R2 参考文件路径 | ✅ | ✅ | ✅ |
| `--pretty` | 格式化输出 JSON | ✅ | ✅ | ✅ |
| `--lang` | 强制指定语言 | ✅ | ❌ | ❌ |
| `--strict` | 严格模式 | ✅ | ❌ | ❌ |

### 输入选项（互斥）

| 选项 | 说明 | parse | revise | confirm |
|------|------|-------|--------|---------|
| `--input` | 原始文本输入 | ✅ | ❌ | ❌ |
| `--input-file` | 从文件读取原始文本 | ✅ | ❌ | ❌ |
| `--json-input` | 直接传 JSON 输入 | ✅ | ✅ | ✅ |
| `--json-input-file` | 从文件读取 JSON 输入 | ✅ | ✅ | ✅ |

### 各阶段推荐用法

**parse 阶段**（4 种方式）:
```bash
# 方式 1: 命令行直接输入
python3 scripts/main.py --action parse --input "邮件文本" --refs references/r2-sample-enums.json

# 方式 2: 从文件读取文本
python3 scripts/main.py --action parse --input-file sample-email.txt --refs references/r2-sample-enums.json

# 方式 3: JSON payload（命令行）
python3 scripts/main.py --action parse --json-input '{"email_text": "..."}' --refs references/r2-sample-enums.json

# 方式 4: JSON payload（文件）
python3 scripts/main.py --action parse --json-input-file samples/sample-input.json --refs references/r2-sample-enums.json
```

**revise/confirm 阶段**（2 种方式，必须使用 JSON）:
```bash
# 方式 1: JSON payload（命令行）
python3 scripts/main.py --action revise --json-input '{"session_id": "...", ...}' --refs references/r2-sample-enums.json

# 方式 2: JSON payload（文件）
python3 scripts/main.py --action revise --json-input-file samples/sample-revise-input.json --refs references/r2-sample-enums.json
```

---

## Core Rules

1. 不得臆造用户未提供的信息
2. 必须支持一封邮件拆分多个服务项
3. 每个需求项必须保留原文证据
4. 允许字段为空，允许输出歧义候选
5. 若用户尚未确认，应继续输出 `next_questions`
6. 只有 `confirm` 阶段明确确认后，状态才变为 `confirmed`
7. 所有用户修订应被记录在 `revision_history` 中
8. 当前版本不解析附件内容，但保留 `attachments` 扩展位

---

## Output Contract

统一输出：

```json
{
  "success": true,
  "data": {
    "session_id": "xxx",
    "status": "needs_confirmation",
    "action": "parse",
    "requirements": [],
    "next_questions": [],
    "revision_history": []
  },
  "error": null
}
```

状态包括：

- `draft`
- `needs_confirmation`
- `confirmed`

---

## Security & Privacy

- 默认本地处理，不主动联网
- 附件暂不解析
- 建议生产环境中由上层 Agent 统一接管模型调用、日志与脱敏

### 环境变量

当前版本不强依赖环境变量，但预留以下配置：

```bash
# .env.example
OPENAI_API_KEY=     # 接入 LLM 时使用
MODEL_NAME=         # 指定模型名称
LOG_LEVEL=INFO      # 日志级别
```

详见 `.env.example` 和 `references/config.md`。

## Troubleshooting（常见问题）

### 1. 错误：`FILE_NOT_FOUND`

**原因**: 输入文件路径不正确

**解决方法**:
```bash
# 使用绝对路径
python3 scripts/main.py --action parse \
  --input-file "/absolute/path/to/email.txt" \
  --refs references/r2-sample-enums.json

# 或使用相对路径（从 skill 目录出发）
cd .opencode/skills/parse-requirement-skill
python3 scripts/main.py --action parse \
  --input-file samples/sample-email.txt \
  --refs references/r2-sample-enums.json
```

### 2. 错误：`INVALID_JSON`

**原因**: JSON 文件格式不正确

**解决方法**:
- 检查 JSON 语法（使用 `jq . input.json` 或在线工具）
- 确保使用 UTF-8 编码保存文件
- 检查是否有 trailing comma

### 3. 解析结果为空或字段为 null

**原因**: 参考枚举文件中没有匹配的条目

**解决方法**:
- 检查 `references/r2-sample-enums.json` 中的枚举定义
- 在 `service_desc_enum`、`service_type_enum`、`equipment_name_enum` 中添加相关别名
- 使用 `--strict` 模式查看置信度

**示例：添加新枚举**
```json
{
  "service_desc_enum": [
    {
      "code": "SD006",
      "name": "火灾报警系统",
      "aliases": ["fire alarm", "consilium", "alarm system", "火灾报警"]
    }
  ]
}
```

### 4. 识别出多个服务项但实际只有一个

**原因**: 文本中包含多个动作或设备关键词

**解决方法**:
- 在 revise 阶段合并服务项
- 调整 `split_keywords` 配置
- 简化邮件描述，分段发送

### 5. 语言检测错误

**原因**: 多语言混合内容

**解决方法**:
```bash
# 强制指定语言
python3 scripts/main.py --action parse \
  --input "邮件文本" \
  --refs references/r2-sample-enums.json \
  --lang en \
  --pretty
```

## Related Skills

- `SearchHistoryCasesSkill`
- `MatchRisksSkill`
- `GenerateReportSkill`