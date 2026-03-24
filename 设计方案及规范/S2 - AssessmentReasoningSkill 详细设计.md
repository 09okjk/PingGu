# S2 - AssessmentReasoningSkill 详细设计

> 创建日期：2026-03-24  
> 最后修改：2026-03-24  
> 状态：设计确认（V2）  
> 所属模块：智能评估 Agent — Skills 层

---

## 目录

1. [Skill 定位与职责](#一skill-定位与职责)
2. [整合背景与设计原则](#二整合背景与设计原则)
3. [整体结构：1 个 Skill + 3 个专项 Reference](#三整体结构1-个-skill--3-个专项-reference)
4. [已确认设计决策](#四已确认设计决策)
5. [输入与输出设计](#五输入与输出设计)
6. [执行流程设计](#六执行流程设计)
7. [R3 风险规则库设计](#七r3-风险规则库设计)
8. [R5 工时经验规则库设计](#八r5-工时经验规则库设计)
9. [R6 人力配置规则库设计](#九r6-人力配置规则库设计)
10. [数据库设计建议](#十数据库设计建议)
11. [与 S1 / S5 / S6 / R2 的关系](#十一与-s1--s5--s6--r2-的关系)
12. [对外接口设计](#十二对外接口设计)
13. [开发阶段实现建议](#十三开发阶段实现建议)
14. [后续演进预留](#十四后续演进预留)

---

## 一、Skill 定位与职责

| 项目 | 内容 |
|------|------|
| **Skill 名称** | AssessmentReasoningSkill |
| **整合来源** | 原 `S2 MatchRisksSkill` + 原 `S3 EstimateWorkHoursSkill` + 原 `S4 EstimateManpowerSkill` |
| **核心职责** | 基于结构化需求、历史相似案例和业务规则，输出风险识别结果、工时估算结果与人数推理结果 |
| **调用方** | `S6 GenerateReportSkill` / 上层 Agent |
| **实施阶段** | MVP 必须 |
| **输出边界** | **只输出推理结果，不负责最终任务组织与报告组装** |

### 核心定位

AssessmentReasoningSkill 是智能评估 Agent 中的统一“评估推理层”，负责：

- 读取已确认的需求单结构化结果
- 吸收历史相似案例作为参考依据
- 调用专项规则库完成风险、工时、人数三类推理
- 输出结构化推理结果及置信度说明

它**不负责**：

- 历史案例检索（由 S1 负责）
- 输入解析与确认（由 S5 负责）
- 最终报告字段组织与输出（由 S6 负责）

---

## 二、整合背景与设计原则

### 2.1 整合原因

原方案中的三项能力：

- 风险匹配
- 工时估算
- 人力推理

本质上都属于同一层“评估推理能力”，且三者之间存在明显依赖关系：

```text
历史案例 + 需求结构化结果
    ↓
风险识别
    ↓
工时估算
    ↓
人数推理
    ↓
交给 S6 组织最终报告
```

在当前阶段将三者整合为一个 Skill，更有利于：

- 减少 Skill 数量
- 降低编排复杂度
- 统一输入输出规范
- 提升 MVP 落地效率

---

### 2.2 整合后的边界控制原则

虽然对外整合为一个 Skill，但内部仍保留三个清晰子域：

- 风险推理域
- 工时推理域
- 人力推理域

其对应知识来源保留为三个专项 Reference：

- `R3 风险规则库`
- `R5 工时经验规则库`
- `R6 人力配置规则库`

这样既能统一执行，又便于未来独立演进。

---

## 三、整体结构：1 个 Skill + 3 个专项 Reference

### 3.1 结构示意

```text
┌────────────────────────────────────────────────────┐
│            AssessmentReasoningSkill                │
│                                                    │
│  输入：                                            │
│  - S5 输出的 RequirementItem                       │
│  - S1 输出的 Top-K 历史相似案例                     │
│  - R2 枚举字典与通用规则                            │
│  - R3 风险规则库                                    │
│  - R5 工时经验规则库                                │
│  - R6 人力配置规则库                                │
│                                                    │
│  输出：                                            │
│  - risk_results                                    │
│  - workhour_results                                │
│  - manpower_result                                 │
│  - confidence_summary                              │
│  - reasoning_trace                                 │
└────────────────────────────────────────────────────┘
```

---

### 3.2 三个专项 Reference 的职责

| Reference | 作用 | 当前形式 |
|-----------|------|----------|
| `R3` | 提供风险条目、触发条件、建议措施 | 数据库存储 |
| `R5` | 提供工时经验值与修正因子 | 数据库存储 |
| `R6` | 提供职级覆盖规则、人力推理约束 | 数据库存储 |

---

## 四、已确认设计决策

以下事项已确认，并作为本设计稿的正式约束：

| 编号 | 事项 | 确认结论 |
|------|------|----------|
| 1 | S2 的输出边界 | **S2 只输出推理结果，由 S6 负责最终任务组织** |
| 2 | R5 初始来源 | **完全来自历史数据统计** |
| 3 | S4 当前串行策略 | **默认按“可串行则复用”的简化策略执行，并保留后续扩展空间** |
| 4 | 风险结果内容 | **需要输出建议措施** |
| 5 | 人数结果是否输出保守方案 | **不需要** |
| 6 | 工时输出形式 | **当前先采用“单值 + 置信度”方案** |
| 7 | 是否按业务归口定制推理策略 | **暂不考虑** |
| 8 | R3/R5/R6 存储方式 | **迁移到与 S1 相同的数据库 `pinggu` 中** |
| 9 | reasoning_trace 是否要前端可视化结构 | **不需要** |

---

## 五、输入与输出设计

---

### 5.1 输入结构

```json
{
  "requirement": {
    "requirement_id": "req-001",
    "business_type": {
      "code": "BT0001",
      "name": "轮机"
    },
    "service_desc": {
      "code": "RS0001",
      "name": "二冲程柴油机"
    },
    "service_type": {
      "code": "CS0017",
      "name": "保养10年"
    },
    "equipment_name": {
      "code": "EN0001",
      "name": "主机"
    },
    "equipment_model": {
      "code": "ET000826",
      "name": "MAN B&W-9S90ME-C9.2-TII"
    },
    "equipment_quantity": 1,
    "equipment_unit": {
      "code": "UM0001",
      "name": "台"
    },
    "remark": "内含船厂常规工作，可能存在交叉作业与备件等待。"
  },
  "history_cases": [],
  "options": {
    "output_language": "zh-CN"
  }
}
```

---

### 5.2 输入说明

| 字段 | 必需 | 说明 |
|------|------|------|
| `requirement` | ✅ | 单个已确认的需求项 |
| `history_cases` | ✅ | S1 返回的 Top-K 历史案例 |
| `options.output_language` | ❌ | 输出语言偏好 |

说明：
- R2/R3/R5/R6 不要求由上层直接传入，而应由 Skill 在执行时从数据库读取
- 当前设计假定：输入已由 S5 完成确认，S2 不再负责补问和修订

---

### 5.3 输出结构

```json
{
  "requirement_id": "req-001",
  "status": "ok",
  "risk_results": [
    {
      "risk_id": "RISK-001",
      "risk_name": "船厂交叉作业导致工期延误",
      "risk_level": "high",
      "confidence": "high",
      "trigger_basis": [
        "remark_keyword:交叉作业",
        "history_case:RH-2025-0009611001"
      ],
      "description": "现场存在交叉作业时，可能导致施工窗口受限与工期延误。",
      "suggested_action": "建议预留工期缓冲，并提前确认现场作业窗口。"
    }
  ],
  "workhour_results": [
    {
      "task_tag": "主机常规坞修保养工作",
      "suggested_hours": 110,
      "confidence": "medium",
      "basis": [
        "history_case_avg",
        "r5_rule:WH-001",
        "risk_adjustment:交叉作业"
      ],
      "note": "当前为单值估算结果，后续可升级为区间估算。"
    }
  ],
  "manpower_result": {
    "total_persons": 3,
    "confidence": "medium",
    "basis": [
      "serial_reuse:true",
      "job_level_cover:true"
    ],
    "explanation": "高职级人员可在串行任务中复用承担低职级任务，因此最小总人数为 3。"
  },
  "confidence_summary": {
    "risk": "high",
    "workhour": "medium",
    "manpower": "medium"
  },
  "reasoning_trace": [
    "命中 remark 关键词：交叉作业、备件等待",
    "参考历史案例 RH-2025-0009611001 的风险与人员配置",
    "��时估算采用历史参考值并叠加风险修正",
    "人数推理采用“可串行则复用”的简化规则"
  ],
  "warnings": []
}
```

---

## 六、执行流程设计

### 6.1 总流程

```text
输入 requirement + history_cases
    ↓
Step 1：读取数据库中的 R2 / R3 / R5 / R6
    ↓
Step 2：风险推理
    ↓
Step 3：工时推理
    ↓
Step 4：人数推理
    ↓
Step 5：汇总结果、生成 confidence_summary 和 reasoning_trace
    ↓
输出统一推理结果
```

---

### 6.2 Step 1：上下文准备

执行内容：

1. 校验 requirement 中关键字段是否齐备
2. 读取数据库中的：
   - R2 枚举与通用业务规则
   - R3 风险规则库
   - R5 工时经验规则库
   - R6 人力配置规则库
3. 标准化历史案例中的任务、风险、人员明细结构
4. 从 remark 中提取风险关键词、复杂度信号

输出：
- normalized_requirement
- normalized_history_cases
- context_signals

---

### 6.3 Step 2：风险推理

执行逻辑：

1. 根据 `service_type` / `equipment_name` / `equipment_model` 匹配 R3 风险条目
2. 扫描 remark 中的关键词触发项
3. 从历史案例中提取高频风险提示作为补充证据
4. 对候选风险条目去重、排序、打置信度
5. 为每条风险补充建议措施

输出：
- `risk_results`

说明：
- 风险结果必须包含 `suggested_action`
- 当前阶段不单独设计为独立 Skill，由本 Skill 内部统一执行

---

### 6.4 Step 3：工时推理

执行逻辑：

1. 从历史案例中提取相似任务的工时信息
2. 从 R5 中查找同类任务经验值
3. 根据设备数量和风险信号做简化修正
4. 输出单值工时建议 + 置信度
5. 暂不输出 P50/P80/P95 区间

说明：
- 当前历史统计数据不足，因此采用**单值 + 置信度**
- 后续如数据充分，可升级为区间估算模型

输出：
- `workhour_results`

---

### 6.5 Step 4：人数推理

执行逻辑：

1. 基于任务与工时结果形成待推理任务集合
2. 按工种分组
3. 应用 R6 职级覆盖规则：
   - 高职级可覆盖同工种低职级
   - 跨工种不可替代
4. 当前采用简化规则：
   - **若任务可串行，则允许人员复用**
5. 计算理论最小总人数
6. 输出总人数和解释说明

说明：
- 当前阶段不输出保守方案
- 当前阶段不接入真实员工能力信息
- 必须保留后续增强为“时间窗口显式建模”的扩展空间

输出：
- `manpower_result`

---

### 6.6 Step 5：结果汇总

执行内容：

1. 计算各域置信度汇总
2. 生成 reasoning_trace 文本列表
3. 检查是否存在明显不稳定结果：
   - 历史案例太少
   - 工时数据不足
   - 人数推理依赖过多假设
4. 输出 warnings

---

## 七、R3 风险规则库设计

### 7.1 定位

R3 是 AssessmentReasoningSkill 的风险推理知识库，提供：

- 风险条目定义
- 触发条件
- 风险等级
- 建议措施

---

### 7.2 字段建议

| 字段 | 类型 | 说明 |
|------|------|------|
| `risk_id` | VARCHAR | 风险唯一标识 |
| `risk_name` | VARCHAR | 风险名称 |
| `risk_level` | VARCHAR | 高/中/低 |
| `description` | TEXT | 风险描述 |
| `suggested_action` | TEXT | 建议措施 |
| `service_type_codes` | JSONB | 适用服务类型列表 |
| `equipment_name_codes` | JSONB | 适用设备名称列表 |
| `equipment_model_codes` | JSONB | 适用设备型号列表 |
| `keyword_triggers` | JSONB | 备注关键词触发列表 |
| `is_active` | BOOLEAN | 是否启用 |

---

### 7.3 初始来源

R3 初始数据来源包括：

1. 从历史评估数据中提取高频风险提示
2. 结合业务专家人工整理补充
3. 存储于 `pinggu` 数据库中

---

## 八、R5 工时经验规则库设计

### 8.1 定位

R5 是工时估算使用的经验规则库，当前仅支撑：

- 单值工时建议
- 简化修正因子
- 置信度计算依据

---

### 8.2 字段建议

| 字段 | 类型 | 说明 |
|------|------|------|
| `rule_id` | VARCHAR | 规则唯一标识 |
| `service_type_code` | VARCHAR | 服务类型编码 |
| `equipment_name_code` | VARCHAR | 设备名称编码 |
| `task_tag` | VARCHAR | 任务标签 |
| `work_type_code` | VARCHAR | 工种编码 |
| `baseline_hours` | DECIMAL | 基准工时单值 |
| `quantity_factor` | DECIMAL | 数量修正系数 |
| `risk_adjustments` | JSONB | 风险修正因子列表 |
| `sample_size` | INTEGER | 统计样本数 |
| `is_active` | BOOLEAN | 是否启用 |

---

### 8.3 初始来源

**已确认：R5 初始来源完全来自历史数据统计。**

因此：
- 不建议先手工拍脑袋配置大量经验值
- 可允许极少量人工校正，但不应改变“历史统计为主”的原则

---

### 8.4 当前简化策略

当前只输出：

- `suggested_hours`
- `confidence`

暂不输出：

- P50 / P80 / P95
- 多档位推荐说明
- 复杂分布推断

---

## 九、R6 人力配置规则库设计

### 9.1 定位

R6 是人数推理使用的规则库，提供：

- 职级覆盖关系
- 跨工种替代限制
- 串行复用规则
- 未来扩展到时间窗口建模的预留字段

---

### 9.2 字段建议

#### 方案 A：拆为两张表
1. `manpower_global_rules`
2. `manpower_level_cover_rules`

这是推荐方案。

---

#### `manpower_global_rules`

| 字段 | 类型 | 说明 |
|------|------|------|
| `rule_key` | VARCHAR | 规则键 |
| `rule_value` | VARCHAR | 规则值 |
| `description` | TEXT | 规则说明 |

可存：

- `higher_level_can_cover_lower_level = true`
- `cross_work_type_substitution = false`
- `allow_serial_reuse = true`

---

#### `manpower_level_cover_rules`

| 字段 | 类型 | 说明 |
|------|------|------|
| `work_type_code` | VARCHAR | 工种编码 |
| `higher_level_code` | VARCHAR | 高职级编码 |
| `lower_level_code` | VARCHAR | 可覆盖的低职级编码 |
| `is_active` | BOOLEAN | 是否启用 |

---

### 9.3 当前简化策略

当前人数推理按以下规则执行：

1. 同工种内高职级可覆盖低职级
2. 跨工种不可替代
3. 若任务可串行，则允许人员复用
4. 输出理论最小总人数
5. **不输出保守方案**

---

### 9.4 未来扩展预留

后续可新增字段支持：

- 时间窗口
- 是否必须并行
- 任务依赖关系
- 员工能力数据接入后的真实排班约束

---

## 十、数据库设计建议

### 10.1 数据库归属

**已确认：R3 / R5 / R6 与 S1 的历史数据一起存储在同一个数据库 `pinggu` 中。**

这样有几个好处：

- 避免多库维护
- 便于与 S1 检索结果联动
- 便于统一数据清洗与统计流程
- 便于后续飞轮回流

---

### 10.2 建议表

| 表名 | 用途 |
|------|------|
| `risk_rules` | 存储 R3 风险规则 |
| `workhour_rules` | 存储 R5 工时经验规则 |
| `manpower_global_rules` | 存储全局人力规则 |
| `manpower_level_cover_rules` | 存储同工种职级覆盖规则 |

---

### 10.3 与 S1 数据联动关系

- `evaluation_records` / `evaluation_personnel` 用于历史参考
- `risk_rules` / `workhour_rules` / `manpower_*` 用于评估推理
- 后续可通过离线任务从历史数据定期更新 R3/R5 的种子规则

---

## 十一、与 S1 / S5 / S6 / R2 的关系

### 与 S5 ParseRequirementSkill

S5 负责：
- 原始需求解析
- 用户确认闭环
- 输出标准化 RequirementItem

S2 只接收**已确认**的 RequirementItem。

---

### 与 S1 SearchHistoryCasesSkill

S1 负责：
- 历史相似案例检索
- 返回 Top-K 参考案例与人员明细

S2 不再检索历史数据，而是直接消费 S1 的输出。

---

### 与 R2 枚举字典与通用规则

R2 负责：
- 工种、职级、单位等基础枚举
- 通用业务规则

R3/R5/R6 则是 S2 的专项推理知识库。

---

### 与 S6 GenerateReportSkill

**已确认：S2 只输出推理结果，由 S6 负责最终任务组织。**

即：

- S2 不直接生成最终施工任务结构
- S2 只给出风险、工时、人数等推理结论
- S6 再将这些结论组织进最终评估报告

---

## 十二、对外接口设计

### 12.1 主接口

| 接口 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `reason_assessment(requirement, history_cases)` | 单个需求项 + 历史案例 | 风险/工时/人数推理结果 | 主接口 |

---

### 12.2 可选保留的子接口

即使整合为一个 Skill，也建议内部保留以下逻辑接口，便于测试：

| 接口 | 说明 |
|------|------|
| `match_risks(...)` | 仅执行风险推理 |
| `estimate_workhours(...)` | 仅执行工时推理 |
| `estimate_manpower(...)` | 仅执行人数推理 |

这些接口可不对上层开放，但工程实现上建议保留。

---

## 十三、开发阶段实现建议

### 13.1 MVP 优先级

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0 | R3 数据表建立 | 风险规则先可用 |
| P0 | R6 数据表建立 | 人力规则先可用 |
| P0 | S2 风险推理链路跑通 | MVP 必做 |
| P0 | S2 人数推理链路跑通 | MVP 必做 |
| P1 | R5 历史统计生成逻辑 | 完全来自历史数据 |
| P1 | S2 工时推理简化版 | 单值 + 置信度 |
| P1 | S2 主接口联调 | 与 S1 / S5 / S6 联调 |

---

### 13.2 实现策略建议

#### 风险推理
- 结构化规则命中
- remark 关键词命中
- 历史案例补强
- 输出建议措施

#### 工时推理
- 历史统计优先
- 单值估算
- 输出中明确写明“当前为简化版”

#### 人数推理
- 高职级覆盖低职级
- 串行复用
- 不考虑真实员工与排班
- 输出解释说明

---

### 13.3 工程目录建议

```text
assessment-reasoning-skill/
├── SKILL.md
├── scripts/
│   ├── main.py
│   ├── risk_engine.py
│   ├── workhour_engine.py
│   ├── manpower_engine.py
│   └── db.py
├── references/
│   └── config.md
└── samples/
    ├── sample-input.json
    └── sample-output.json
```

说明：
- 虽然 R3/R5/R6 已迁移到数据库，但 `references/config.md` 仍建议保留，用于说明表结构、初始化方式和字段含义

---

## 十四、后续演进预留

### 14.1 工时估算升级方向

未来可从：
- 单值 + 置信度

升级为：
- P50 / P80 / P95
- 分场景推荐档位
- 更稳健的修正因子体系

---

### 14.2 人数推理升级方向

未来可从：
- 可串行则复用

升级为：
- 显式时间窗口建模
- 并行/串行约束求解
- 真实员工能力数据接入
- 更细粒度排班优化

---

### 14.3 风险推理升级方向

未来可从：
- 规则 + 历史高频风险

升级为：
- 风险模式聚类
- 专家规则动态维护
- 风险等级自动校准

---

*文档持续更新中，最后修改：2026-03-24*
