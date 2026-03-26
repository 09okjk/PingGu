---
name: S4 - Dialog Intent Detector
slug: s4-dialog-intent-detector
version: 1.1.0
description: 识别工务审核对话中的意图（修改/确认/取消），管理审核状态机，触发 S3 学习飞轮，支持 Redis 状态持久化。
changelog: |
  ## [1.1.0] - 状态持久化
  - ✅ 集成 review-persistence-skill 实现 Redis 持久化
  - ✅ 支持进程重启后自动恢复审核状态
  - ✅ TTL 1 小时自动过期清理
  - ✅ 每次交互后自动保存状态
  
  ## [1.0.0] - 初始版本
  - 4 种意图识别（MODIFY / READY_TO_CONFIRM / CONFIRM / CANCEL）
  - 4 状态流转管理（REVIEW_IN_PROGRESS → CONFIRMATION_PENDING → COMPLETED）
  - S3 学习飞轮触发逻辑
  - 工务审核对话流程集成
metadata:
  clawdbot:
    emoji: 🧠
    requires:
      bins: ["python3"]
      env: []
    os: ["linux", "darwin", "win32"]
---

# DialogIntentDetector - 对话意图检测器

这是一个面向智能评估 Agent 的对话管理 Skill，用于识别工务审核对话中的意图，管理审核状态机，并在二次确认后自动触发 S3 学习飞轮。

支持三种操作：

- `process_message`：处理用户消息，返回意图识别结果和状态更新
- `get_state`：获取当前任务状态
- `reset_state`：重置任务状态

---

## When to Use

✅ 适用于：

- 工务人员审核评估单时的对话交互
- 需要识别"修改"/"确认"/"取消"等意图
- 需要管理审核状态流转（审核中 → 二次确认 → 完成）
- 需要在二次确认后自动触发 S3 学习飞轮
- 需要记录修订历史用于模型优化

---

## When NOT to Use

❌ 不适用于：

- 需求解析阶段（使用 `parse-requirement-skill`）
- 历史案例检索（使用 `search-history-cases-skill`）
- 评估报告生成（使用 `generate-report-skill`）
- 非工务审核场景的对话

---

## Setup

### 基础用法

```bash
# 处理工务消息
python3 {baseDir}/scripts/main.py \
  --action process_message \
  --message "风险等级调高一点" \
  --task-id "TASK-2026-001" \
  --pretty
```

### 快速测试（4 种方式）

**方式 1: 命令行直接输入**
```bash
python3 scripts/main.py --action process_message \
  --message "风险等级调高一点" \
  --task-id "TASK-001" \
  --pretty
```

**方式 2: JSON payload（命令行）**
```bash
python3 scripts/main.py --action process_message \
  --json-input '{"message":"确认","task_id":"TASK-001"}' \
  --pretty
```

**方式 3: JSON payload（文件）**
```bash
python3 scripts/main.py --action process_message \
  --json-input-file samples/sample-message.json \
  --pretty
```

**方式 4: 获取/重置状态**
```bash
# 获取当前状态
python3 scripts/main.py --action get_state --task-id "TASK-001" --pretty

# 重置状态
python3 scripts/main.py --action reset_state --task-id "TASK-001" --pretty
```

---

## Options

### 通用选项

| 选项 | 说明 | process_message | get_state | reset_state |
|------|------|-----------------|-----------|-------------|
| `--action` | 指定操作类型 | ✅ | ✅ | ✅ |
| `--task-id` | 任务 ID | ✅ | ✅ | ✅ |
| `--pretty` | 格式化输出 JSON | ✅ | ✅ | ✅ |

### process_message 选项

| 选项 | 说明 | 必需 |
|------|------|------|
| `--message` | 用户消息内容 | ✅（或与 JSON 输入二选一） |
| `--json-input` | JSON payload 字符串 | ✅（或与 message 二选一） |
| `--json-input-file` | 从文件读取 JSON payload | ✅（或与 message 二选一） |
| `--state` | 当前状态（可选，默认从状态机读取） | ❌ |

