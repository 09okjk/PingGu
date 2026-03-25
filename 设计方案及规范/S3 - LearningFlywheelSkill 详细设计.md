# S3 - LearningFlywheelSkill 详细设计

> 创建日期：2026-03-25  
> 最后修改：2026-03-25  
> 状态：设计新增（V1）  
> 所属模块：智能评估 Agent — Skills 层

---

## 目录

1. [Skill 定位与职责](#一skill-定位与职责)
2. [为什么必须独立为 LearningFlywheelSkill](#二为什么必须独立为-learningflywheelskill)
3. [整体定位与设计原则](#三整体定位与设计原则)
4. [已确认设计决策](#四已确认设计决策)
5. [输入与输出设计](#五输入与输出设计)
6. [执行流程设计](#六执行流程设计)
7. [修订归因标签设计](#七修订归因标签设计)
8. [学习资产设计](#八学习资产设计)
9. [数据库设计建议](#九数据库设计建议)
10. [与 S1 / S2 / S5 / S6 / R2 的关系](#十与-s1--s2--s5--s6--r2-的关系)
11. [对外接口设计](#十一对外接口设计)
12. [开发阶段实现建议](#十二开发阶段实现建议)
13. [工程目录建议](#十三工程目录建议)
14. [伪代码设计](#十四伪代码设计)
15. [测试设计](#十五测试设计)
16. [后续演进预留](#十六后续演进预留)

---

## 一、Skill 定位与职责

| 项目 | 内容 |
|------|------|
| **Skill 名称** | LearningFlywheelSkill |
| **编号** | S3 |
| **核心职责** | 对“初稿 → 人工修订 → 最终确认”的全过程进行差异采集、归因打标、学习资产提炼，并反哺后续评估流程 |
| **调用方** | 上层 Agent / 评估确认后的后台自动任务 |
| **实施阶段** | 第二期建议优先实现 |
| **输出边界** | **不直接修改当前评估结论，只生成未来可复用的学习资产与候选知识** |

### 核心定位

LearningFlywheelSkill 是智能评估 Agent 中的“**闭环学习层 / 经验沉淀层**”，负责把一次真实评估中的人工修订过程转化为系统后续可利用的经验资产。

它的核心价值不是再做一次评估，而是：

- 理解人工到底改了什么
- 理解人工为什么这么改
- 判断这次修订是否值得学习
- 把值得学习的部分转化为可复用资产
- 在下一轮评估时为 S1 / S2 / S6 提供更贴近真实业务习惯的参考

### 核心职责

S3 负责：

1. 采集初稿、终稿、修订动作与对话上下文
2. 生成结构化 revision diff
3. 对修订原因进行归因分类
4. 生成高质量学习样本
5. 提炼候选规则与输出偏好候选
6. 输出后续存储、审核与反哺动作建议

### 职责边界

S3：

- **负责“未来优化”所需的学习资产生成**
- **负责“候选知识”的提炼与分类**
- **负责“修订经验”向可检索资产的转化**

S3 不负责：

- 当前需求解析（S5）
- 当前历史案例检索（S1）
- 当前风险 / 工时 / 人数推理（S2）
- 当前报告草稿生成（S6）
- 直接修改当前报告终稿
- 直接自动生效正式规则

---

## 二、为什么必须独立为 LearningFlywheelSkill

### 2.1 根本原因

如果没有独立的闭环学习模块，系统虽然能生成评估草稿，但每次都像“从零开始”，难以持续逼近真实评估人员的经验判断。

当前主流程的四个 Skill 分别负责：

- S5：解析与确认需求
- S1：检索历史参考
- S2：做专项推理
- S6：组织最终报告

但“人工修订”本身尚未被结构化地利用。

### 2.2 为什么不应把飞轮逻辑直接塞进 S6

虽然 S6 最接近最终报告，但如果把学习飞轮直接合并进 S6，会导致：

- 当前结果生成和未来学习沉淀边界混乱
- 在线链路职责过重
- 学习逻辑难以单独回滚和调试
- 难以实现后台异步执行

因此，S3 必须独立，承担“**当前链路完成之后的经验沉淀**”职责。

### 2.3 为什么 S3 不能直接改当前结论

这是最关键的边界：

> **S3 只优化未来，不改写当前。**

原因：

1. 当前终稿应由人工确认负责，保证可控性
2. 单次修订可能是偶发偏好，不能立刻污染全局知识
3. 候选知识需要经过聚类、统计和人工审核后才适合正式生效

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
人工审阅 / 对话修订 / 终稿确认
    ↓
S3 LearningFlywheelSkill
    ↓
学习资产库
    ├── 修订经验样本库
    ├── 候选规则库
    ├── 已审核规则库
    └── 输出偏好库
    ↓
下一轮评估复用
```

### 3.2 三个核心原则

#### 原则 1：对当前流程无侵入
S3 默认在终稿确认后后台触发，不阻塞主评估链路。

#### 原则 2：候选与生效分离
S3 产出的知识必须明确分为：
- 候选资产
- 已审核生效资产

#### 原则 3：优先学习共性，不放大个体偶发偏好
一次修订先记为样本；高频、稳定、可解释的模式才考虑升级为规则或偏好。

### 3.3 三层学习模型

S3 建议按三层学习能力建设：

1. **案例学习**（优先级最高）
   - 保存“人修过的好答案”
   - 供 S1 检索参考

2. **规则学习**
   - 从高频修订模式中提炼候选规则
   - 审核通过后反哺 S2

3. **偏好学习**
   - 学习报告结构和表达偏好
   - 反哺 S6 的输出组织

---

## 四、已确认设计决策

以下事项已确认，并作为本设计稿的正式约束：

| 编号 | 事项 | 确认结论 |
|------|------|----------|
| 1 | S3 是否修改当前结论 | **不修改，只服务未来优化** |
| 2 | S3 触发时机 | **终稿确认后后台自动触发** |
| 3 | S3 对用户是否显式可见 | **普通工务用户无感，管理员可见统计结果** |
| 4 | 单次修订是否可直接生效 | **不可以，需先作为候选资产沉淀** |
| 5 | 优先沉淀哪类资产 | **修订经验样本优先** |
| 6 | 是否需要规则候选审核机制 | **需要** |
| 7 | 是否需要偏好候选审核机制 | **建议需要** |
| 8 | S3 输出形式 | **结构化 JSON，包含 diff、标签、样本、候选规则、偏好候选** |
| 9 | 是否阻塞主流程 | **不阻塞，异步执行** |

---

## 五、输入与输出设计

### 5.1 输入结构

```json
{
  "context": {
    "task_id": "AT202603250001",
    "org_id": "org_001",
    "user_id": "u_123",
    "business_type": "轮机",
    "ship_type": "bulk_carrier"
  },
  "artifacts": {
    "requirement_json": {},
    "history_cases_json": [],
    "assessment_reasoning_json": {},
    "initial_report_json": {},
    "final_report_json": {},
    "conversation_messages": [],
    "edit_actions": []
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
}
```

---

### 5.2 输入说明

| 字段 | 必需 | 说明 |
|------|------|------|
| `context` | ✅ | 当前评估任务的业务上下文 |
| `artifacts.requirement_json` | ✅ | 当前需求及确认结果 |
| `artifacts.history_cases_json` | ✅ | S1 返回的历史案例参考 |
| `artifacts.assessment_reasoning_json` | ✅ | S2 推理结果 |
| `artifacts.initial_report_json` | ✅ | 初始评估草稿 |
| `artifacts.final_report_json` | ✅ | 人工确认后的最终报告 |
| `artifacts.conversation_messages` | ❌ | 人机对话修订记录 |
| `artifacts.edit_actions` | ❌ | 前端或后端记录的字段编辑动作 |
| `versions` | ✅ | Skill / Prompt / Reference 版本信息 |
| `options.*` | ❌ | 是否生成各类候选资产 |

说明：
- 若无 `edit_actions`，S3 也必须能基于初稿与终稿做 diff 提取
- `versions` 必须记录，便于回溯学习结果来自哪个系统版本

---

### 5.3 输出结构

```json
{
  "success": true,
  "data": {
    "revision_diff": [],
    "feedback_tags": [],
    "learning_sample": {
      "store": true,
      "quality_score": 0.92,
      "sample_type": "revision_case"
    },
    "rule_candidates": [],
    "report_preference_candidates": [],
    "next_step_actions": [
      "store_revision",
      "store_learning_sample",
      "submit_rule_candidates_for_review"
    ]
  },
  "error": null
}
```

---

### 5.4 revision_diff 结构建议

```json
[
  {
    "field_path": "report_table.risk_rows[0].risk_level",
    "action": "update",
    "before": "medium",
    "after": "high"
  },
  {
    "field_path": "report_table.spare_parts_or_equipment.to_be_confirmed",
    "action": "append",
    "before": [],
    "after": [
      {
        "item_name": "专用备件包"
      }
    ]
  }
]
```

---

## 六、执行流程设计

### 6.1 总流程

```text
输入：context + artifacts + versions
    ↓
Step 1：输入校验与标准化
    ↓
Step 2：提取 revision diff
    ↓
Step 3：修订归因分类
    ↓
Step 4：学习样本评分
    ↓
Step 5：提炼候选规则
    ↓
Step 6：提炼输出偏好候选
    ↓
Step 7：生成 next_step_actions
    ↓
输出统一学习结果
```

---

### 6.2 Step 1：输入校验与标准化

执行内容：

1. 校验 `initial_report_json` 与 `final_report_json` 是否存在
2. 标准化字段路径表示方式
3. 清洗空值、无效占位内容
4. 统一对话消息与编辑动作格式
5. 检查是否满足“可学习”最低条件

输出：
- `normalized_context`
- `normalized_artifacts`
- `normalized_versions`

---

### 6.3 Step 2：提取 revision diff

执行逻辑：

1. 对比初稿与终稿的结构化 JSON
2. 识别字段级 `add` / `update` / `remove` / `append`
3. 尽可能保留原始路径与变化前后值
4. 将自由文本修改抽象为可追踪条目

输出：
- `revision_diff`

说明：
- diff 是后续归因和学习提炼的基础，不可省略
- 若字段太大，应保留摘要而非重复整段长文本

---

### 6.4 Step 3：修订归因分类

执行逻辑：

1. 基于 diff 判断修改落在哪一类问题上
2. 结合 S1/S2/S6 的输入与结果判断问题来源
3. 必要时参考对话记录中的用户解释
4. 输出可枚举、可统计的 `feedback_tags`

输出：
- `feedback_tags`

说明：
- 同一次修订可命中多个标签
- 标签应尽量业务可理解，便于后续统计看板

---

### 6.5 Step 4：学习样本评分

执行逻辑：

1. 判断本次修订是否完整且明确
2. 判断终稿是否稳定、结构是否可复用
3. 判断修订是否有明确业务价值
4. 计算 `quality_score`
5. 决定是否进入高质量学习样本库

输出：
- `learning_sample`

评分维度建议：
- 修改是否明确
- 最终结果是否完整
- 终稿是否已确认
- 是否存在清晰归因
- 是否适合复用于相似场景

---

### 6.6 Step 5：提炼候选规则

执行逻辑：

1. 从本次修订中提取“触发条件 → 修订建议”模式
2. 识别是否属于共性问题而非个体偏好
3. 形成规则候选结构
4. 给出置信度与审核建议

输出：
- `rule_candidates`

说明：
- 单次可生成候选规则，但不自动生效
- 候选规则需进入审核流程，审核通过后方可进入正式规则库

---

### 6.7 Step 6：提炼输出偏好候选

执行逻辑：

1. 识别用户增加/调整了哪些章节、字段、表达方式
2. 判断这类偏好是否具有场景性或组织一致性
3. 输出偏好候选

输出：
- `report_preference_candidates`

说明：
- 偏好学习优先影响 S6 报告组织
- 不应影响 S2 的核心判断逻辑

---

### 6.8 Step 7：生成 next_step_actions

执行内容：

1. 判断哪些结果需要写入数据库
2. 判断哪些候选需进入审核队列
3. 判断哪些结果仅适合存档，不适合生效
4. 输出建议动作列表

输出：
- `next_step_actions`

---

## 七、修订归因标签设计

### 7.1 建议标签集合

```json
[
  "PARSE_INCOMPLETE",
  "RETRIEVAL_MISS",
  "RISK_UNDER_ESTIMATED",
  "RISK_OVER_ESTIMATED",
  "WORKHOUR_UNDER_ESTIMATED",
  "WORKHOUR_OVER_ESTIMATED",
  "MANPOWER_UNDER_ESTIMATED",
  "MANPOWER_OVER_ESTIMATED",
  "MISSING_DIMENSION",
  "MISSING_RECOMMENDATION",
  "WRONG_TERMINOLOGY",
  "UNCLEAR_EXPRESSION",
  "FORMAT_NOT_PRACTICAL",
  "ORG_SPECIFIC_PREFERENCE"
]
```

### 7.2 标签说明示例

| 标签 | 含义 | 示例 |
|------|------|------|
| `PARSE_INCOMPLETE` | 需求解析不完整 | 服务类型、设备型号被人工补齐 |
| `RETRIEVAL_MISS` | 检索参考不足或偏差 | 人工补充了历史常见但系统未给出的任务 |
| `RISK_UNDER_ESTIMATED` | 风险评估偏低 | 风险等级从中调整为高 |
| `MISSING_DIMENSION` | 漏掉关键业务维度 | 人工补充“停航影响”或“备件等待” |
| `MISSING_RECOMMENDATION` | 缺少必要建议项 | 人工新增“靠港前完成”建议 |
| `WRONG_TERMINOLOGY` | 术语不专业或不符合习惯 | “建议处理”改为“建议施工措施” |
| `FORMAT_NOT_PRACTICAL` | 报告结构不利于审核或报价 | 人工重排字段顺序或补充表头 |
| `ORG_SPECIFIC_PREFERENCE` | 组织特定偏好 | 某部门固定要求增加“时效说明” |

---

## 八、学习资产设计

### 8.1 资产类型总览

| 资产类型 | 作用 | 反哺对象 |
|----------|------|----------|
| 修订经验样本 | 相似场景检索参考 | S1 / S2 |
| 候选规则 | 高频共性问题规则化 | S2 |
| 已审核规则 | 正式生效知识 | S2 |
| 输出偏好候选 | 结构与表达偏好学习 | S6 |
| 已审核输出偏好 | 正式生效的场景化输出配置 | S6 |

### 8.2 学习样本结构建议

```json
{
  "sample_id": "LF-20260325-0001",
  "sample_type": "revision_case",
  "scenario": {
    "business_type": "轮机",
    "service_desc_code": "RS0000001761",
    "service_type_code": "CS0001"
  },
  "revision_summary": "风险等级上调，并补充备件等待影响",
  "quality_score": 0.92,
  "source_task_id": "AT202603250001",
  "status": "candidate"
}
```

### 8.3 候选规则结构建议

```json
{
  "candidate_rule_id": "CR-20260325-001",
  "trigger": {
    "business_type": "轮机",
    "service_desc_code": "RS0000001761",
    "remark_keywords": ["异常振动", "备件等待"]
  },
  "suggestion": {
    "risk_level_floor": "medium",
    "must_include_sections": ["风险提示", "备件建议", "时效影响"]
  },
  "confidence": 0.78,
  "status": "pending_review"
}
```

### 8.4 输出偏好候选结构建议

```json
{
  "preference_id": "PF-20260325-001",
  "scenario": "轮机类高风险问题",
  "required_sections": [
    "风险等级",
    "停航影响",
    "备件建议",
    "建议时效"
  ],
  "expression_preference": "先结论后依据",
  "status": "pending_review"
}
```

---

## 九、数据库设计建议

### 9.1 数据库归属

建议 S3 与 S1/S2 共享 `pinggu` 数据库，统一管理历史案例、规则库和学习资产。

这样有几个好处：

- 避免多库维护
- 便于将学习资产与历史案例联动检索
- 便于将候选规则审核后无缝转入正式规则体系
- 便于后续数据看板与飞轮统计

---

### 9.2 建议表

| 表名 | 用途 |
|------|------|
| `learning_revision_records` | 存储单次修订事件及 diff |
| `learning_feedback_tags` | 存储修订归因标签 |
| `learning_samples` | 存储高质量学习样本 |
| `learning_rule_candidates` | 存储候选规则 |
| `learning_report_preferences` | 存储偏好候选与已审核偏好 |

### 9.3 建议表结构示意

```sql
CREATE TABLE learning_revision_records (
  id BIGSERIAL PRIMARY KEY,
  task_id VARCHAR(50) NOT NULL,
  org_id VARCHAR(50),
  user_id VARCHAR(50),
  requirement_id VARCHAR(50),
  revision_diff JSONB NOT NULL,
  initial_report_json JSONB NOT NULL,
  final_report_json JSONB NOT NULL,
  versions JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE learning_feedback_tags (
  id BIGSERIAL PRIMARY KEY,
  revision_record_id BIGINT NOT NULL REFERENCES learning_revision_records(id) ON DELETE CASCADE,
  tag_code VARCHAR(50) NOT NULL,
  tag_confidence DECIMAL(4,2),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE learning_samples (
  id BIGSERIAL PRIMARY KEY,
  sample_id VARCHAR(50) UNIQUE NOT NULL,
  task_id VARCHAR(50) NOT NULL,
  scenario JSONB NOT NULL,
  revision_summary TEXT,
  quality_score DECIMAL(4,2),
  status VARCHAR(20) DEFAULT 'candidate',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE learning_rule_candidates (
  id BIGSERIAL PRIMARY KEY,
  candidate_rule_id VARCHAR(50) UNIQUE NOT NULL,
  trigger JSONB NOT NULL,
  suggestion JSONB NOT NULL,
  confidence DECIMAL(4,2),
  status VARCHAR(20) DEFAULT 'pending_review',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE learning_report_preferences (
  id BIGSERIAL PRIMARY KEY,
  preference_id VARCHAR(50) UNIQUE NOT NULL,
  scenario VARCHAR(200) NOT NULL,
  preference_content JSONB NOT NULL,
  status VARCHAR(20) DEFAULT 'pending_review',
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 十、与 S1 / S2 / S5 / S6 / R2 的关系

### 与 S5 ParseRequirementSkill

S5 负责：
- 原始需求解析
- 交互确认
- 输出已确认 RequirementItem

S3 使用 S5 的结果理解“当前任务是什么”，并把需求上下文作为学习样本的场景特征。

---

### 与 S1 SearchHistoryCasesSkill

S1 负责：
- 历史相似案例检索
- 返回 Top-K 参考案例

S3 不重新检索历史案例，而是使用 S1 输出判断：
- 当时参考了什么
- 是否存在检索不足
- 哪些修订经验值得纳入未来检索资产

未来反哺方式：
- S1 增加对 `learning_samples` 的相似修订样本检索

---

### 与 S2 AssessmentReasoningSkill

S2 负责：
- 风险推理
- 工时推理
- 人数推理

S3 不重做专项推理，但会根据人工修订判断：
- 哪些推理偏高或偏低
- 哪些修订模式可形成候选规则

未来反哺方式：
- S2 读取已审核规则和高频修订提示

---

### 与 S6 GenerateReportSkill

S6 负责：
- 组织最终评估报告草稿
- 输出可审核结构

S3 以 S6 初稿与人工终稿的差异作为核心输入之一。

未来反哺方式：
- S6 读取已审核输出偏好
- S6 读取高频补充章节建议
- S6 读取审核重点模板

---

### 与 R2 枚举字典与通用规则

R2 负责：
- 枚举规范化
- 通用业务约束

S3 使用 R2 做：
- 场景特征标准化
- diff 中字段和术语统一
- 候选规则触发条件标准化

---

## 十一、对外接口设计

### 11.1 主接口

| 接口 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `learn_from_revision(context, artifacts, versions)` | 评估上下文 + 初稿终稿 + 修订记录 + 版本信息 | diff / 标签 / 学习样本 / 候选规则 / 偏好候选 | 主接口 |

---

### 11.2 可选内部子接口

建议内部保留以下逻辑接口，便于测试和后续迭代：

| 接口 | 说明 |
|------|------|
| `extract_revision_diff(...)` | 仅提取字段级差异 |
| `classify_feedback(...)` | 仅做修订归因标签分类 |
| `score_learning_sample(...)` | 仅判断样本质量与可学习性 |
| `mine_rule_candidates(...)` | 仅提炼候选规则 |
| `mine_report_preferences(...)` | 仅提炼偏好候选 |

---

### 11.3 输入输出原则

- 一次处理一次已完成确认的评估任务
- 输出必须保持结构稳定
- 输出结果必须清晰区分“候选”与“已生效”
- 输出必须附带足够的可追溯信息

---

## 十二、开发阶段实现建议

### 12.1 分阶段落地顺序

#### Phase 1：最小闭环
- 记录初稿与终稿
- 自动生成 diff
- 简单归因打标签
- 入学习样本库

#### Phase 2：反哺检索
- S1 检索相似修订经验样本
- 为 S2 提供“相似修订参考摘要”

#### Phase 3：规则候选审核
- 批量聚类高频修订模式
- 生成候选规则
- 增加审核通过后生效流程

#### Phase 4：偏好学习
- 学习不同业务/角色的报告输出偏好
- 反哺 S6 的输出结构

---

### 12.2 MVP 后的优先实现建议

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0 | revision diff 提取 | 最小可用能力 |
| P0 | learning_samples 入库 | 先建立学习资产基础 |
| P1 | feedback_tags 归因 | 为后续看板与规则挖掘提供基础 |
| P1 | S1 检索修订经验样本 | 最快体现飞轮价值 |
| P1 | 候选规则生成 | 为后续审核机制做准备 |
| P2 | 输出偏好候选 | 优化 S6 可用性 |

---

## 十三、工程目录建议

```text
learning-flywheel-skill/
├── SKILL.md
├── scripts/
│   ├── main.py
│   ├── diff_extractor.py
│   ├── feedback_classifier.py
│   ├── sample_scorer.py
│   ├── rule_miner.py
│   ├── preference_miner.py
│   ├── storage.py
│   └── utils.py
├── references/
│   ├── config.md
│   ├── feedback-tags.md
│   └── output.schema.json
└── samples/
    ├── sample-input.json
    └── sample-output.json
```

说明：
- `feedback-tags.md` 建议单独维护，便于业务侧审核标签体系
- `output.schema.json` 用于约束 S3 输出结构稳定性

---

## 十四、伪代码设计

```python
def learn_from_revision(context, artifacts, versions, options=None):
    options = options or {}

    normalized_context = normalize_context(context)
    normalized_artifacts = normalize_artifacts(artifacts)
    normalized_versions = normalize_versions(versions)

    revision_diff = extract_revision_diff(
        normalized_artifacts["initial_report_json"],
        normalized_artifacts["final_report_json"],
        normalized_artifacts.get("edit_actions", []),
    )

    feedback_tags = classify_feedback(
        revision_diff,
        normalized_artifacts,
    )

    learning_sample = score_learning_sample(
        normalized_context,
        normalized_artifacts,
        revision_diff,
        feedback_tags,
    )

    rule_candidates = []
    if options.get("generate_rule_candidates", True):
        rule_candidates = mine_rule_candidates(
            normalized_context,
            normalized_artifacts,
            revision_diff,
            feedback_tags,
        )

    report_preference_candidates = []
    if options.get("generate_preference_candidates", True):
        report_preference_candidates = mine_report_preferences(
            normalized_context,
            normalized_artifacts,
            revision_diff,
            feedback_tags,
        )

    next_step_actions = build_next_step_actions(
        learning_sample,
        rule_candidates,
        report_preference_candidates,
    )

    return {
        "success": True,
        "data": {
            "revision_diff": revision_diff,
            "feedback_tags": feedback_tags,
            "learning_sample": learning_sample,
            "rule_candidates": rule_candidates,
            "report_preference_candidates": report_preference_candidates,
            "next_step_actions": next_step_actions,
        },
        "error": None,
    }
```

---

## 十五、测试设计

### 15.1 测试目标

- diff 提取正确
- 归因标签合理
- 学习样本评分稳定
- 候选规则结构正确
- 偏好候选结构正确
- 输出包含 `success / data / error`
- 中文正常显示，无乱码

---

### 15.2 测试场景

#### 场景 A：风险等级被人工上调
- 预期：命中 `RISK_UNDER_ESTIMATED`
- 预期：生成 revision diff
- 预期：可形成候选规则

#### 场景 B：人工补充缺失章节
- 预期：命中 `MISSING_DIMENSION` 或 `MISSING_RECOMMENDATION`
- 预期：生成偏好候选

#### 场景 C：只是轻微措辞调整
- 预期：可能命中 `WRONG_TERMINOLOGY` 或 `UNCLEAR_EXPRESSION`
- 预期：学习样本质量分较低，不一定入高质量样本库

#### 场景 D：终稿未确认
- 预期：降低学习样本评分
- 预期：不进入正式候选审核流

#### 场景 E：无 edit_actions，仅有初稿终稿
- 预期：仍可从 JSON diff 中提取主要变化

---

### 15.3 测试检查清单

- [ ] 输出包含 `success`, `data`, `error`
- [ ] `revision_diff` 正常输出
- [ ] `feedback_tags` 正常输出
- [ ] `learning_sample.quality_score` 正常输出
- [ ] `rule_candidates` 结构正确
- [ ] `report_preference_candidates` 结构正确
- [ ] `next_step_actions` 正常输出
- [ ] 中文正常显示，无乱码

---

## 十六、后续演进预留

### 16.1 第二期增强
- 接入前端字段级编辑日志
- 增加管理员审核看板
- 增加高频问题 Top N 统计
- S1 接入相似修订经验检索

### 16.2 第三期增强
- 增加批量规则聚类与审核建议
- 增加组织/角色维度偏好学习
- 与 S6 的审核引导深度联动
- 增加学习结果质量评估报表

### 16.3 长期方向
- 形成“案例学习 + 规则学习 + 偏好学习”的完整闭环
- 基于高质量修订样本持续优化 Prompt / few-shot / 规则体系
- 形成稳定的组织经验沉淀机制，而非依赖个人记忆

---

*文档持续更新中，最后修改：2026-03-25*