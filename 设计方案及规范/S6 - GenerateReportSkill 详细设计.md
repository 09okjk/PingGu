# S6 - GenerateReportSkill 详细设计

> 创建日期：2026-03-24  
> 最后修改：2026-03-24  
> 状态：设计确认（MVP）  
> 所属模块：智能评估 Agent — Skills 层

---

## 目录

1. [Skill 定位与职责](#一skill-定位与职责)
2. [设计背景与定位说明](#二设计背景与定位说明)
3. [已确认设计决策](#三已确认设计决策)
4. [整体输入输出定位](#四整体输入输出定位)
5. [报告使用链路与目标用户](#五报告使用链路与目标用户)
6. [整体结构：1 个 Skill + 多来源结果合成](#六整体结构1-个-skill--多来源结果合成)
7. [输入与输出设计](#七输入与输出设计)
8. [报告结构设计（MVP）](#八报告结构设计mvp)
9. [执行流程设计](#九执行流程设计)
10. [结果裁决与冲突处理原则](#十结果裁决与冲突处理原则)
11. [风险章节设计](#十一风险章节设计)
12. [施工任务章节设计](#十二施工任务章节设计)
13. [总计章节设计](#十三总计章节设计)
14. [工具 / 耗材 / 专用工具章节设计](#十四工具--耗材--专用工具章节设计)
15. [设备 / 备件需求章节设计](#十五设备--备件需求章节设计)
16. [置信度设计](#十六置信度设计)
17. [来源标注与可解释性设计](#十七来源标注与可解释性设计)
18. [审核引导设计](#十八审核引导设计)
19. [输出形态设计](#十九输出形态设计)
20. [与 S1 / S2 / S5 / R2 / R4 的关系](#二十与-s1--s2--s5--r2--r4-的关系)
21. [对外接口设计](#二十一对外接口设计)
22. [开发阶段实现建议](#二十二开发阶段实现建议)
23. [工程目录建议](#二十三工程目录建议)
24. [伪代码设计](#二十四伪代码设计)
25. [测试设计](#二十五测试设计)
26. [后续演进预留](#二十六后续演进预留)

---

## 一、Skill 定位与职责

| 项目 | 内容 |
|------|------|
| **Skill 名称** | GenerateReportSkill |
| **编号** | S6 |
| **核心职责** | 基于已确认需求、历史相似案例与评估推理结果，生成最终结构化评估报告草稿 |
| **调用方** | 上层 Agent 主流程 / `assess()` 主接口 |
| **实施阶段** | MVP 必须 |
| **输出边界** | **输出完整评估报告草稿，不直接生成报价单** |
| **报告粒度** | **单个 RequirementItem 对应一份报告（一项一报）** |

### 核心定位

GenerateReportSkill 是智能评估 Agent 中的“**报告合成层 / 结果编排层**”，负责把上游多个 Skill 的结果，整理成：

- 结构稳定
- 可供审核
- 可供服贸使用
- 可作为后续报价依据

的最终评估报告草稿。

### 核心职责

S6 负责：

1. 整合 S5 输出的已确认需求单
2. 整合 S1 返回的历史案例参考
3. 整合 S2 返回的风险 / 工时 / 人数推理结果
4. 组合成统一的评估报告结构
5. 对关键字段输出置信度与来源
6. 检测冲突、缺失、不稳定项
7. 给出人工审核重点提示

### 职责边界

S6：

- **负责最终报告字段组织**
- **负责章节化 / 表格化结构输出**
- **负责字段级置信度标注**
- **负责字段级来源标注**
- **负责审核提示输出**

S6 不负责：

- 原始邮件解析与确认（S5）
- 历史案例检索（S1）
- 风险 / 工时 / 人数底层推理（S2）
- 商务报价金额计算
- 报价项建议生成
- 最终商务承诺
- 实际排班优化

---

## 二、设计背景与定位说明

### 2.1 为什么 S6 必须作为独立 Skill

虽然 S6 的输入来自前置 Skill，但它并不是简单“拼接 JSON”，而是承担一个独立的业务层职责：

> **把机器中间结果转化为业务可消费的评估报告草稿。**

上游输出的特点分别是：

- S5：结构化需求结果
- S1：历史案例参考
- S2：专项推理结果

这些结果本身并不能直接给最终用户使用，因为：

- 粒度不统一
- 可能存在冲突
- 可能存在缺失
- 不符合最终审核与报价准备习惯
- 不适合直接呈现给服贸人员

因此，必须由 S6 做统一收口。

---

### 2.2 S6 在整体链路中的业务位置

该报告的实际使用链路已确认如下：

```text
客户原始需求
    ↓
S5 ParseRequirementSkill
    ↓
S1 SearchHistoryCasesSkill
    ↓
S2 AssessmentReasoningSkill
    ↓
S6 GenerateReportSkill
    ↓
工务人员查看报告
    ↓
与 Agent 对话 / 调整报告内容
    ↓
工务人员审核通过
    ↓
交付服贸人员
    ↓
服贸人员据此生成报价单
```

### 2.3 因此 S6 的核心要求

S6 输出必须同时满足两类用户：

#### 第一层用户：工务人员
重点诉求：
- 能审核
- 能调整
- 能发现问题
- 能定位低置信字段
- 能与 Agent 继续迭代

#### 第二层用户：服贸人员
重点诉求：
- 能快速理解服务内容
- 能获取报价依据
- 能读取结构化表格信息
- 不需要查看底层复杂推理过程

这意味着 S6 输出必须：

- **结构化表格优先**
- 同时保留必要的审核说明
- 不追求长篇 narrative 报告
- 更像“可审核的结构化评估单”

---

## 三、已确认设计决策

以下事项已确认，并作为本设计稿正式约束：

| 编号 | 事项 | 确认结论 |
|------|------|----------|
| 1 | 报告最终偏好形式 | **结构化表格优先** |
| 2 | 报告首先由谁使用 | **先由工务人员审核与调整，再交付服贸人员** |
| 3 | 是否在 S6 中生成报价项建议 | **暂不生成** |
| 4 | 是否航修判断规则 | **取决于 S5 的服务地点类型；若服务地点类型为“港口”，则为航修** |
| 5 | 设备 / 备件需求结构 | **拆分为“客户提供 / 我方提供 / 待确认”三栏** |
| 6 | 工具 / 耗材是否区分 “必需 / 建议” | **不区分** |
| 7 | 是否附带适合报价的摘要文案 | **不需要** |
| 8 | 多服务项报告输出方式 | **一项一报** |
| 9 | S6 是否重新做风险 / 工时 / 人数推理 | **不做，以 S2 为主** |
| 10 | S6 是否负责最终报告组装 | **负责** |

---

## 四、整体输入输出定位

### 4.1 输入定位

S6 的输入必须是：

- **已确认的单个 RequirementItem**
- 该需求项对应的 Top-K 历史案例
- 该需求项对应的 S2 推理结果

即：

> S6 的最小处理单位 = 单个需求项的一次完整报告生成

这与“一项一报”的业务决策保持一致。

---

### 4.2 输出定位

S6 输出的是：

> **单个需求项的结构化评估报告草稿**

该报告不是最终报价单，但应作为：

- 工务审核依据
- 工务调整基础
- 服贸生成报价单的输入依据

---

## 五、报告使用链路与目标用户

### 5.1 使用链路

```text
S6 报告生成
    ↓
工务审核
    ↓
工务与 Agent 交互修订
    ↓
工务审核通过
    ↓
服贸读取结构化报告
    ↓
生成报价单
```

---

### 5.2 对工务人员的价值

S6 报告应帮助工务人员快速确认：

- 风险是否合理
- 任务是否完整
- 人数 / 工时是否可信
- 物料是否遗漏
- 设备 / 备件归属是否清楚
- 哪些字段需要进一步人工修订

---

### 5.3 对服贸人员的价值

服贸人员不关心复杂推理过程，而关心：

- 服务范围
- 工作内容
- 人力投入
- 总工时
- 风险影响
- 物料准备
- 我方需提供什么

因此，S6 输出必须偏“结构化信息单”，而不是大段自由文本。

---

## 六、整体结构：1 个 Skill + 多来源结果合成

### 6.1 结构示意

```text
┌────────────────────────────────────────────────────────────┐
│                 GenerateReportSkill                        │
│                                                            │
│  输入：                                                    │
│  - S5 输出的已确认 RequirementItem                         │
│  - S1 输出的 Top-K 历史相似案例                             │
│  - S2 输出的风险 / 工时 / 人数推理结果                      │
│  - R2 枚举字典与通用规则                                    │
│  - R4 工具/耗材模板（第二期预留）                           │
│                                                            │
│  输出：                                                    │
│  - summary 摘要信息                                        │
│  - report_table 结构化评估报告表格                          │
│  - confidence_summary                                      │
│  - source_summary                                          │
│  - warnings                                                │
│  - review_focus                                            │
└─────────────────────────────────────────────────────────────┘
```

---

### 6.2 合成原则

S6 合成不是平权拼接，而是有明确裁决优先级：

```text
S5 已确认需求
    >
S2 推理结果
    >
S1 历史案例参考
    >
R4 模板参考
    >
占位字段 / 待确认字段
```

---

## 七、输入与输出设计

### 7.1 输入结构

```json
{
  "requirement": {},
  "history_cases": [],
  "assessment_result": {},
  "options": {
    "output_language": "zh-CN",
    "include_source_details": true,
    "include_review_focus": true
  }
}
```

---

### 7.2 输入说明

| 字段 | 必需 | 来源 | 说明 |
|------|------|------|------|
| `requirement` | ✅ | S5 | 单个已确认需求项 |
| `history_cases` | ✅ | S1 | 当前需求项对应的 Top-K 历史案例 |
| `assessment_result` | ✅ | S2 | 当前需求项对应的风险 / 工时 / 人数推理结果 |
| `options.output_language` | ❌ | 上层 Agent | 输出语言 |
| `options.include_source_details` | ❌ | 上层 Agent | 是否输出详细来源 |
| `options.include_review_focus` | ❌ | 上层 Agent | 是否输出审核重点 |

说明：
- S6 不直接消费原始邮件
- S6 不负责补问用户
- 输入必须是已由 S5 确认后的结构化需求项

---

### 7.3 输出顶层结构

```json
{
  "requirement_id": "req-001",
  "status": "ok",
  "report_version": "1.0.0",
  "report_language": "zh-CN",
  "report_type": "service_assessment_draft",
  "report_for": [
    "engineering_review",
    "quotation_preparation"
  ],
  "summary": {},
  "report_table": {},
  "confidence_summary": {},
  "source_summary": {},
  "warnings": [],
  "review_focus": [],
  "metadata": {}
}
```

---

## 八、报告结构设计（MVP）

### 8.1 总体原则

由于已确认“结构化表格优先”，因此 S6 的主体输出采用：

> **结构化评估报告表格（report_table）**

同时辅以：

- 顶层 summary
- warnings
- review_focus
- confidence_summary

---

### 8.2 建议输出结构

```json
{
  "summary": {
    "requirement_summary": "",
    "business_type": {},
    "service_desc": {},
    "service_type": {},
    "service_location_type": {},
    "equipment_name": {},
    "equipment_model": {},
    "equipment_quantity": 1,
    "equipment_unit": {},
    "remark_summary": ""
  },
  "report_table": {
    "risk_rows": [],
    "task_rows": [],
    "totals": {},
    "tool_rows": [],
    "material_rows": [],
    "special_tool_rows": [],
    "spare_parts_or_equipment": {
      "customer_provided": [],
      "provider_provided": [],
      "to_be_confirmed": []
    }
  }
}
```

---

### 8.3 各章节对应关系

| 报告章节 | 主要来源 | 说明 |
|------|------|------|
| `risk_rows` | S2 | 风险结果为主 |
| `task_rows` | S1 + S2 | 任务组织由 S6 完成 |
| `totals` | S2 + S5 | 总人数/总工时由 S2，航修由 S5 |
| `tool_rows` | S1（MVP）/ R4（二期） | 工具建议 |
| `material_rows` | S1（MVP）/ R4（二期） | 耗材建议 |
| `special_tool_rows` | S1（MVP）/ R4（二期） | 专用工具建议 |
| `spare_parts_or_equipment` | S5 + S1 | 三栏拆分 |

---

## 九、执行流程设计

### 9.1 总流程

```text
输入：requirement + history_cases + assessment_result
    ↓
Step 1：输入校验与标准化
    ↓
Step 2：生成 summary
    ↓
Step 3：生成 risk_rows
    ↓
Step 4：生成 task_rows
    ↓
Step 5：生成 totals
    ↓
Step 6：生成 tool_rows / material_rows / special_tool_rows
    ↓
Step 7：生成 spare_parts_or_equipment 三栏
    ↓
Step 8：生成 confidence_summary / source_summary
    ↓
Step 9：生成 warnings / review_focus
    ↓
输出最终结构化评估报告
```

---

### 9.2 Step 1：输入校验与标准化

执行内容：

1. 校验 requirement 是否已确认
2. 校验 assessment_result 是否可用
3. 标准化枚举显示名
4. 清洗 history_cases 中的空值、重复项
5. 将输入转换为统一内部结构

输出：
- `normalized_requirement`
- `normalized_history_cases`
- `normalized_assessment_result`

---

### 9.3 Step 2：生成 summary

Summary 用于快速概览当前需求项，建议包含：

- 需求摘要
- 业务归口
- 服务描述 / 服务类型
- 服务地点类型
- 设备名称 / 型号
- 数量 / 单位
- remark 摘要

注意：
- summary 只做概览，不承担详细推理结果展示
- 不额外生成“报价摘要文案”

---

### 9.4 Step 3：生成风险章节

执行逻辑：

1. 读取 S2 的 `risk_results`
2. 去重同义风险
3. 按风险等级排序
4. 组织为 `risk_rows`
5. 若存在高风险或低置信风险，加入 `review_focus`

---

### 9.5 Step 4：生成施工任务章节

执行逻辑：

1. 从 S1 历史案例中提取候选任务骨架
2. 结合 S2 工时结果组织任务条目
3. 参考历史人员配置生成任务内人力明细
4. 同义任务合并
5. 若历史结构不稳定，则退化为粗粒度任务

说明：
- S2 不负责最终任务组织，因此该步骤是 S6 的核心职责之一
- 任务结构要尽量适合工务审核与服贸阅读

---

### 9.6 Step 5：生成总计章节

执行逻辑：

1. 根据 S5 的 `service_location_type` 判断是否航修
   - 若服务地点类型 = `港口` → `is_voyage_repair = true`
   - 否则为 `false`
2. 从 S2 取 `total_persons`
3. 从 S2 取 `total_hours`
4. 输出总计说明

---

### 9.7 Step 6：生成工具 / 耗材 / 专用工具章节

MVP 阶段：

- 主要根据 S1 Top-K 历史案例归纳生成
- 不区分“必需 / 建议”
- 只输出推荐清单、数量、来源、置信度

第二期：

- 再叠加 R4 标准模板能力

---

### 9.8 Step 7：生成设备 / 备件需求章节

执行逻辑：

1. 从 requirement.remark / 结构化字段中识别客户自备信号
2. 结合历史案例中设备/备件需求模式做辅助判断
3. 按三栏输出：
   - `customer_provided`
   - `provider_provided`
   - `to_be_confirmed`

说明：
- 若证据不足，不强行归类，进入 `to_be_confirmed`

---

### 9.9 Step 8：生成置信度与来源摘要

执行内容：

1. 为各章节计算综合置信度
2. 汇总使用的案例 / 规则 / 推理来源
3. 输出 `confidence_summary`
4. 输出 `source_summary`

---

### 9.10 Step 9：生成审核提示

执行内容：

1. 根据 warnings 输出系统级提醒
2. 根据不稳定字段输出 `review_focus`
3. 为工务人员提供重点审核清单

---

## 十、结果裁决与冲突处理原则

### 10.1 冲突类型

S6 需要处理的典型冲突包括：

1. 历史案例与 S2 推理结果冲突
2. 多个历史案例之间差异较大
3. 当前需求与历史案例模式冲突
4. 设备 / 备件归属不明确
5. 工具 / 耗材频次分布分散

---

### 10.2 裁决优先级

统一采用以下优先级：

```text
已确认需求（S5）
    >
专项推理结果（S2）
    >
高相似历史案例（S1）
    >
模板参考（R4，二期）
    >
待确认占位
```

---

### 10.3 核心裁决原则

#### 原则 1：当前需求优先于历史经验
如果 requirement 已明确说明客户自备，则不能因为历史案例常见我方供件而直接覆盖。

#### 原则 2：S2 的专项结果优先于 S1 的历史参考
尤其在人数、工时、风险判断上，S2 为主，S1 为辅。

#### 原则 3：信息不足时输出待确认，不做伪精确
特别是设备 / 备件需求与航修边界类字段。

---

## 十一、风险章节设计

### 11.1 数据来源

风险章节以 S2 `risk_results` 为主。

---

### 11.2 每条风险建议字段

```json
{
  "risk_id": "RISK-001",
  "risk_name": "船厂交叉作业导致工期延误",
  "risk_level": "high",
  "description": "现场存在交叉作业时，可能导致施工窗口受限与工期延误。",
  "suggested_action": "建议预留工期缓冲，并提前确认现场作业窗口。",
  "confidence": "high",
  "source": [
    "s2_risk:RISK-001",
    "s1_history_case:RH-2025-0009611001"
  ]
}
```

---

### 11.3 输出要求

- 按风险等级排序
- 必须保留 `suggested_action`
- 高风险项自动进入 `review_focus`

---

## 十二、施工任务章节设计

### 12.1 定位

施工任务章节是 S6 最核心的章节之一，因为它直接影响后续报价理解。

---

### 12.2 任务生成原则

任务组织主要依据：

1. S1 历史案例中的任务描述与人员分组
2. S2 的工时结果
3. requirement 的服务描述 / 服务类型 / remark

---

### 12.3 当前阶段组织策略

#### 策略 A：历史任务骨架优先
若 Top-K 历史案例中存在明显一致的任务结构，则沿用该骨架。

#### 策略 B：S2 工时结果补充任务时长
若 S2 `task_tag` 可映射到历史任务，则挂接其工时建议。

#### 策略 C：人力条目参考历史，人数总量以 S2 为准
任务内部人力结构更多参考 S1；
总人数仍以 S2 `manpower_result` 为准。

#### 策略 D：结构不稳定时退化为粗粒度任务
若历史任务分组差异很大，则退化成单任务或少量大任务，并降低置信度。

---

### 12.4 任务条目结构建议

```json
{
  "task_id": "task-001",
  "task_name": "主机常规坞修保养工作",
  "task_description": "依据历史相似案例整理的施工任务。",
  "quantity": 1,
  "unit": {
    "code": "UM0005",
    "name": "台"
  },
  "work_items": [
    {
      "work_type": {
        "code": "JN0001",
        "name": "电气工程师"
      },
      "job_level": {
        "code": "ET3",
        "name": "中级工程师"
      },
      "persons": 1,
      "hours": 12,
      "confidence": "medium",
      "source": [
        "s1_history_case:RH-2025-0009611001"
      ]
    }
  ],
  "suggested_hours": {
    "value": 110,
    "confidence": "medium",
    "source": [
      "s2_workhour:主机常规坞修保养工作"
    ]
  },
  "confidence": "medium",
  "source": [
    "s1_history_cases",
    "s2_reasoning"
  ],
  "notes": []
}
```

---

## 十三、总计章节设计

### 13.1 字段范围

总计章节建议包含：

- 是否航修
- 总小时数
- 总人数
- 说明
- 置信度
- 来源

---

### 13.2 是否航修判断规则

已确认：

> **是否航修取决于 S5 中的服务地点类型。若服务地点类型为“港口”，则判定为航修。**

因此：

```text
service_location_type == 港口
    → is_voyage_repair = true
否则
    → is_voyage_repair = false
```

若 S5 未给出明确服务地点类型：

- 输出低置信
- 加入 warning
- 加入 review_focus

---

### 13.3 总小时数

来源：

- 以 S2 `workhour_results` 为主
- 表示整体施工总时长
- 不是人工时直接相加

---

### 13.4 总人数

来源：

- 以 S2 `manpower_result.total_persons` 为主

说明：

- 总人数不是 task rows 内人数简单求和
- 允许存在串行复用与高职级覆盖低职级

---

### 13.5 建议结构

```json
{
  "is_voyage_repair": {
    "value": true,
    "confidence": "high",
    "source": [
      "s5_service_location_type"
    ]
  },
  "total_hours": {
    "value": 110,
    "confidence": "medium",
    "source": [
      "s2_workhour"
    ]
  },
  "total_persons": {
    "value": 3,
    "confidence": "medium",
    "source": [
      "s2_manpower"
    ]
  },
  "explanation": "总小时数表示整体施工总时长；总人数表示理论最小所需人数，并非各任务人数直接相加。"
}
```

---

## 十四、工具 / 耗材 / 专用工具章节设计

### 14.1 MVP 数据来源

当前阶段主要来自 S1 历史案例：

- `tools_content`
- `materials_content`
- `special_tools_content`

R4 作为第二期增强能力预留。

---

### 14.2 当前阶段规则

- 不区分“必需 / 建议”
- 仅输出推荐清单
- 保留数量、来源、置信度
- 低频项不强行纳入正式表格

---

### 14.3 聚合原则

#### 工具
聚合键：
- `toolName`
- `toolTypeNo`
- `unitMeasurement.no`

#### 耗材
聚合键：
- `toolName`
- `model`
- `unitMeasurement.no`

#### 专用工具
聚合键：
- `toolName`
- `model`
- `unitMeasurement.no`

---

### 14.4 数量策略

优先级建议：

1. Top-1 案例值
2. Top-K 众数
3. Top-K 中位数

如果差异较大：

- 取中位值
- 降低置信度
- 输出 warning

---

## 十五、设备 / 备件需求章节设计

### 15.1 业务定位

该章节直接关系报价边界，因此必须显式拆分为三栏。

---

### 15.2 已确认结构

设备 / 备件需求必须拆分为：

1. `customer_provided`
2. `provider_provided`
3. `to_be_confirmed`

---

### 15.3 判定原则

#### `customer_provided`
满足任一：
- 当前 requirement 明确说明客户自备 / 客户已有
- S5 确认中已明确归属为客户提供

#### `provider_provided`
满足任一：
- requirement 明确说明需我方提供
- 历史高相似案例中稳定出现且当前场景未出现冲突信号

#### `to_be_confirmed`
满足任一：
- 当前信息不足
- 历史案例分歧大
- requirement 未明确说明
- 当前 remark 与历史模式冲突

---

### 15.4 输出结构建议

```json
{
  "customer_provided": [
    {
      "item_name": "备用阀件",
      "confidence": "medium",
      "source": [
        "s5_requirement"
      ],
      "notes": []
    }
  ],
  "provider_provided": [
    {
      "item_name": "检测设备",
      "confidence": "low",
      "source": [
        "s1_history_case:RH-2025-0009611001"
      ],
      "notes": []
    }
  ],
  "to_be_confirmed": [
    {
      "item_name": "专用备件包",
      "confidence": "low",
      "source": [
        "history_cases"
      ],
      "notes": [
        "历史案例存在类似需求，但当前需求未明确。"
      ]
    }
  ]
}
```

---

## 十六、置信度设计

### 16.1 为什么 S6 仍需单独输出置信度

虽然 S2 已输出推理置信度，但 S6 仍需提供“报告字段层置信度”，因为：

- S6 生成了新的组织结果
- 施工任务、物料建议、设备 / 备件归属并不完全等价于 S2 输出
- 同一字段可能由多个来源共同支持

---

### 16.2 置信度分层

#### 高置信（high）
- 当前需求明确
- S2 高置信
- S1 高相似案例一致性高
- 无明显冲突

#### 中置信（medium）
- 主要由历史案例 + 推理结果综合得出
- 有依据但仍建议人工快速审核

#### 低置信（low）
- 历史案例少
- 依赖弱信号
- 多来源存在冲突
- 当前字段仅为暂时性组织结果

---

### 16.3 顶层汇总建议

```json
{
  "risks": "high",
  "tasks": "medium",
  "totals": "medium",
  "tools": "medium",
  "materials": "medium",
  "special_tools": "low",
  "spare_parts_or_equipment": "low"
}
```

---

## 十七、来源标注与可解释性设计

### 17.1 来源编码建议

- `s5_requirement`
- `s5_service_location_type`
- `s1_history_case:<case_id>`
- `s2_risk:<risk_id>`
- `s2_workhour:<task_tag>`
- `s2_manpower`
- `r4_template:<template_id>`
- `manual_placeholder`

---

### 17.2 source_summary 建议

```json
{
  "history_case_ids": [
    "RH-2025-0009611001",
    "RH-2025-0009571001"
  ],
  "risk_rule_ids": [
    "RISK-001",
    "RISK-003"
  ],
  "workhour_rule_ids": [
    "WH-001"
  ],
  "used_reference_types": [
    "requirement",
    "history_cases",
    "assessment_reasoning"
  ]
}
```

---

### 17.3 输出要求

- 风险、任务、总计、物料、备件三栏都应尽量带 source
- 低置信字段尤其必须标注来源

---

## 十八、审核引导设计

### 18.1 warnings 与 review_focus 的区别

#### warnings
系统侧提示，偏数据稳定性：

- 历史案例不足
- 工时结果稳定性一般
- 备件归属不明确
- 航修判断信息缺失

#### review_focus
给工务人员的业务审核重点：

- 请确认设备 / 备件由谁提供
- 请确认任务拆分是否完整
- 请确认交叉作业风险是否影响工期
- 请确认特殊工具是否可现场获取

---

### 18.2 输出示例

```json
{
  "warnings": [
    {
      "code": "LOW_HISTORY_CASE_COVERAGE",
      "message": "历史相似案例数量不足，任务组织与物料推荐稳定性有限。",
      "severity": "medium"
    }
  ],
  "review_focus": [
    "请重点确认设备/备件归属是否完整。",
    "请确认总小时数是否需考虑现场交叉作业影响。",
    "请确认专用工具是否可由现场提供。"
  ]
}
```

---

## 十九、输出形态设计

### 19.1 输出形态原则

已确认：

> **结构化表格优先**

因此 S6 输出应以 `report_table` 为主体，而不是大段 Markdown 报告正文。

---

### 19.2 为什么采用结构化表格优先

原因：

1. 更适合工务审核逐项查看
2. 更适合服贸读取并据此报价
3. 更适合后续前端渲染
4. 更适合作为标准化中间结构沉淀

---

### 19.3 当前阶段不做的形态

- 不输出长篇 narrative 报告
- 不生成报价项建议表
- 不生成正式商务文案

---

## 二十、与 S1 / S2 / S5 / R2 / R4 的关系

### 与 S5 ParseRequirementSkill

S5 负责：

- 需求解析
- 交互确认
- 输出已确认 RequirementItem
- 提供服务地点类型

S6 使用 S5 结果作为当前需求的唯一事实输入来源。

---

### 与 S1 SearchHistoryCasesSkill

S1 负责：

- 检索历史案例
- 返回任务、风险、人员、工具、耗材等参考信息

S6 不重新检索，只消费其结果。

---

### 与 S2 AssessmentReasoningSkill

S2 负责：

- 风险推理
- 工时推理
- 人数推理

S6 以其作为专项结果主来源，不重复做底层推理。

---

### 与 R2 枚举字典与通用规则

R2 负责：

- 名称标准化
- 枚举合法性
- 单位与术语统一

S6 使用其完成显示名统一与输出格式标准化。

---

### 与 R4 工具 / 耗材模板

当前阶段不强依赖 R4。

第二期中：

- R4 可增强工具 / 耗材 / 专用工具章节质量
- 与历史案例推荐形成“双来源支撑”

---

## 二十一、对外接口设计

### 21.1 主接口

| 接口 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `generate_report(requirement, history_cases, assessment_result)` | 单个需求项 + 历史案例 + 推理结果 | 单个需求项的完整评估报告草稿 | 主接口 |

---

### 21.2 输入输出原则

- 一次只处理一个 RequirementItem
- 输出一份完整报告
- 多服务项由上层 Agent 循环调用 S6 实现

---

## 二十二、开发阶段实现建议

### 22.1 MVP 优先级

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0 | 定义 S6 输出 JSON Schema | 先冻结结构 |
| P0 | 实现 summary / risk_rows / totals | 跑通主链路 |
| P0 | 接通 S5 / S1 / S2 输入 | 联调必需 |
| P1 | 实现 task_rows | S6 核心 |
| P1 | 实现工具 / 耗材 / 专用工具聚合 | MVP 需要 |
| P1 | 实现设备 / 备件三栏输出 | MVP 需要 |
| P1 | 实现 warnings / review_focus | 提升审核可用性 |

---

### 22.2 实现策略建议

#### 风险章节
- 直接消费 S2
- 做展示整理、排序、去重

#### 任务章节
- 历史任务骨架优先
- S2 工时补足
- 人力结构参考历史

#### 总计章节
- 航修由 S5 决定
- 人数 / 工时由 S2 决定

#### 物料章节
- 先做历史聚合版
- R4 延后接入

#### 备件章节
- 先做三栏归类
- 归类不清则进入待确认

---

## 二十三、工程目录建议

```text
generate-report-skill/
├── SKILL.md
├── scripts/
│   ├── main.py
│   ├── report_builder.py
│   ├── summary_builder.py
│   ├── risk_section.py
│   ├── task_section.py
│   ├── totals_section.py
│   ├── materials_section.py
│   ├── spare_parts_section.py
│   ├── confidence.py
│   ├── sources.py
│   └── utils.py
├── references/
│   ├── config.md
│   ├── output.schema.json
│   └── report-field-guidelines.md
└── samples/
    ├── sample-input.json
    └── sample-output.json
```

---

## 二十四、伪代码设计

```python
def generate_report(requirement, history_cases, assessment_result, options=None):
    options = options or {}

    normalized_requirement = normalize_requirement(requirement)
    normalized_history_cases = normalize_history_cases(history_cases)
    normalized_assessment = normalize_assessment(assessment_result)

    warnings = []

    summary = build_summary(
        normalized_requirement,
        normalized_history_cases,
    )

    risk_rows = build_risk_rows(
        normalized_assessment,
        warnings,
    )

    task_rows = build_task_rows(
        normalized_requirement,
        normalized_history_cases,
        normalized_assessment,
        warnings,
    )

    totals = build_totals(
        normalized_requirement,
        normalized_assessment,
        task_rows,
        warnings,
    )

    tool_rows = build_tool_rows(
        normalized_history_cases,
        warnings,
    )

    material_rows = build_material_rows(
        normalized_history_cases,
        warnings,
    )

    special_tool_rows = build_special_tool_rows(
        normalized_history_cases,
        warnings,
    )

    spare_parts_or_equipment = build_spare_parts_or_equipment(
        normalized_requirement,
        normalized_history_cases,
        warnings,
    )

    confidence_summary = build_confidence_summary(
        risk_rows,
        task_rows,
        totals,
        tool_rows,
        material_rows,
        special_tool_rows,
        spare_parts_or_equipment,
    )

    source_summary = build_source_summary(
        normalized_history_cases,
        normalized_assessment,
    )

    review_focus = build_review_focus(
        normalized_requirement,
        normalized_assessment,
        task_rows,
        totals,
        spare_parts_or_equipment,
        warnings,
    )

    return {
        "requirement_id": normalized_requirement["requirement_id"],
        "status": "ok",
        "report_version": "1.0.0",
        "report_language": options.get("output_language", "zh-CN"),
        "report_type": "service_assessment_draft",
        "report_for": [
            "engineering_review",
            "quotation_preparation"
        ],
        "summary": summary,
        "report_table": {
            "risk_rows": risk_rows,
            "task_rows": task_rows,
            "totals": totals,
            "tool_rows": tool_rows,
            "material_rows": material_rows,
            "special_tool_rows": special_tool_rows,
            "spare_parts_or_equipment": spare_parts_or_equipment
        },
        "confidence_summary": confidence_summary,
        "source_summary": source_summary,
        "warnings": warnings,
        "review_focus": review_focus,
        "metadata": {
            "generator_version": "1.0.0"
        }
    }
```

---

## 二十五、测试设计

### 25.1 测试目标

- 输出结构稳定
- 支持一项一报
- 航修判断正确
- 总人数 / 总工时来源正确
- 三栏备件结构正确
- 工具 / 耗材 / 专用工具可聚合
- 低置信项能正确进入审核提示

---

### 25.2 测试场景

#### 场景 A：标准高置信场景
- S5 字段完整
- S1 有 5 条高相似案例
- S2 结果完整
- 预期：主字段为高/中置信

#### 场景 B：服务地点类型 = 港口
- 预期：`is_voyage_repair = true`

#### 场景 C：备件归属不明确
- 预期：进入 `to_be_confirmed`

#### 场景 D：历史工具推荐差异较大
- 预期：仅保留稳定项，输出 warning

#### 场景 E：任务骨架不稳定
- 预期：退化为粗粒度任务，并降低置信度

---

### 25.3 测试检查清单

- [ ] 输出包含 `report_table`
- [ ] `risk_rows` 正常输出
- [ ] `task_rows` 正常输出
- [ ] `totals.is_voyage_repair` 判断正确
- [ ] `spare_parts_or_equipment` 含三栏
- [ ] 关键字段包含 `confidence`
- [ ] 关键字段包含 `source`
- [ ] 低置信字段进入 `review_focus`
- [ ] 中文正常显示，无乱码

---

## 二十六、后续演进预留

### 26.1 第二期
- 接入 R4 工具 / 耗材模板
- 提升任务组织稳定性
- 优化多语言显示
- 增强审核引导

### 26.2 第三期
- 与报价模块对接
- 支持字段级人工修订回流
- 统计高频修改字段
- 优化任务骨架模板

### 26.3 长期方向
- 基于工务人员修改记录持续优化 S6
- 优化设备 / 备件归属判断
- 优化物料推荐精度
- 形成更稳定的“评估报告 → 报价依据”中间层

---

*文档持续更新中，最后修改：2026-03-24*