### JSON Payload 格式

**process_message 输入**:
```json
{
  "message": "风险等级调高一点",
  "task_id": "TASK-2026-001",
  "org_id": "ORG-001",
  "user_id": "USER-工务 -001",
  "state": "REVIEW_IN_PROGRESS"
}
```

**get_state/reset_state 输入**:
```json
{
  "task_id": "TASK-2026-001",
  "org_id": "ORG-001",
  "user_id": "USER-工务 -001"
}
```

---

## Core Rules

1. 每个 `task_id` 有独立的状态机实例
2. 状态流转必须遵循：REVIEW_IN_PROGRESS → CONFIRMATION_PENDING → COMPLETED
3. S3 学习飞轮仅在二次确认（CONFIRM 意图）后触发
4. 无修订直接确认时，跳过二次确认，不触发 S3
5. 意图识别置信度低于 0.7 时应询问澄清
6. 所有修订应记录到 modification_history
7. ✅ **状态持久化**: 每次交互后自动保存到 Redis（TTL 1 小时）
8. ✅ **自动恢复**: 进程重启后自动从 Redis 恢复审核状态
9. ✅ **流程清理**: 审核完成后自动删除 Redis 中的状态

---

## Output Contract

统一输出：

```json
{
  "success": true,
  "data": {
    "message": "收到修改请求：风险等级调高一点",
    "state": "REVIEW_IN_PROGRESS",
    "intent": "MODIFY",
    "confidence": 0.95,
    "action": "call_s6_modify",
    "s3_input": null,
    "s3_input_constructed": false
  },
  "error": null
}
```

### 意图类型

| 意图 | 说明 | 触发动作 |
|------|------|---------|
| `MODIFY` | 继续修改 | 调用 S6 修改报告 |
| `READY_TO_CONFIRM` | 首次确认 | 进入二次确认流程，展示修订摘要 |
| `CONFIRM` | 二次确认 | 调用 S3 学习飞轮 |
| `CANCEL` | 取消/反悔 | 返回审核中状态 |
| `UNKNOWN` | 未知意图 | 询问澄清 |

### 状态说明

| 状态 | 说明 | 触发动作 |
|------|------|---------|
| `REVIEW_IN_PROGRESS` | 工务正在修改评估单 | 调用 S6 修改报告 |
| `CONFIRMATION_PENDING` | 等待工务二次确认 | 展示修订摘要 |
| `COMPLETED` | 审核完成 | 调用 S3 学习飞轮 |

### 触发 S3 学习飞轮（确认时）

```json
{
  "success": true,
  "data": {
    "message": "[OK] 已确认最终稿...",
    "state": "COMPLETED",
    "intent": "CONFIRM",
    "confidence": 0.9,
    "action": "call_s3",
    "s3_input": {
      "context": { "task_id": "TASK-001", ... },
      "artifacts": { "draft": {...}, "final": {...} },
      "versions": { "v1": {...}, "v2": {...} },
      "options": { "risk_level": "高", ... }
    },
    "s3_input_constructed": false
  },
  "error": null
}
```

---

## 完整对话流程

```
[S6 生成初稿]
    ↓
┌───────────────────────────────────────────────────┐
│ REVIEW_IN_PROGRESS（审核中）                       │
│                                                   │
│ 工务："风险等级调高一点" → MODIFY                 │
│ 工务："工时也增加些" → MODIFY                     │
│ 工务："好了" → READY_TO_CONFIRM                   │
└───────────────────────────────────────────────────┘
    ↓ (READY_TO_CONFIRM)
┌───────────────────────────────────────────────────┐
│ CONFIRMATION_PENDING（二次确认中）                 │
│                                                   │
│ Agent 展示修订摘要                                  │
│ 工务："确认" → CONFIRM                            │
│ 工务："取消" → CANCEL                             │
└───────────────────────────────────────────────────┘
    ↓ (CONFIRM)
┌───────────────────────────────────────────────────┐
│ COMPLETED（完成）                                  │
│                                                   │
│ 调用 S3 学习飞轮                                   │
│ 评估单交付服贸                                     │
└───────────────────────────────────────────────────┘
```

