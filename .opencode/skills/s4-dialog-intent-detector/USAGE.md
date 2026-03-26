# 对话意图检测器 - 使用指南

## 📦 安装

无需额外依赖，使用 Python 标准库即可运行。

```bash
# 克隆或复制到项目目录
cd workspace-assessment/skills/dialog-intent-detector
```

## 🚀 快速开始

### 方式 1：独立使用意图检测器

```python
from dialog_intent_detector import DialogIntentDetector, DialogContext, DialogState

# 创建检测器
detector = DialogIntentDetector()

# 创建上下文
context = DialogContext(
    state=DialogState.REVIEW_IN_PROGRESS,
    has_revisions=True,
    edit_actions_count=3
)

# 检测意图
message = "好了"
result = detector.detect_intent(message, context)

print(f"意图：{result.intent.value}")
print(f"置信度：{result.confidence}")
print(f"解释：{result.explanation}")
print(f"建议动作：{result.suggested_action}")
```

### 方式 2：使用状态机（推荐）

```python
from review_state_machine import ReviewStateMachine

# 创建状态机
machine = ReviewStateMachine(
    task_id="TASK-2026-001",
    org_id="ORG-001",
    user_id="USER-工务 -001"
)

# 设置初稿报告
machine.set_initial_report({
    'risk_level': '中',
    'total_hours': 96,
    'total_persons': 3,
    'status': 'draft'
})

# 模拟对话
messages = [
    "风险等级调高一点",
    "工时也增加些",
    "再加 1 个人",
    "好了",
    "确认"
]

for msg in messages:
    print(f"用户：{msg}")
    response = machine.handle_user_message(msg)
    print(f"Agent: {response['message']}")
    print(f"状态：{machine.state.value}\n")
```

## 📊 意图类型说明

| 意图 | 说明 | 触发时机 | 下一步动作 |
|------|------|---------|-----------|
| `READY_TO_CONFIRM` | 首次确认 | 工务说"好了"且有修订历史 | 进入二次确认流程，展示修订摘要 |
| `CONFIRM` | 二次确认 | 工务说"确认"（在二次确认状态下） | 调用 S3 学习飞轮 |
| `MODIFY` | 继续修改 | 工务提出修改要求 | 调用 S6 修改报告 |
| `CANCEL` | 取消/反悔 | 工务说"取消"或"再想想" | 返回审核中状态 |
| `UNKNOWN` | 未知意图 | 未匹配任何模式 | 询问澄清 |

## 🔄 状态流转图

```
┌─────────────────────────────────────────────────────────────┐
│                    工务审核对话流程                          │
└─────────────────────────────────────────────────────────────┘

[S6 生成初稿]
    ↓
┌───────────────────────────────────────────────────┐
│ REVIEW_IN_PROGRESS（审核中）                       │
│                                                   │
│ 工务："风险等级调高一点" → MODIFY                 │
│ 工务："好了" → READY_TO_CONFIRM                   │
└───────────────────────────────────────────────────┘
    ↓ (READY_TO_CONFIRM)
┌───────────────────────────────────────────────────┐
│ CONFIRMATION_PENDING（二次确认中）                 │
│                                                   │
│ 展示修订摘要                                       │
│ 工务："确认" → CONFIRM                            │
│ 工务："取消" → CANCEL                             │
└───────────────────────────────────────────────────┘
    ↓ (CONFIRM)
┌───────────────────────────────────────────────────┐
│ LEARNING（学习中）                                 │
│                                                   │
│ 调用 S3 learn_from_revision                       │
└───────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────┐
│ COMPLETED（完成）                                  │
│                                                   │
│ 评估单交付服贸                                     │
└───────────────────────────────────────────────────┘
```

## 🧪 测试

### 运行意图检测器测试

```bash
cd skills/dialog-intent-detector
python dialog_intent_detector.py
```

### 运行状态机测试

```bash
cd skills/dialog-intent-detector
python review_state_machine.py
```

## 🔧 集成到现有系统

### 步骤 1：导入模块

```python
# 在你的对话处理逻辑中
from dialog_intent_detector import DialogIntentDetector, DialogContext, DialogState
from review_state_machine import ReviewStateMachine
```

### 步骤 2：初始化状态机

```python
# 在 S6 生成报告后
def after_report_generation(task_id, org_id, user_id, report):
    machine = ReviewStateMachine(task_id, org_id, user_id)
    machine.set_initial_report(report)
    return machine
```

### 步骤 3：处理用户消息

```python
# 在对话处理入口
def handle_dialog_message(machine: ReviewStateMachine, user_message: str):
    response = machine.handle_user_message(user_message)
    
    if response['status'] == 'modify':
        # 调用 S6 修改报告
        updated_report = call_s6_modify(user_message)
        machine.apply_edit(...)
        machine.current_report = updated_report
    
    elif response['status'] == 'confirmation_pending':
        # 展示修订摘要，等待二次确认
        send_message(response['message'])
    
    elif response['status'] == 'completed':
        # S3 学习完成，交付服贸
        deliver_to_sales(response['learning_result'])
    
    return response
```

### 步骤 4：调用 S3

```python
# 在状态机内部已自动构造 S3 输入
# 你只需要在实际调用时替换 TODO 部分

def call_s3_learning(s3_input: dict):
    # 调用 learning-flywheel-skill
    result = subprocess.run([
        'uv', 'run', 'python',
        'skills/learning-flywheel-skill/scripts/main.py',
        '--action', 'learn_from_revision',
        '--json-input', json.dumps(s3_input)
    ], capture_output=True, text=True)
    
    return json.loads(result.stdout)
```

## 📝 自定义配置

### 修改触发关键词

```python
detector = DialogIntentDetector()

# 添加自定义确认关键词
detector.confirm_patterns_high.extend([
    r'审核完毕',
    r'审核完成',
])

# 添加自定义修改关键词
detector.modify_patterns.extend([
    r'调整一下',
    r'优化',
])
```

### 调整置信度阈值

```python
result = detector.detect_intent(message, context)

if result.confidence < 0.7:
    # 低置信度时询问澄清
    ask_for_clarification()
else:
    # 高置信度时直接执行
    execute_action(result.intent)
```

## ⚠️ 注意事项

1. **S3 触发时机**：仅在二次确认后触发（`CONFIRM` 意图）
2. **无修订直接确认**：跳过二次确认，直接交付，不触发 S3
3. **状态持久化**：如需跨会话保持状态，请序列化 `ReviewStateMachine` 实例
4. **并发处理**：同一任务 ID 的状态机实例应保持唯一

## 📚 相关文档

- `README.md` - 本文件（使用指南）
- `dialog_intent_detector.py` - 意图检测器源码
- `review_state_machine.py` - 状态机源码
- `../S3-DIALOG-TRIGGER.md` - S3 对话触发设计文档
- `../learning-flywheel-skill/SKILL.md` - S3 学习飞轮技能说明

---

_丝滑但严谨，让学习成为审核流程的自然延伸。_
