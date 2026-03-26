# 对话意图检测器 - 集成指南

## 📋 概述

对话意图检测器已集成到主流程中，通过 `integration_main.py` 提供统一的入口。

## 🔧 使用方式

### 1. 命令行调用

```bash
# 处理用户消息
python integration_main.py --action process_message --message "风险等级调高一点" --task-id "TASK-001" --pretty

# 获取当前状态
python integration_main.py --action get_state --task-id "TASK-001" --pretty

# 重置状态
python integration_main.py --action reset_state --task-id "TASK-001" --pretty
```

### 2. JSON 输入（推荐用于 Agent 集成）

```bash
# 从文件读取
python integration_main.py --action process_message --json-input-file input.json --pretty

# 直接传 JSON 字符串
python integration_main.py --action process_message --json-input '{"message":"确认","task_id":"TASK-001"}' --pretty
```

### 3. Python 模块导入

```python
from integration_main import process_message, get_state, reset_state

# 处理消息
result = process_message(
    message="风险等级调高一点",
    task_id="TASK-001",
    org_id="org-123",
    user_id="user-456"
)

print(result["data"]["message"])
print(result["data"]["state"])
print(result["data"]["intent"])
```

## 📊 返回格式

### 成功响应

```json
{
  "success": true,
  "data": {
    "message": "收到修改请求：风险等级调高一点",
    "state": "REVIEW_IN_PROGRESS",
    "intent": "MODIFY",
    "confidence": 0.95,
    "action": null,
    "s3_input": null,
    "s3_input_constructed": false
  },
  "error": null
}
```

### 触发 S3 学习飞轮（确认时）

```json
{
  "success": true,
  "data": {
    "message": "[OK] 已确认最终稿...",
    "state": "COMPLETED",
    "intent": "CONFIRM",
    "confidence": 0.9,
    "action": null,
    "s3_input": {
      "context": { ... },
      "artifacts": { ... },
      "versions": { ... },
      "options": { ... }
    },
    "s3_input_constructed": false
  },
  "error": null
}
```

## 🔄 完整对话流程

```
用户：风险等级调高一点
→ intent: MODIFY
→ state: REVIEW_IN_PROGRESS
→ message: "收到修改请求：风险等级调高一点"

用户：工时也增加些
→ intent: MODIFY
→ state: REVIEW_IN_PROGRESS
→ message: "收到修改请求：工时也增加些"

用户：好了
→ intent: READY_TO_CONFIRM
→ state: CONFIRMATION_PENDING
→ message: "好的，这是修订摘要...请确认"

用户：确认
→ intent: CONFIRM
→ state: COMPLETED
→ message: "[OK] 已确认最终稿..."
→ s3_input: { ... }  ← 触发 S3 学习飞轮
```

## 🎯 状态说明

| 状态 | 说明 | 触发动作 |
|------|------|---------|
| `READY_FOR_REVIEW` | 初始状态，等待工务审核 | 无 |
| `REVIEW_IN_PROGRESS` | 工务正在修改评估单 | 调用 S6 修改报告 |
| `CONFIRMATION_PENDING` | 等待工务二次确认 | 展示修订摘要 |
| `COMPLETED` | 审核完成 | 调用 S3 学习飞轮 |

## 🧩 与 S3 学习飞轮集成

当工务说"确认"后，`s3_input` 字段会包含完整的 S3 输入数据结构。主流程可以：

1. 检查 `data.s3_input` 是否非空
2. 如果非空，调用 S3 学习飞轮：
   ```bash
   python scripts/main.py --action store --json-input <s3_input>
   ```
3. 将 S3 执行结果返回给用户

## 📝 注意事项

1. **状态持久化**：当前状态保存在内存中，重启后重置。生产环境需实现状态持久化。
2. **任务隔离**：每个 `task_id` 有独立的状态机实例。
3. **编码兼容**：Windows 环境下已处理 UTF-8 编码问题。
4. **S3 触发时机**：仅在工务二次确认后触发，修改过程中不触发。

## 🚀 下一步

1. 实现状态持久化（Redis/数据库）
2. 添加更多意图类型（如 CANCEL、ASK_QUESTION）
3. 集成到主 Agent 流程中
4. 添加单元测试和集成测试