---

## 与 S3 学习飞轮集成

当工务说"确认"后，`s3_input` 字段会包含完整的 S3 输入数据结构。主流程可以：

1. 检查 `data.s3_input` 是否非空
2. 如果非空，调用 S3 学习飞轮：
   ```bash
   python3 {baseDir}/../learning-flywheel-skill/scripts/main.py \
     --action learn_from_revision \
     --json-input '<s3_input>'
   ```
3. 将 S3 执行结果返回给用户

---

## 集成到现有系统

### 步骤 1：在 S6 生成报告后初始化状态机

```python
# 在你的主流程中
def after_report_generation(task_id, org_id, user_id, report):
    # 初始化状态机（状态会自动保存）
    state_machine = ReviewStateMachine(task_id, org_id, user_id)
    state_machine.set_initial_report(report)
    return state_machine
```

### 步骤 2：处理用户消息

```python
def handle_dialog_message(task_id, user_message):
    result = subprocess.run([
        'python3', 'scripts/main.py',
        '--action', 'process_message',
        '--message', user_message,
        '--task-id', task_id,
        '--json-output'
    ], capture_output=True, text=True)
    
    response = json.loads(result.stdout)
    
    if response['data']['action'] == 'call_s6_modify':
        # 调用 S6 修改报告
        updated_report = call_s6_modify(user_message)
    
    elif response['data']['action'] == 'call_s3':
        # 调用 S3 学习飞轮
        s3_result = call_s3_learning(response['data']['s3_input'])
    
    return response
```

---

## Security & Privacy

- 默认本地处理，不主动联网
- 状态数据保存在内存中（生产环境建议持久化到 Redis/数据库）
- 建议生产环境中由上层 Agent 统一接管模型调用、日志与脱敏

### 环境变量

当前版本使用 Redis 持久化状态，需配置以下环境变量：

```bash
# .env.example
LOG_LEVEL=INFO              # 日志级别
REDIS_HOST=localhost        # Redis 服务器地址
REDIS_PORT=6379            # Redis 端口
REDIS_DB=0                 # Redis 数据库编号
REDIS_PASSWORD=            # Redis 密码（可选）
STATE_TTL=3600             # 状态 TTL（秒），默认 1 小时
```

### Redis 连接测试

```bash
# 测试 Redis 连接
python3 scripts/main.py --action test_connection --pretty
```

---

## Troubleshooting（常见问题）

### 1. 错误：`INVALID_STATE`

**原因**: 状态机未初始化或状态无效

**解决方法**:
```bash
# 先重置状态
python3 scripts/main.py --action reset_state --task-id "TASK-001" --pretty

# 或确保在 S6 生成报告后先初始化状态机
```

### 2. 错误：`S3_INPUT_NOT_CONSTRUCTED`

**原因**: 未达到触发 S3 的条件（无修订直接确认）

**解决方法**:
- 检查是否有修订历史（modification_count > 0）
- 无修订时跳过 S3，直接交付服贸

### 3. 意图识别置信度低

**原因**: 用户消息未匹配任何已知模式

**解决方法**:
```python
if result['data']['confidence'] < 0.7:
    # 询问澄清
    ask_for_clarification(result['data']['intent'])
```

### 4. 状态丢失（重启后）

**原因**: 当前状态保存在内存中

**解决方法**:
- 生产环境实现状态持久化（Redis/数据库）
- 或在会话开始时重新初始化状态机

---

## Related Skills

- `learning-flywheel-skill` - S3 学习飞轮（从修订中学习）
- `generate-report-skill` - S6 生成评估报告
- `parse-requirement-skill` - 需求解析
- `search-history-cases-skill` - 历史案例检索

---

_丝滑但严谨，让学习成为审核流程的自然延伸。_
