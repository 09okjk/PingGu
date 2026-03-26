# S4 - DialogIntentDetector 详细设计

> 创建日期：2026-03-25  
> 最后修改：2026-03-26  
> 状态：设计确认（v1.1.0 状态持久化版）  
> 所属模块：智能评估 Agent — Skills 层

---

## 目录

1. [Skill 定位与职责](#一skill-定位与职责)
2. [为什么需要独立的对话意图检测层](#二为什么需要独立的对话意图检测层)
3. [整体定位与设计原则](#三整体定位与设计原则)
4. [已确认设计决策](#四已确认设计决策)
5. [意图类型与状态机设计](#五意图类型与状态机设计)
6. [输入与输出设计](#六输入与输出设计)
7. [执行流程设计](#七执行流程设计)
8. [意图识别策略](#八意图识别策略)
9. [状态流转逻辑](#九状态流转逻辑)
10. [与 S3 / S6 / S7 的关系](#十与-s3--s6--s7-的关系)
11. [Redis 持久化设计](#十一redis-持久化设计)
12. [对外接口设计](#十一对外接口设计)
13. [开发阶段实现建议](#十二开发阶段实现建议)
14. [工程目录建议](#十三工程目录建议)
15. [伪代码设计](#十四伪代码设计)
16. [测试设计](#十五测试设计)
17. [后续演进预留](#十六后续演进预留)

---

## 一、Skill 定位与职责

| 项目 | 内容 |
|------|------|
| **Skill 名称** | DialogIntentDetector |
| **编号** | S4 |
| **核心职责** | 识别工务审核对话中的意图（修改/确认/取消），管理审核状态机，触发 S3 学习飞轮 |
| **调用方** | 上层 Agent 主流程 / 工务审核对话界面 |
| **实施阶段** | MVP 必须 |
| **输出边界** | **输出意图识别结果 + 状态流转建议 + S3 输入构造** |
| **持久化** | **支持 Redis 状态持久化（v1.1.0+）** |

### 核心定位

DialogIntentDetector 是智能评估 Agent 中的"**对话管理层 / 意图识别层**"，负责在工务人员审核评估报告时：

- 理解工务的真实意图（修改/确认/取消）
- 管理审核状态流转（审核中 → 待确认 → 完成）
- 在二次确认后自动构造 S3 学习飞轮输入
- 记录修订历史用于模型优化

### 核心职责

S4 负责：

1. 接收工务对话消息
2. 识别意图类型（MODIFY / READY_TO_CONFIRM / CONFIRM / CANCEL）
3. 管理状态机流转
4. 记录修订历史
5. 在二次确认后构造 S3 输入
6. ✅ **状态持久化到 Redis（v1.1.0+）**
7. ✅ **支持进程重启后自动恢复状态（v1.1.0+）**

### 职责边界

S4：

- **负责对话意图识别**
- **负责状态机管理**
- **负责 S3 学习触发**
- **负责修订历史记录**

S4 不负责：

- 需求解析（S5）
- 历史案例检索（S1）
- 风险/工时/人数推理（S2）
- 报告草稿生成（S6）
- 报告内容修改执行（由 S6 负责）

---

## 二、为什么需要独立的对话意图检测层

### 2.1 根本原因

工务审核环节不是简单的"通过/驳回"，而是一个多轮交互过程：

```
工务查看初稿 → 提出修改 → 查看修订稿 → 再次修改 → 确认最终稿
```

如果没有独立的意图检测层，会导致：

- 意图识别逻辑散落在主流程中，难以维护
- 状态流转不清晰，容易出现状态混乱
- 修订历史无法系统记录
- S3 学习飞轮触发时机不明确

### 2.2 为什么不应把意图检测塞进 S6

虽然 S6 生成报告，但如果把意图检测合并进 S6，会导致：

- S6 职责过重（既要生成又要对话）
- 状态机逻辑与报告生成逻辑耦合
- 难以独立测试意图识别准确率
- 无法灵活调整状态流转规则

因此，S4 必须独立，承担"**报告生成后的对话管理**"职责。

### 2.3 为什么需要状态持久化（v1.1.0+）

生产环境中，工务可能：

- 审核中途离开（开会/休息）
- Agent 服务意外重启
- 网络中断导致会话丢失

如果没有状态持久化：

- 工务必须重新开始审核
- 修订历史丢失
- 用户体验极差

因此，v1.1.0 引入 Redis 持久化，确保：

- **状态持久化** - 审核状态保存到 Redis
- **状态恢复** - Agent 重启后自动恢复
- **未完成列表** - 支持查询未完成的评估单

---

## 三、整体定位与设计原则

### 3.1 在总流程中的位置

```text
S5 ParseRequirementSkill
    ↓
S1 SearchHistoryCasesSkill
    ↓
S2 AssessmentReasoningSkill
    ↓
S6 GenerateReportSkill
    ↓
┌─────────────────────────────────────┐
│ S4 DialogIntentDetector             │
│  - 意图识别                          │
│  - 状态机管理                        │
│  - 修订历史记录                      │
│  - S3 输入构造                        │
│  - Redis 持久化 (v1.1.0+)             │
└─────────────────────────────────────┘
    ↓ (CONFIRM 意图)
S3 LearningFlywheelSkill
    ↓
交付服贸报价
```

### 3.2 三个核心原则

#### 原则 1：意图识别优先于状态流转
必须先准确识别意图，再执行状态流转。

#### 原则 2：二次确认机制
工务首次说"好了"时不直接触发 S3，而是进入二次确认流程，展示修订摘要。

#### 原则 3：状态持久化（v1.1.0+）
每次交互后自动保存状态到 Redis，支持进程重启后恢复。

### 3.3 状态机设计

```
                    ┌──────────────────┐
                    │  初始状态         │
                    │ (S6 生成初稿后)    │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ REVIEW_IN_PROGRESS│
                    │   审核中           │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
      MODIFY  │      READY_TO_CONFIRM       │ CANCEL
              │              │              │
              ▼              ▼              ▼
    ┌─────────────────┐  ┌──────────────────┐
    │ 调用 S6 修改报告   │  │ CONFIRMATION_    │
    │ 保持审核中状态    │  │ PENDING          │
    └────────┬────────┘  │   待确认          │
             │           └────────┬─────────┘
             │                    │
             │           ┌────────┼────────┐
             │           │        │        │
             │     CONFIRM│   CANCEL│  MODIFY
             │           │        │        │
             │           ▼        ▼        ▼
             │    ┌──────────┐  ┌──────────┐
             │    │ COMPLETED│  │返回审核中│
             │    │ 完成      │  │          │
             │    └────┬─────┘  └──────────┘
             │         │
             │         ▼
             │    ┌──────────────┐
             │    │ 调用 S3 学习    │
             │    │ 清理 Redis 状态  │
             │    └──────────────┘
             │
             └─────────────┘ (循环)
```

---

## 四、已确认设计决策

以下事项已确认，并作为本设计稿的正式约束：

| 编号 | 事项 | 确认结论 |
|------|------|----------|
| 1 | 意图类型数量 | **4 种：MODIFY / READY_TO_CONFIRM / CONFIRM / CANCEL** |
| 2 | 状态类型数量 | **3 种：REVIEW_IN_PROGRESS / CONFIRMATION_PENDING / COMPLETED** |
| 3 | 二次确认机制 | **必须，首次确认不直接触发 S3** |
| 4 | S3 触发时机 | **仅 CONFIRM 意图且 modification_count > 0 时触发** |
| 5 | 修订历史必须记录 | **是，用于 S3 学习和审计** |
| 6 | 意图识别置信度阈值 | **0.7，低于此值需询问澄清** |
| 7 | 状态持久化 | **必须，使用 Redis（v1.1.0+）** |
| 8 | 状态 TTL | **1 小时自动过期** |
| 9 | 无修订直接确认 | **跳过二次确认，不触发 S3** |

---

## 五、意图类型与状态机设计

### 5.1 意图类型定义

| 意图 | 触发词示例 | 状态转换 | 后续动作 |
|------|-----------|---------|---------|
| `MODIFY` | "修改/调整/改成/风险调高/工时增加" | REVIEW_IN_PROGRESS → REVIEW_IN_PROGRESS | 调用 S6 修改报告 |
| `READY_TO_CONFIRM` | "好了/可以了/没问题/就这样" | REVIEW_IN_PROGRESS → CONFIRMATION_PENDING | 展示修订摘要，等待二次确认 |
| `CONFIRM` | "确认/通过/同意/交付" | CONFIRMATION_PENDING → COMPLETED | 调用 S3 学习飞轮 |
| `CANCEL` | "取消/放弃/算了/重新来" | CONFIRMATION_PENDING → REVIEW_IN_PROGRESS | 返回审核中状态 |
| `UNKNOWN` | 其他未识别表述 | 保持当前状态 | 询问澄清 |

### 5.2 状态说明

| 状态 | 含义 | 进入条件 | 退出条件 |
|------|------|---------|---------|
| `REVIEW_IN_PROGRESS` | 工务正在修改评估单 | S6 生成初稿后 | 工务说"好了" |
| `CONFIRMATION_PENDING` | 等待工务二次确认 | 工务首次确认 | 工务二次确认或取消 |
| `COMPLETED` | 审核完成，交付服贸 | 工务二次确认 | 无（终态） |

### 5.3 修订历史记录

```json
{
  "modification_history": [
    {
      "round": 1,
      "timestamp": "2026-03-26T10:30:00+08:00",
      "edit_instruction": "风险等级调高一点",
      "intent": "MODIFY",
      "modified_fields": ["risk_rows[0].risk_level"],
      "before_value": "medium",
      "after_value": "high"
    },
    {
      "round": 2,
      "timestamp": "2026-03-26T10:35:00+08:00",
      "edit_instruction": "工时也增加些",
      "intent": "MODIFY",
      "modified_fields": ["report_table.totals.total_hours"],
      "before_value": 110,
      "after_value": 120
    }
  ]
}
```

---

## 六、输入与输出设计

### 6.1 输入结构

```json
{
  "message": "风险等级调高一点",
  "task_id": "TASK-2026-001",
  "org_id": "ORG-001",
  "user_id": "USER-工务 -001",
  "state": "REVIEW_IN_PROGRESS"
}
```

### 6.2 输入说明

| 字段 | 必需 | 说明 |
|------|------|------|
| `message` | ✅ | 工务对话消息 |
| `task_id` | ✅ | 评估单任务 ID |
| `org_id` | ❌ | 组织 ID（用于权限控制） |
| `user_id` | ❌ | 用户 ID（用于审计） |
| `state` | ❌ | 当前状态（可选，默认从状态机读取） |

### 6.3 输出顶层结构

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
    "s3_input_constructed": false,
    "modification_history": [...],
    "state_saved": true
  },
  "error": null
}
```

### 6.4 输出字段说明

| 字段 | 说明 |
|------|------|
| `message` | 给用户的响应消息 |
| `state` | 新状态 |
| `intent` | 识别的意图类型 |
| `confidence` | 意图识别置信度 |
| `action` | 建议的后续动作 |
| `s3_input` | 构造的 S3 输入（CONFIRM 时非空） |
| `s3_input_constructed` | 是否成功构造 S3 输入 |
| `modification_history` | 修订历史 |
| `state_saved` | 状态是否已保存到 Redis |

### 6.5 触发 S3 学习飞轮（确认时）

```json
{
  "success": true,
  "data": {
    "message": "[OK] 已确认最终稿，评估单将交付服贸",
    "state": "COMPLETED",
    "intent": "CONFIRM",
    "confidence": 0.9,
    "action": "call_s3",
    "s3_input": {
      "context": {
        "task_id": "TASK-001",
        "org_id": "ORG-001",
        "user_id": "USER-001",
        "business_type": "轮机"
      },
      "artifacts": {
        "requirement_json": {...},
        "history_cases_json": [...],
        "assessment_reasoning_json": {...},
        "initial_report_json": {...},
        "final_report_json": {...},
        "conversation_messages": [...],
        "edit_actions": [...]
      },
      "versions": {
        "s5_version": "2.0.0",
        "s1_version": "1.0.0",
        "s2_version": "1.1.0",
        "s6_version": "1.0.0",
        "prompt_version": "report_prompt_v1",
        "references_version": "2026-03-24"
      },
      "options": {
        "store_learning_sample": true,
        "generate_rule_candidates": true,
        "generate_preference_candidates": true
      }
    },
    "s3_input_constructed": true,
    "state_saved": false
  },
  "error": null
}
```

---

## 七、执行流程设计

### 7.1 总流程

```text
输入：message + task_id + (可选) state
    ↓
Step 1：加载或初始化状态机
    ↓
Step 2：意图识别
    ↓
Step 3：置信度检查
    ↓
Step 4：状态流转
    ↓
Step 5：记录修订历史
    ↓
Step 6：构造 S3 输入（如适用）
    ↓
Step 7：保存状态到 Redis（v1.1.0+）
    ↓
输出：意图识别结果 + 状态更新
```

### 7.2 Step 1：加载或初始化状态机

执行逻辑：

1. 检查 Redis 中是否存在 `review_state:{task_id}`
2. 如果存在，加载状态
3. 如果不存在，初始化新状态机
4. 设置初始状态为 `REVIEW_IN_PROGRESS`

### 7.3 Step 2：意图识别

执行逻辑：

1. 对 message 进行关键词匹配
2. 计算各意图类型的置信度
3. 选择置信度最高的意图
4. 记录匹配到的触发词

### 7.4 Step 3：置信度检查

执行逻辑：

1. 检查最高置信度是否 >= 0.7
2. 如果低于阈值，返回 `UNKNOWN` 意图
3. 在 message 中建议询问澄清

### 7.5 Step 4：状态流转

执行逻辑：

1. 根据当前状态和识别的意图
2. 查询状态流转表
3. 执行状态转换
4. 如果流转非法，返回错误

### 7.6 Step 5：记录修订历史

执行逻辑：

1. 如果意图为 `MODIFY`，记录修订轮数
2. 保存 edit_instruction
3. 如果 S6 返回 modified_fields，一并记录
4. 更新 modification_history

### 7.7 Step 6：构造 S3 输入

执行逻辑（仅 CONFIRM 意图）：

1. 检查 modification_count > 0
2. 如果为 true，构造完整 S3 输入
3. 如果为 false（无修订直接确认），设置 `s3_input_constructed = false`
4. 在 message 中提示跳过 S3

### 7.8 Step 7：保存状态到 Redis（v1.1.0+）

执行逻辑：

1. 序列化状态机数据
2. 保存到 `review_state:{task_id}`
3. 设置 TTL = 3600 秒
4. 更新用户未完成列表 `user_pending_tasks:{user_id}`
5. 更新全局未完成列表 `global_pending_tasks`
6. 如果状态为 `COMPLETED`，删除 Redis 状态

---

## 八、意图识别策略

### 8.1 关键词匹配规则

#### MODIFY 意图

```python
MODIFY_KEYWORDS = [
    "修改", "调整", "改成", "改为", "调高", "调低",
    "增加", "减少", "补充", "删除", "去掉",
    "风险", "工时", "人数", "工具", "耗材"
]
```

#### READY_TO_CONFIRM 意图

```python
READY_TO_CONFIRM_KEYWORDS = [
    "好了", "可以了", "没问题", "就这样", "行了",
    "OK", "ok", "通过", "审核通过"
]
```

#### CONFIRM 意图

```python
CONFIRM_KEYWORDS = [
    "确认", "确认最终稿", "交付", "同意", "没问题了",
    "可以交付", "审核完成", "最终确认"
]
```

#### CANCEL 意图

```python
CANCEL_KEYWORDS = [
    "取消", "放弃", "算了", "重新来", "重来",
    "返回", "回到上一步", "不满意"
]
```

### 8.2 置信度计算

```python
def calculate_confidence(message, intent_keywords):
    """
    计算意图识别置信度
    
    规则：
    1. 完全匹配关键词：0.9-1.0
    2. 部分匹配关键词：0.7-0.9
    3. 语义相关但无关键词：0.5-0.7
    4. 无匹配：0.0-0.5
    """
    matched_keywords = [kw for kw in intent_keywords if kw in message]
    
    if not matched_keywords:
        return 0.3  # 无匹配
    
    match_ratio = len(matched_keywords) / len(intent_keywords)
    
    if match_ratio > 0.5:
        return 0.9 + (match_ratio - 0.5) * 0.2
    else:
        return 0.7 + match_ratio * 0.4
```

### 8.3 上下文增强识别（第二期）

未来可引入：

- 对话上下文（前几轮说了什么）
- 当前状态（审核中 vs 待确认）
- 修订历史（已修改几轮）
- 用户习惯（该工务的常用表述）

---

## 九、状态流转逻辑

### 9.1 状态流转表

| 当前状态 | 意图 | 新状态 | 是否合法 | 说明 |
|----------|------|--------|---------|------|
| `REVIEW_IN_PROGRESS` | `MODIFY` | `REVIEW_IN_PROGRESS` | ✅ | 继续修改 |
| `REVIEW_IN_PROGRESS` | `READY_TO_CONFIRM` | `CONFIRMATION_PENDING` | ✅ | 进入二次确认 |
| `REVIEW_IN_PROGRESS` | `CONFIRM` | `CONFIRMATION_PENDING` | ⚠️ | 跳过二次确认（无修订时） |
| `REVIEW_IN_PROGRESS` | `CANCEL` | `REVIEW_IN_PROGRESS` | ⚠️ | 已经是审核中，忽略 |
| `CONFIRMATION_PENDING` | `MODIFY` | `REVIEW_IN_PROGRESS` | ✅ | 返回修改 |
| `CONFIRMATION_PENDING` | `READY_TO_CONFIRM` | `CONFIRMATION_PENDING` | ⚠️ | 已在待确认，忽略 |
| `CONFIRMATION_PENDING` | `CONFIRM` | `COMPLETED` | ✅ | 确认完成 |
| `CONFIRMATION_PENDING` | `CANCEL` | `REVIEW_IN_PROGRESS` | ✅ | 取消确认 |
| `COMPLETED` | 任意 | `COMPLETED` | ❌ | 终态，不可流转 |

### 9.2 非法流转处理

```python
def handle_invalid_transition(current_state, intent):
    """
    处理非法状态流转
    
    策略：
    1. 返回错误提示
    2. 保持当前状态
    3. 建议合法操作
    """
    error_messages = {
        ("COMPLETED", "*"): "审核已完成，无法继续操作",
        ("REVIEW_IN_PROGRESS", "CONFIRM"): "请先说'好了'进入确认流程",
        ("CONFIRMATION_PENDING", "READY_TO_CONFIRM"): "已处于待确认状态，请说'确认'或'取消'"
    }
    
    key = (current_state, intent)
    return error_messages.get(key, "状态流转错误")
```

---

## 十、与 S3 / S6 / S7 的关系

### 与 S3 LearningFlywheelSkill

S4 负责：
- 识别 CONFIRM 意图
- 构造 S3 输入数据结构
- 在 modification_count > 0 时触发 S3

S3 负责：
- 接收 S4 构造的输入
- 执行差异分析
- 生成学习样本

关系：
- **S4 是 S3 的前置触发器**
- **S4 不负责学习逻辑，只负责构造输入**

### 与 S6 GenerateReportSkill

S4 负责：
- 识别 MODIFY 意图
- 传递 edit_instruction 给 S6
- 记录修订轮数

S6 负责：
- 执行报告修改
- 返回 modified_fields

关系：
- **S4 是对话管理，S6 是内容修改**
- **S4 不调用 S6，由上层 Agent 协调**

### 与 S7 ReviewPersistenceSkill

S7 负责：
- Redis 状态持久化
- 状态恢复
- 未完成列表管理

S4 负责：
- 调用 S7 保存状态
- 在进程重启后恢复状态

关系：
- **S7 是 S4 的持久化层**
- **S4 每次交互后自动调用 S7**

---

## 十一、Redis 持久化设计

### 11.1 Redis Key 设计

```
# 单个评估单状态
review_state:{task_id} = JSON 对象
# 过期时间：STATE_TTL_SECONDS (默认 3600 秒)

# 用户未完成列表 (Set)
user_pending_tasks:{user_id} = {task_id_1, task_id_2, ...}
# 过期时间：PENDING_LIST_TTL_SECONDS (默认 86400 秒)

# 全局未完成列表 (Sorted Set, 按时间排序)
global_pending_tasks = {task_id_1: timestamp_1, task_id_2: timestamp_2, ...}
# 过期时间：PENDING_LIST_TTL_SECONDS (默认 86400 秒)
```

### 11.2 状态数据结构

```json
{
  "state": "REVIEW_IN_PROGRESS",
  "task_name": "XX 项目",
  "org_id": "ORG-001",
  "user_id": "USER-001",
  "context": {
    "current_round": 3,
    "last_modification": {
      "edit_instruction": "风险等级调高一点",
      "timestamp": "2026-03-26T10:30:00+08:00"
    }
  },
  "modification_history": [
    {
      "round": 1,
      "timestamp": "2026-03-26T10:30:00+08:00",
      "edit_instruction": "风险等级调高一点",
      "intent": "MODIFY"
    }
  ],
  "last_modified": "2026-03-26T10:30:00+08:00",
  "modification_count": 1
}
```

### 11.3 持久化时机

| 时机 | 操作 | 说明 |
|------|------|------|
| 每次交互后 | 保存状态 | 确保状态不丢失 |
| 状态流转时 | 更新状态 | 记录新状态 |
| 审核完成时 | 删除状态 | 清理 Redis |
| 进程启动时 | 扫描恢复 | 恢复未完成状态 |

### 11.4 自动恢复逻辑（v1.1.0+）

```python
def recover_all_states():
    """
    Agent 启动时恢复所有未完成状态
    
    步骤：
    1. 扫描 global_pending_tasks
    2. 过滤未过期的 task_id
    3. 加载每个 task_id 的状态
    4. 重建状态机实例
    5. 记录恢复日志
    """
    recovered_count = 0
    for task_id in global_pending_tasks:
        state = redis.get(f"review_state:{task_id}")
        if state:
            state_machine = ReviewStateMachine.from_json(state)
            recovered_count += 1
    
    logger.info(f"已恢复 {recovered_count} 个未完成状态")
```

---

## 十二、对外接口设计

### 12.1 主接口

| 接口 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `process_message(message, task_id, ...)` | 用户消息 + 任务 ID | 意图识别结果 + 状态更新 | 主接口 |
| `get_state(task_id)` | 任务 ID | 当前状态 | 获取状态 |
| `reset_state(task_id)` | 任务 ID | 重置结果 | 重置状态 |

### 12.2 输入输出原则

- 一次处理一条用户消息
- 输出必须包含 `success / data / error`
- 输出必须包含 `intent / confidence / state`
- 输出必须包含 `action` 建议
- CONFIRM 时尝试构造 `s3_input`

---

## 十三、开发阶段实现建议

### 13.1 MVP 优先级

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0 | 意图识别（4 种类型） | 最小可用能力 |
| P0 | 状态机管理 | 状态流转逻辑 |
| P0 | 修订历史记录 | 记录 modification_history |
| P1 | 二次确认机制 | READY_TO_CONFIRM → CONFIRM |
| P1 | S3 输入构造 | CONFIRM 时构造 s3_input |
| P1 | Redis 持久化（v1.1.0） | 状态保存与恢复 |
| P2 | 置信度阈值检查 | < 0.7 时询问澄清 |

### 13.2 实现策略建议

#### 意图识别
- 关键词匹配优先
- 置信度计算简单明了
- 预留语义理解接口

#### 状态机
- 使用枚举定义状态
- 状态流转表驱动
- 非法流转返回错误

#### 持久化
- 使用 Redis Hash 结构
- 设置合理 TTL
- 完成时自动清理

---

## 十四、工程目录建议

```text
s4-dialog-intent-detector/
├── SKILL.md
├── scripts/
│   ├── main.py                      # CLI 入口
│   ├── intent_detector.py           # 意图识别
│   ├── state_machine.py             # 状态机管理
│   ├── redis_persistence.py         # Redis 持久化（v1.1.0+）
│   └── s3_input_builder.py          # S3 输入构造
├── references/
│   ├── config.md
│   ├── intent-keywords.json         # 意图关键词配置
│   └── state-transitions.json       # 状态流转表
├── samples/
│   ├── sample-message.json
│   └── sample-output.json
└── tests/
    ├── test_intent_detector.py
    ├── test_state_machine.py
    └── test_redis_persistence.py
```

---

## 十五、伪代码设计

```python
def process_message(message, task_id, org_id, user_id, state=None):
    # Step 1: 加载或初始化状态机
    state_machine = load_or_init_state_machine(task_id, org_id, user_id, state)
    
    # Step 2: 意图识别
    intent, confidence, matched_keywords = detect_intent(message)
    
    # Step 3: 置信度检查
    if confidence < 0.7:
        return {
            "success": True,
            "data": {
                "message": f"未识别您的意图，您是想修改还是确认？",
                "intent": "UNKNOWN",
                "confidence": confidence,
                "state": state_machine.state.value
            }
        }
    
    # Step 4: 状态流转
    new_state, is_valid = state_machine.transition(intent)
    
    if not is_valid:
        return {
            "success": False,
            "error": {
                "code": "INVALID_STATE_TRANSITION",
                "message": handle_invalid_transition(state_machine.state.value, intent)
            }
        }
    
    # Step 5: 记录修订历史
    if intent == "MODIFY":
        state_machine.record_modification(message)
    
    # Step 6: 构造 S3 输入
    s3_input = None
    s3_input_constructed = False
    
    if intent == "CONFIRM" and state_machine.modification_count > 0:
        s3_input = build_s3_input(state_machine)
        s3_input_constructed = True
    
    # Step 7: 保存状态到 Redis
    state_saved = save_state_to_redis(state_machine)
    
    # 构建响应
    return {
        "success": True,
        "data": {
            "message": build_response_message(intent, new_state),
            "state": new_state.value,
            "intent": intent,
            "confidence": confidence,
            "action": suggest_action(intent),
            "s3_input": s3_input,
            "s3_input_constructed": s3_input_constructed,
            "modification_history": state_machine.modification_history,
            "state_saved": state_saved
        },
        "error": None
    }
```

---

## 十六、测试设计

### 16.1 测试目标

- 意图识别准确
- 状态流转正确
- 修订历史记录完整
- S3 输入构造正确
- Redis 持久化可靠
- 中文正常显示，无乱码

### 16.2 测试场景

#### 场景 A：正常修改流程

```
用户："风险等级调高一点" → MODIFY
用户："工时也增加些" → MODIFY
用户："好了" → READY_TO_CONFIRM
用户："确认" → CONFIRM
预期：触发 S3，状态流转正确
```

#### 场景 B：无修订直接确认

```
用户："好了" → READY_TO_CONFIRM
用户："确认" → CONFIRM
预期：modification_count = 0，不触发 S3
```

#### 场景 C：取消确认

```
用户："好了" → READY_TO_CONFIRM
用户："取消" → CANCEL
预期：返回 REVIEW_IN_PROGRESS
```

#### 场景 D：意图识别置信度低

```
用户："这个那个什么的" → UNKNOWN
预期：confidence < 0.7，询问澄清
```

#### 场景 E：状态持久化与恢复

```
1. 用户修改 → 保存状态
2. 进程重启
3. 加载状态 → 恢复成功
预期：状态、修订历史完整恢复
```

### 16.3 测试检查清单

- [ ] 输出包含 `success`, `data`, `error`
- [ ] `intent` 正常输出
- [ ] `confidence` 正常输出
- [ ] `state` 正常输出
- [ ] `action` 正常输出
- [ ] `modification_history` 正常输出
- [ ] `s3_input` 在 CONFIRM 时正确构造
- [ ] Redis 持久化正常
- [ ] 中文正常显示，无乱码

---

## 十七、后续演进预留

### 17.1 第二期增强

- 语义理解增强（接入 LLM）
- 上下文感知意图识别
- 用户习惯学习
- 多轮对话管理

### 17.2 第三期增强

- 意图识别准确率看板
- 高频修改模式分析
- 智能推荐修改建议
- 与 S3 学习结果联动

### 17.3 长期方向

- 形成"对话 - 修改 - 学习"完整闭环
- 基于工务人员对话持续优化意图识别
- 实现更自然的工务审核体验

---

*文档持续更新中，最后修改：2026-03-26*
