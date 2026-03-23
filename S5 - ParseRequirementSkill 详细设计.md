# S5 - ParseRequirementSkill 详细设计

> 创建日期：2026-03-23  
> 最后修改：2026-03-23  
> 状态：设计确认  
> 所属模块：智能评估 Agent — Skills 层

---

## 目录

1. [Skill 定位与职责](#一skill-定位与职责)
2. [输入特征分析](#二输入特征分析)
3. [核心挑战：多服务项拆分](#三核心挑战多服务项拆分)
4. [R2 枚举字典的使用方式](#四r2-枚举字典的使用方式)
5. [LLM 调用策略](#五llm-调用策略)
6. [处理流程设计](#六处理流程设计)
7. [输入输出定义](#七输入输出定义)
8. [LLM Prompt 设计](#八llm-prompt-设计)
9. [校验与归一化逻辑](#九校验与归一化逻辑)
10. [Skill 逻辑伪代码](#十skill-逻辑伪代码)
11. [返回结果结构示例](#十一返回结果结构示例)
12. [异常处理与降级策略](#十二异常处理与降级策略)
13. [OpenClaw Skill 目录结构](#十三openclaw-skill-目录结构)
14. [SKILL.md 设计](#十四skillmd-设计)
15. [与后续 Skill 的接口衔接](#十五与后续-skill-的接口衔接)
16. [扩展性预留](#十六扩展性预留)
17. [待确认事项](#十七待确认事项)

---

## 一、Skill 定位与职责

| 项目 | 内容 |
|------|------|
| **Skill 名称** | ParseRequirementSkill |
| **编号** | S5 |
| **核心职责** | 接收自然语言描述的原始需求（通常为客户邮件内容），执行多服务项识别与拆分、枚举映射、备注 NLU 提取，输出一个或多个标准化的 `ParsedServiceItem`，供后续 S1/S2/S4/S6 消费 |
| **调用方** | 智能评估 Agent 编排层（**第一步必调**，是整个 Agent 流程的入口 Skill） |
| **Skill 类型** | **纯推理 Skill**（LLM NLU + 枚举匹配逻辑，无外部数据库依赖） |
| **LLM 依赖** | 使用 Agent 当前配置的模型，不单独配置 |
| **实施阶段** | MVP 必须 |

### 为什么 S5 必须最先执行

```
用户提交原始需求（邮件文本）
        ↓
  ┌─────────────────────────┐
  │  S5 ParseRequirementSkill │ ← 第一步：解析 + 拆分
  └─────────────────────────┘
        ↓ 输出 N 个 ParsedServiceItem
  ┌─────────────────────────┐
  │  对每个 ServiceItem 分别  │ ← 后续步骤
  │  执行 S1 → S2 → S4 → S6 │
  └─────────────────────────┘
```

S5 的输出是所有后续 Skill 的**输入基础**：
- S1 需要 `business_type` + `service_desc_code` 才能检索
- S2 需要结构化的服务类型 + 设备信息才能匹配风险
- S4 需要任务维度信息才能推理人力
- S6 需要完整的解析结果才能合成报告

**没有 S5 的输出，后续 Skill 均无法启动。**

### 为什么是 Skill 而不是 Reference

| 对比维度 | 作为 Reference | 作为 Skill |
|---------|---------------|-----------|
| 自然语言理解 | 无法执行（Reference 不含执行逻辑） | 调用 LLM 做多语言 NLU |
| 多服务项拆分 | 无法识别邮件中的多个服务项 | LLM 语义理解 + 枚举匹配，自动拆分 |
| 枚举映射 | 只能被动注入字典 | 主动将自然语言映射为编码，报告匹配置信度 |
| 异常处理 | 无法中止流程 | 关键信息无法识别时返回警告，引导人工介入 |

---

## 二、输入特征分析

### 2.1 输入不是标准表单

用户输入**不是**结构化的字段表单，而是：
- 客户发来的原始邮件（英文为主，可能含中/日/韩文）
- 业务人员附加的简短说明
- 自然语言描述，可能带有行业专业术语
- 长度通常在几十到几百个单词

### 2.2 典型输入示例

**示例 1：单服务项**
```
Dear team,

We need health check service for our main engine 5S50ME-B during 
the upcoming drydocking in Singapore. Please advise on scheduling.

Best regards
```

**示例 2：多服务项（需拆分）**
```
Hi,

During our vessel's scheduled drydocking, we need the following services:
1. Main engine overhaul for 9K98ME-C, including piston inspection
2. Boiler safety valve replacement and testing
3. ICCP system maintenance

The vessel will be at shipyard from April 15-30. 
Please provide assessment asap.

Thanks
```

**示例 3：中文邮件**
```
您好，

我司船舶将于下月进坞，需要以下服务：
- 主机（MAN B&W 6S50MC-C）坞修保养
- 发电机组检修（2台）
- 锅炉安全阀更换

请尽快安排技术评估。
```

### 2.3 输入特征总结

| 特征 | 说明 |
|------|------|
| 格式 | 非结构化自然语言，邮件体 |
| 语言 | 英文为主，含简体中文、繁体中文、韩语、日语 |
| 长度 | 几十～几百单词，不会很长 |
| 服务项数量 | 可能 1 个，也可能包含多个服务需求 |
| 专业术语 | 含设备型号、工种名称等行业术语 |
| 附加信息 | 可能包含时间要求、地点、特殊约束等 |

---

## 三、核心挑战：多服务项拆分

### 3.1 业务背景

用户的原始邮件可能包含**多个服务项**。业务人员在处理时，会根据需要的服务项创建**多个需求单**，每个服务项对应一个需求单。

例如：邮件提到"主机保养 + 锅炉维修 + ICCP 检查"，应拆分为 **3 个独立的服务项**。

### 3.2 拆分依据

拆分的核心依据是 **R2 服务描述枚举**：
- 每个服务项应对应 R2 中**一个**服务描述（service_description）
- 不同设备大类（主机 / 锅炉 / 发电机 / 电气系统等）通常对应不同的服务描述
- 同一设备大类下的不同工作内容（保养 / 维修 / 更换）可能对应不同的服务类型（service_type）

### 3.3 拆分规则

```
规则 1：不同设备大类 → 不同服务项
  例：主机 + 锅炉 → 2 个服务项

规则 2：同一设备大类、不同服务类型 → 根据业务判断
  例：主机健康检查 + 主机坞修保养 → 2 个服务项
  例：主机坞修保养（含活塞检查）→ 1 个服务项（活塞检查是保养的子任务）

规则 3：无法确定的拆分 → 标记为 ambiguous，由业务人员确认
```

### 3.4 拆分流程

```
原始邮件文本
    ↓
LLM 第一轮分析：识别邮件中提及的所有服务需求
    ↓
提取候选列表：
  [{
    raw_description: "Main engine overhaul for 9K98ME-C",
    equipment_mentioned: "9K98ME-C",
    action_described: "overhaul, piston inspection"
  }, ...]
    ↓
枚举匹配：每个候选 → 在 R2 服务描述枚举中查找最佳匹配
    ↓
输出 N 个 ParsedServiceItem（每个对应一个需求单）
```

---

## 四、R2 枚举字典的使用方式

### 4.1 R2 是全局共享的 Reference，不是每个 Skill 各自复制

```
项目根目录/
├── references/
│   └── R2-enums/                    ← 全局唯一，所有 Skill 共享
│       ├── service_descriptions.json
│       ├── service_types.json
│       ├── business_units.json
│       ├── equipment_models.json
│       ├── work_types.json
│       ├── job_levels.json
│       └── measurement_units.json
├── search-history-cases-skill/       ← S1（引用 R2，不复制）
├── parse-requirement-skill/          ← S5（引用 R2，不复制）
└── ...
```

### 4.2 各 Skill 如何使用 R2

| Skill | 使用 R2 的方式 | 使用目的 |
|-------|--------------|---------|
| **S5** | 读取枚举 JSON 做映射匹配 + 注入 LLM prompt 作为候选列表 | 将自然语言映射为编码 |
| **S1** | 不直接使用 R2（S5 已完成映射） | — |
| **S2** | 读取风险触发条件中的枚举关联 | 匹配风险条目 |
| **S4** | 读取职级覆盖规则、工种枚举 | 人力调度推理 |
| **S6** | 读取枚举做输出字段校验 | 报告合成时的格式校验 |

### 4.3 S5 使用 R2 的具体方式

S5 有两种使用 R2 的路径（并行）：

**路径 A：注入 LLM Prompt**
- 将 R2 服务描述枚举的 `[{code, name}]` 列表注入 prompt
- LLM 根据邮件内容 + 枚举列表做匹配
- 适合模糊语义匹配场景

**路径 B：规则匹配兜底**
- LLM 返回的匹配结果，用规则逻辑二次验证
- 确保返回的 code 确实存在于 R2 中
- 处理 LLM 可能的幻觉（返回不存在的编码）

### 4.4 R2 枚举字典格式约定（MVP 默认数据）

> 以下为占位数据，后续拿到真实枚举内容后自行替换。

#### service_descriptions.json

```json
[
  {"code": "RS0000000001", "name": "二冲程柴油机", "business_type": "轮机"},
  {"code": "RS0000000002", "name": "四冲程柴油机", "business_type": "轮机"},
  {"code": "RS0000000003", "name": "锅炉", "business_type": "轮机"},
  {"code": "RS0000000004", "name": "发电机组", "business_type": "电气"},
  {"code": "RS0000000005", "name": "燃油系统", "business_type": "轮机"},
  {"code": "RS0000000006", "name": "ICCP系统", "business_type": "电气"},
  {"code": "RS0000000007", "name": "自动化控制系统", "business_type": "电气"},
  {"code": "RS0000000008", "name": "阀门", "business_type": "轮机"},
  {"code": "RS0000000009", "name": "管路系统", "business_type": "轮机"},
  {"code": "RS0000000010", "name": "甲板机械", "business_type": "轮机"}
]
```

#### service_types.json

```json
[
  {"code": "CS0001", "name": "维修"},
  {"code": "CS0002", "name": "更换"},
  {"code": "CS0003", "name": "检测"},
  {"code": "CS0004", "name": "安装"},
  {"code": "CS0005", "name": "调试"},
  {"code": "CS0006", "name": "健康检查"},
  {"code": "CS0007", "name": "坞修保养"},
  {"code": "CS0008", "name": "航修"},
  {"code": "CS0009", "name": "技术支持"},
  {"code": "CS0010", "name": "现场检验"}
]
```

#### equipment_models.json

```json
[
  {"code": "ET000000000001", "name": "5S50ME-B", "parent_desc_code": "RS0000000001"},
  {"code": "ET000000000002", "name": "9K98ME-C", "parent_desc_code": "RS0000000001"},
  {"code": "ET000000000003", "name": "6S50MC-C", "parent_desc_code": "RS0000000001"},
  {"code": "ET000000000004", "name": "MAN B&W-9S90ME-C9.2-TII", "parent_desc_code": "RS0000000001"},
  {"code": "ET000000000005", "name": "6S50MC", "parent_desc_code": "RS0000000001"}
]
```

#### business_units.json

```json
[
  {"code": "BU001", "name": "轮机部", "business_type": "轮机"},
  {"code": "BU002", "name": "电气部", "business_type": "电气"}
]
```

#### measurement_units.json

```json
[
  {"code": "UM0001", "name": "个"},
  {"code": "UM0002", "name": "台"},
  {"code": "UM0003", "name": "套"},
  {"code": "UM0005", "name": "台"},
  {"code": "UM0018", "name": "瓶"},
  {"code": "UM0028", "name": "千克"},
  {"code": "UM0150", "name": "次"}
]
```

---

## 五、LLM 调用策略

### 5.1 不单独配置 LLM

S5 **不**自行管理 LLM 连接。LLM 调用由上层 Agent 编排层统一处理：

```
方式 A（推荐，MVP 阶段）：
  S5 生成结构化 prompt → 交给 Agent 编排层调用 LLM → 编排层将 LLM 响应传回 S5 → S5 解析响应

方式 B（Skill 独立运行时的降级方案）：
  S5 通过环境变量读取 Agent 的 LLM 配置（如 LLM_API_KEY）
  仅用于独立调试/测试，正式编排时走方式 A
```

### 5.2 Prompt 策略

S5 只需做**一次** LLM 调用（单轮），完成以下所有任务：
1. 识别邮件中的服务项并拆分
2. 每个服务项匹配服务描述/服务类型枚举
3. 提取设备信息
4. 提取备注级补充信息（紧迫性、特殊要求等）

将枚举列表注入 prompt，让 LLM 在有限候��集中选择，而不是自由生成。

### 5.3 Token 预算

| 项目 | 估算 |
|------|------|
| 输入 prompt（系统指令 + 枚举列表） | ~800-1200 tokens |
| 用户邮件文本 | ~100-500 tokens |
| LLM 输出（结构化 JSON） | ~500-1500 tokens |
| **总计** | ~1500-3200 tokens |

邮件不会很长（最多几百单词），枚举列表有限，单次调用 token 消耗可控。

---

## 六、处理流程设计

```
输入：原始邮件文本（自然语言）

        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1：加载 R2 枚举字典                                 │
│  读取全局 R2 枚举 JSON 文件（服务描述、服务类型、设备型号等）│
│  构建查找索引（code→name、name→code）                     │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  Step 2：LLM 分析（单次调用）                              │
│                                                         │
│  2.1 构建 Prompt                                        │
│      → 系统指令：角色定义 + 输出格式要求                    │
│      → 注入 R2 枚举列表作为候选集                          │
│      → 注入原始邮件文本                                   │
│                                                         │
│  2.2 LLM 返回结构化 JSON                                 │
│      → 识别的服务项列表（1~N 个）                          │
│      → 每个服务项的枚举匹配结果                            │
│      → 设备信息                                          │
│      → 备注级提取（紧迫性、特殊要求等）                     │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  Step 3：校验与归一化（规则逻辑，不调 LLM）                 │
│                                                         │
│  3.1 枚举匹配验证                                        │
│      → LLM 返回的 code 是否存在于 R2 中                   │
│      → 不存在时：按 name 模糊匹配兜底                      │
│      → 仍无匹配：标记 low_confidence                      │
│                                                         │
│  3.2 业务归口自动推导                                     │
│      → 从匹配的 service_description 中取 business_type    │
│      → 无需用户手动指定                                   │
│                                                         │
│  3.3 级联关系校验                                        │
│      → 设备型号是否属于对应的服务描述类别                   │
│      → 不匹配时标记 warning                               │
│                                                         │
│  3.4 置信度计算                                          │
│      → 每个字段标注 high / medium / low 置信度             │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  Step 4：输出组装                                        │
│                                                         │
│  4.1 为每个服务项生成 ParsedServiceItem                   │
│  4.2 为每个服务项预组装 S1 检索参数（search_params）        │
│  4.3 生成整体解析报告（含拆分说明、校验结果）               │
└─────────────────────────────────────────────────────────┘

输出：ParsedRequirementResult（含 N 个 ParsedServiceItem）
```

---

## 七、输入输出定义

### 7.1 输入

```json
{
  "raw_text": "原始邮件文本（自然语言，多语言）",
  "submitted_by": "提交人姓名（可选，用于追踪）",
  "submitted_at": "提交时间（可选，ISO 8601）"
}
```

只有 `raw_text` 是必填项。

### 7.2 输出

```typescript
interface ParsedRequirementResult {
  // ===== 元信息 =====
  skill: "ParseRequirementSkill";
  version: "1.0.0";
  
  // ===== 输入回显 =====
  raw_text: string;              // 原始输入文本

  // ===== 全局分析结果 =====
  detected_language: string;     // 检测到的主要语言：en / zh-CN / zh-TW / ko / ja
  service_item_count: number;    // 识别出的服务项数量
  split_reasoning: string;       // 拆分依据的自然语言说明

  // ===== 全局补充信息（跨服务项共享） =====
  global_context: {
    urgency_level: "high" | "medium" | "low" | "unknown";
    urgency_signals: string[];           // 紧迫性判断依据（原文片段）
    time_constraints: string | null;     // 时间约束（如 "April 15-30"）
    location: string | null;             // 地点信息（如 "Singapore"）
    special_requirements: string[];      // 通用特殊��求
    additional_context: string | null;   // 其他有价值的补充信息
  };

  // ===== 拆分后的服务项列表 =====
  service_items: ParsedServiceItem[];

  // ===== 整体校验结果 =====
  validation: {
    is_valid: boolean;            // 至少有 1 个 service_item 是有效的
    total_errors: number;
    total_warnings: number;
  };
}

interface ParsedServiceItem {
  // ===== 服务项标识 =====
  item_index: number;             // 从 1 开始的序号
  raw_description: string;        // 从邮件中提取的该服务项原始描述

  // ===== 枚举匹配结果 =====
  business_type: string;          // 业务归口，如 "轮机" / "电气"（从服务描述自动推导）
  
  service_desc: {
    code: string | null;          // 服务描述编码，如 "RS0000000001"
    name: string | null;          // 服务描述名称，如 "二冲程柴油机"
    confidence: "high" | "medium" | "low";
    match_reason: string;         // 匹配依据说明
  };

  service_type: {
    code: string | null;          // 服务类型编码，如 "CS0007"
    name: string | null;          // 服务类型名称，如 "坞修保养"
    confidence: "high" | "medium" | "low";
    match_reason: string;
  } | null;                       // 无法识别时为 null

  // ===== 设备信息 =====
  equipment: {
    model_code: string | null;    // 设备型号编码
    model_name: string | null;    // 设备型号名称（原文提取）
    manufacturer: string | null;  // 厂家
    qty: number | null;           // 数量
    unit: string | null;          // 单位
    confidence: "high" | "medium" | "low";
  };

  // ===== 该服务项的特定备注 =====
  item_notes: {
    fault_description: string | null;    // 故障/问题描述
    work_scope: string[];                // 工作范围描述
    item_special_requirements: string[]; // 该项特有的特殊要求
  };

  // ===== S1 检索参数预组装 =====
  search_params: {
    business_type: string;
    service_desc_code: string;
    service_type_code: string | null;
    equipment_model_code: string | null;
    task_description: string | null;
    remark: string | null;
  };

  // ===== 该服务项的校验结果 =====
  validation: {
    is_valid: boolean;
    errors: ValidationIssue[];
    warnings: ValidationIssue[];
  };
}

interface ValidationIssue {
  field: string;
  type: "missing" | "invalid" | "ambiguous" | "low_confidence";
  message: string;
  suggestion?: string;
}
```

---

## 八、LLM Prompt 设计

### 8.1 System Prompt

```
你是一名专业的船舶服务评估助手。你的任务是分析客户的服务需求邮件，从中识别所有的服务项并结构化输出。

你必须：
1. 识别邮件中提到的所有独立服务需求
2. 每个服务需求对应一个"服务项"
3. 将每个服务项匹配到提供的枚举列表中最合适的选项
4. 提取设备信息、工作范围、特殊要求等
5. 严格按照指定的 JSON 格式输出

拆分规则：
- 不同设备大类（如主机、锅炉、发电机）→ 拆分为不同服务项
- 同一设备大类的不同独立工作内容（如"检查"和"更换"是不同性质的服务）→ 酌情拆分
- 同一工作中包含的子任务（如"保养含活塞检查"）→ 不拆分，归入同一服务项的工作范围
- 无法确定是否应拆分的 → 按独立服务项处理，在 match_reason 中说明
```

### 8.2 User Prompt 模板

```
## 可选的服务描述（从以下列表中选择最匹配的）：
{service_descriptions_list}

## 可选的服务类型（从以下列表中选择最匹配的）：
{service_types_list}

## 已知的设备型号（如果邮件中提到的型号在此列表中，请匹配）：
{equipment_models_list}

---

## 客户邮件内容：
{raw_text}

---

请分析以上邮件，按以下 JSON 格式输出：

```json
{
  "detected_language": "en|zh-CN|zh-TW|ko|ja",
  "service_items": [
    {
      "raw_description": "从邮件中提取的该服务项原文描述",
      "service_desc_match": {
        "code": "匹配的服务描述编码",
        "name": "匹配的服务描述名称",
        "confidence": "high|medium|low",
        "match_reason": "为什么选择这个匹配"
      },
      "service_type_match": {
        "code": "匹配的服务类型编码或null",
        "name": "匹配的服务类型名称或null",
        "confidence": "high|medium|low",
        "match_reason": "匹配依据"
      },
      "equipment": {
        "model_name": "从邮件中识别的设备型号文本，无则null",
        "model_code": "匹配的设备型号编码，无匹配则null",
        "manufacturer": "厂家，无则null",
        "qty": null,
        "unit": null
      },
      "fault_description": "故障或问题描述，无则null",
      "work_scope": ["工作范围描述1", "工作范围描述2"],
      "item_special_requirements": ["该项特有的特殊要求"]
    }
  ],
  "split_reasoning": "解释为何这样拆分服务项",
  "global_context": {
    "urgency_level": "high|medium|low|unknown",
    "urgency_signals": ["原文中表明紧迫性的片段"],
    "time_constraints": "时间约束，无则null",
    "location": "地点，无则null",
    "special_requirements": ["通用特殊要求"],
    "additional_context": "其他补充信息，无则null"
  }
}
```

输出规则：
1. 保留原文语言片段作为证据，不要翻译
2. code 必须从提供的枚举列表中选取，不要编造不存在的编码
3. 如果无法匹配任何枚举项，将 code 设为 null，confidence 设为 "low"
4. confidence 判断标准：
   - high: 邮件明确提到了与枚举项高度吻合的描述
   - medium: 可以合理推断，但不完全确定
   - low: 勉强匹配或无法匹配
5. 设备数量和单位如果邮件中未提及，设为 null
```

---

## 九、校验与归一化逻辑

### 9.1 校验规则矩阵

| 校验项 | 规则 | 结果类型 | 说明 |
|--------|------|---------|------|
| service_desc_code 不为空 | 必须有值 | error | 无法识别服务描述则该服务项无效 |
| service_desc_code 在 R2 中存在 | R2 查表 | error | LLM 幻觉兜底 |
| service_type_code 在 R2 中存在 | R2 查表（允许 null） | warning | 有值但不在 R2 中 |
| equipment_model_code 在 R2 中存在 | R2 查表（允许 null） | warning | 有值但不在 R2 中 |
| 设备型号归属校验 | model 的 parent_desc_code 是否等于 service_desc_code | warning | 型号和服务描述不匹配 |
| business_type 推导 | 从 service_desc_code 对应记录取 business_type | auto | 不需用户填写 |
| confidence 为 low 的字段 | 统计 | warning | 提示业务人员确认 |
| 至少识别 1 个有效服务项 | service_items 非空 | error | 无法解析出任何服务项 |

### 9.2 归一化规则

```
1. 设备型号名称标准化：
   去除首尾空格
   如果 LLM 返回的 model_name 与 R2 中已有的 name 接近（编辑距离 ≤ 3），
   采用 R2 中的标准名称

2. business_type 自动推导：
   business_type = R2.service_descriptions
     .find(d => d.code === service_desc_code)
     .business_type
   用户无需手动指定

3. search_params.task_description 组合生成：
   = service_desc_name
     + " " + (service_type_name || "")
     + " " + (fault_description || "")
     + " " + work_scope.join(",")
   → 去除多余空格，截断至 500 字符
   → 用于 S1 的 pg_trgm 相似度排序

4. search_params.remark：
   = raw_text（完整原始邮件文本透传）
   → 用于 S1 Step 3 备注相似度补充
```

---

## 十、Skill 逻辑伪代码

```python
def parse_requirement(
    raw_text: str,
    enums: R2Enums,          # R2 枚举字典（全局共享，由 Agent 编排层传入）
    llm_caller: Callable,    # Agent 编排层提供的 LLM 调用函数
) -> ParsedRequirementResult:
    """
    S5 ParseRequirementSkill 主逻辑

    Args:
        raw_text: 原始邮件文本
        enums: R2 枚举字典对象
        llm_caller: 上层 Agent 提供的 LLM 调用能力
    """

    # ── Step 1：加载并索引 R2 枚举 ────────────────────────
    desc_index = {d["code"]: d for d in enums.service_descriptions}
    desc_name_index = {d["name"]: d for d in enums.service_descriptions}
    type_index = {t["code"]: t for t in enums.service_types}
    model_index = {m["code"]: m for m in enums.equipment_models}

    # ── Step 2：构建 Prompt 并调用 LLM ─────────────────────
    prompt = build_prompt(
        raw_text=raw_text,
        service_descriptions=enums.service_descriptions,
        service_types=enums.service_types,
        equipment_models=enums.equipment_models,
    )

    llm_response = llm_caller(prompt)
    parsed_llm = safe_parse_json(llm_response)
    # 如果 JSON 解析失败，进入降级处理（见第十二节）

    # ── Step 3：逐服务项校验与归一化 ──────────────────────
    service_items = []
    for idx, item in enumerate(parsed_llm["service_items"], start=1):
        errors = []
        warnings = []

        # 3.1 服务描述校验
        desc_code = item["service_desc_match"]["code"]
        if desc_code is None:
            errors.append(ValidationIssue(
                field="service_desc_code",
                type="missing",
                message=f"服务项 {idx}：无法识别服务描述"
            ))
            business_type = "unknown"
            desc_name = None
        elif desc_code not in desc_index:
            # LLM 幻觉兜底：尝试按名称模糊匹配
            fallback = fuzzy_match_desc(
                item["service_desc_match"]["name"],
                enums.service_descriptions
            )
            if fallback:
                desc_code = fallback["code"]
                desc_name = fallback["name"]
                business_type = fallback["business_type"]
                warnings.append(ValidationIssue(
                    field="service_desc_code",
                    type="ambiguous",
                    message=f"LLM 返回的编码不在 R2 中，已自动修正为 {desc_code}",
                    suggestion=desc_code
                ))
            else:
                errors.append(ValidationIssue(
                    field="service_desc_code",
                    type="invalid",
                    message=f"服务描述编码 {desc_code} 不在 R2 枚举中，且无法模糊匹配"
                ))
                business_type = "unknown"
                desc_name = None
        else:
            desc_name = desc_index[desc_code]["name"]
            business_type = desc_index[desc_code]["business_type"]

        # 3.2 服务类型校验（允许 null）
        type_match = item.get("service_type_match")
        type_code = None
        type_name = None
        if type_match and type_match.get("code"):
            if type_match["code"] in type_index:
                type_code = type_match["code"]
                type_name = type_index[type_code]["name"]
            else:
                warnings.append(ValidationIssue(
                    field="service_type_code",
                    type="invalid",
                    message=f"服务类型编码 {type_match['code']} 不在 R2 中"
                ))

        # 3.3 设备型号校验（允许 null）
        equip = item.get("equipment", {})
        model_code = equip.get("model_code")
        model_name = equip.get("model_name")
        if model_code and model_code not in model_index:
            # 尝试按名称模糊匹配
            fallback_model = fuzzy_match_model(
                model_name, enums.equipment_models
            )
            if fallback_model:
                model_code = fallback_model["code"]
                model_name = fallback_model["name"]
            else:
                model_code = None
                warnings.append(ValidationIssue(
                    field="equipment_model_code",
                    type="ambiguous",
                    message=f"设备型号 '{model_name}' 无法匹配 R2 已知型号"
                ))

        # 3.4 级联关系校验
        if model_code and desc_code:
            model_record = model_index.get(model_code, {})
            if model_record.get("parent_desc_code") != desc_code:
                warnings.append(ValidationIssue(
                    field="equipment_model_code",
                    type="ambiguous",
                    message=f"设备型号 {model_name} 不属于服务描述 {desc_name} 类别"
                ))

        # 3.5 low confidence 标记
        for field_key, match_obj in [
            ("service_desc", item.get("service_desc_match", {})),
            ("service_type", item.get("service_type_match", {})),
        ]:
            if match_obj and match_obj.get("confidence") == "low":
                warnings.append(ValidationIssue(
                    field=field_key,
                    type="low_confidence",
                    message=f"{field_key} 的匹配置信度较低，建议人工确认",
                    suggestion=match_obj.get("name")
                ))

        # 3.6 组装 search_params
        task_desc_parts = [desc_name or ""]
        if type_name:
            task_desc_parts.append(type_name)
        if item.get("fault_description"):
            task_desc_parts.append(item["fault_description"])
        if item.get("work_scope"):
            task_desc_parts.append(",".join(item["work_scope"]))
        task_description = " ".join(filter(None, task_desc_parts)).strip()[:500] or None

        search_params = {
            "business_type": business_type,
            "service_desc_code": desc_code,
            "service_type_code": type_code,
            "equipment_model_code": model_code,
            "task_description": task_description,
            "remark": raw_text,  # 完整原始邮件透传
        }

        # 3.7 构建 ParsedServiceItem
        service_items.append(ParsedServiceItem(
            item_index=idx,
            raw_description=item.get("raw_description", ""),
            business_type=business_type,
            service_desc={
                "code": desc_code,
                "name": desc_name,
                "confidence": item.get("service_desc_match", {}).get("confidence", "low"),
                "match_reason": item.get("service_desc_match", {}).get("match_reason", ""),
            },
            service_type={
                "code": type_code,
                "name": type_name,
                "confidence": (type_match or {}).get("confidence", "low"),
                "match_reason": (type_match or {}).get("match_reason", ""),
            } if type_code else None,
            equipment={
                "model_code": model_code,
                "model_name": model_name,
                "manufacturer": equip.get("manufacturer"),
                "qty": equip.get("qty"),
                "unit": equip.get("unit"),
                "confidence": "high" if model_code else "low",
            },
            item_notes={
                "fault_description": item.get("fault_description"),
                "work_scope": item.get("work_scope", []),
                "item_special_requirements": item.get("item_special_requirements", []),
            },
            search_params=search_params,
            validation={
                "is_valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
            },
        ))

    # ── Step 4：组装最终输出 ──────────────────────────────
    global_ctx = parsed_llm.get("global_context", {})

    return ParsedRequirementResult(
        skill="ParseRequirementSkill",
        version="1.0.0",
        raw_text=raw_text,
        detected_language=parsed_llm.get("detected_language", "unknown"),
        service_item_count=len(service_items),
        split_reasoning=parsed_llm.get("split_reasoning", ""),
        global_context={
            "urgency_level": global_ctx.get("urgency_level", "unknown"),
            "urgency_signals": global_ctx.get("urgency_signals", []),
            "time_constraints": global_ctx.get("time_constraints"),
            "location": global_ctx.get("location"),
            "special_requirements": global_ctx.get("special_requirements", []),
            "additional_context": global_ctx.get("additional_context"),
        },
        service_items=service_items,
        validation={
            "is_valid": any(item.validation["is_valid"] for item in service_items),
            "total_errors": sum(len(item.validation["errors"]) for item in service_items),
            "total_warnings": sum(len(item.validation["warnings"]) for item in service_items),
        },
    )
```

---

## 十一、返回结果结构示例

### 示例输入

```
Hi,

During our vessel's scheduled drydocking, we need the following services:
1. Main engine overhaul for 9K98ME-C, including piston inspection
2. Boiler safety valve replacement and testing
3. ICCP system maintenance

The vessel will be at shipyard from April 15-30. 
Please provide assessment asap.

Thanks
```

### 示例输出

```json
{
  "skill": "ParseRequirementSkill",
  "version": "1.0.0",
  "raw_text": "Hi,\n\nDuring our vessel's scheduled drydocking, we need the following services:\n1. Main engine overhaul for 9K98ME-C, including piston inspection\n2. Boiler safety valve replacement and testing\n3. ICCP system maintenance\n\nThe vessel will be at shipyard from April 15-30.\nPlease provide assessment asap.\n\nThanks",
  "detected_language": "en",
  "service_item_count": 3,
  "split_reasoning": "邮件中明确列出了3项独立的服务需求，分别涉及不同设备大类：主机（二冲程柴油机）、锅炉、ICCP系统，因此拆分为3个服务项。",

  "global_context": {
    "urgency_level": "medium",
    "urgency_signals": ["asap"],
    "time_constraints": "April 15-30",
    "location": "shipyard（未指明具体船厂）",
    "special_requirements": [],
    "additional_context": "scheduled drydocking（计划坞修，非紧急抢修）"
  },

  "service_items": [
    {
      "item_index": 1,
      "raw_description": "Main engine overhaul for 9K98ME-C, including piston inspection",
      "business_type": "轮机",
      "service_desc": {
        "code": "RS0000000001",
        "name": "二冲程柴油机",
        "confidence": "high",
        "match_reason": "Main engine + 9K98ME-C 属于二冲程柴油机系列"
      },
      "service_type": {
        "code": "CS0007",
        "name": "坞修保养",
        "confidence": "medium",
        "match_reason": "overhaul 在坞修背景下对应坞修保养，但也可能指大修(维修)"
      },
      "equipment": {
        "model_code": "ET000000000002",
        "model_name": "9K98ME-C",
        "manufacturer": null,
        "qty": null,
        "unit": null,
        "confidence": "high"
      },
      "item_notes": {
        "fault_description": null,
        "work_scope": ["overhaul", "piston inspection"],
        "item_special_requirements": []
      },
      "search_params": {
        "business_type": "轮机",
        "service_desc_code": "RS0000000001",
        "service_type_code": "CS0007",
        "equipment_model_code": "ET000000000002",
        "task_description": "二冲程柴油机 坞修保养 overhaul,piston inspection",
        "remark": "Hi,\n\nDuring our vessel's scheduled drydocking..."
      },
      "validation": {
        "is_valid": true,
        "errors": [],
        "warnings": [
          {
            "field": "service_type",
            "type": "low_confidence",
            "message": "service_type 的匹配置信度为 medium，建议人工确认",
            "suggestion": "坞修保养"
          }
        ]
      }
    },
    {
      "item_index": 2,
      "raw_description": "Boiler safety valve replacement and testing",
      "business_type": "轮机",
      "service_desc": {
        "code": "RS0000000003",
        "name": "锅炉",
        "confidence": "high",
        "match_reason": "Boiler 直接匹配锅炉"
      },
      "service_type": {
        "code": "CS0002",
        "name": "更换",
        "confidence": "high",
        "match_reason": "replacement 明确指向更换"
      },
      "equipment": {
        "model_code": null,
        "model_name": null,
        "manufacturer": null,
        "qty": null,
        "unit": null,
        "confidence": "low"
      },
      "item_notes": {
        "fault_description": null,
        "work_scope": ["safety valve replacement", "testing"],
        "item_special_requirements": []
      },
      "search_params": {
        "business_type": "轮机",
        "service_desc_code": "RS0000000003",
        "service_type_code": "CS0002",
        "equipment_model_code": null,
        "task_description": "锅炉 更换 safety valve replacement,testing",
        "remark": "Hi,\n\nDuring our vessel's scheduled drydocking..."
      },
      "validation": {
        "is_valid": true,
        "errors": [],
        "warnings": []
      }
    },
    {
      "item_index": 3,
      "raw_description": "ICCP system maintenance",
      "business_type": "电气",
      "service_desc": {
        "code": "RS0000000006",
        "name": "ICCP系统",
        "confidence": "high",
        "match_reason": "ICCP system 直接匹配 ICCP系统"
      },
      "service_type": {
        "code": "CS0001",
        "name": "维修",
        "confidence": "medium",
        "match_reason": "maintenance 可能指维修或保养，暂匹配维修"
      },
      "equipment": {
        "model_code": null,
        "model_name": null,
        "manufacturer": null,
        "qty": null,
        "unit": null,
        "confidence": "low"
      },
      "item_notes": {
        "fault_description": null,
        "work_scope": ["maintenance"],
        "item_special_requirements": []
      },
      "search_params": {
        "business_type": "电气",
        "service_desc_code": "RS0000000006",
        "service_type_code": "CS0001",
        "equipment_model_code": null,
        "task_description": "ICCP系统 维修 maintenance",
        "remark": "Hi,\n\nDuring our vessel's scheduled drydocking..."
      },
      "validation": {
        "is_valid": true,
        "errors": [],
        "warnings": [
          {
            "field": "service_type",
            "type": "low_confidence",
            "message": "service_type 的匹配置信度为 medium，建议人工确认",
            "suggestion": "维修"
          }
        ]
      }
    }
  ],

  "validation": {
    "is_valid": true,
    "total_errors": 0,
    "total_warnings": 2
  }
}
```

---

## 十二、异常处理与降级策略

| 场景 | 处理方式 | 是否阻断流程 |
|------|---------|------------|
| `raw_text` 为空或纯空白 | 返回 error："输入文本为空" | ✅ 阻断 |
| LLM 调用超时/失败 | 降级为纯规则匹配：按关键词扫描 R2 枚举，尽力匹配。warnings 追加"LLM 降级" | ❌ 不阻断，但结果可能不完整 |
| LLM 返回非 JSON / 格式异常 | 重试 1 次（可配置）。仍失败则同上降级 | ❌ 不阻断 |
| LLM 返回的编码不在 R2 中 | 按名称模糊匹配兜底。仍无匹配则标记 low_confidence | ❌ 不阻断 |
| 无法识别任何服务项 | 返回 error："无法从文本中识别服务需求"，建议人工介入 | ✅ 阻断 |
| 所有服务项的 service_desc 校验失败 | `is_valid = false`，编排层应中止并提示人工填写 | ✅ 阻断 |
| 部分服务项校验失败 | 有效服务项继续流转，失败的标记 `is_valid = false` 并提示 | ❌ 部分阻断 |
| R2 枚举文件缺失/加载失败 | Skill 启动即失败，返回系统错误 | ✅ 阻断 |

### 降级模式下的关键词匹配规则

当 LLM 不可用时，使用以下关键词规则做基础匹配：

```python
# 服务描述关键词映射（降级用）
DESC_KEYWORDS = {
    "RS0000000001": ["main engine", "主机", "diesel", "柴油机", "ME-C", "ME-B", "MC-C", "S50", "K98"],
    "RS0000000003": ["boiler", "锅炉"],
    "RS0000000004": ["generator", "发电机"],
    "RS0000000006": ["ICCP", "接地"],
    "RS0000000008": ["valve", "阀门"],
    "RS0000000009": ["pipe", "piping", "管路"],
    # ...
}

# 服务类型关键词映射（降级用）
TYPE_KEYWORDS = {
    "CS0001": ["repair", "维修", "修理"],
    "CS0002": ["replace", "replacement", "更换", "换新"],
    "CS0003": ["inspection", "检测", "检查", "test"],
    "CS0006": ["health check", "健康检查"],
    "CS0007": ["drydocking", "overhaul", "坞修", "保养"],
    "CS0008": ["voyage repair", "航修"],
    # ...
}
```

---

## 十三、OpenClaw Skill 目录结构

```
parse-requirement-skill/
├── SKILL.md                          # 【必需】技能定义文件
├── _meta.json                        # 元数据
├── .env.example                      # 环境变量示例（降级模式用）
├── .gitignore
├── README.md
├── requirements.txt                  # Python 依赖（极简）
├── scripts/
│   ├── main.py                       # 主脚本入口
│   ├── enum_loader.py                # R2 枚举加载与索引构建
│   ├── prompt_builder.py             # Prompt 构建器
│   ├── llm_response_parser.py        # LLM 响应解析与兜底
│   ├── validator.py                  # 校验与归一化逻辑
│   ├── output_builder.py             # 输出组装
│   └── fallback_matcher.py           # 降级关键词匹配（LLM 不可用时）
├── input.example.json                # 输入示例（英文单项）
├── input.multi.json                  # 输入示例（英文多服务项）
├── input.chinese.json                # 输入示例（中文）
└── tests/
    ├── test_enum_loader.py
    ├── test_prompt_builder.py
    ├── test_validator.py
    ├── test_fallback_matcher.py
    └── fixtures/
        ├── single_item_en.json
        ├── multi_item_en.json
        ├── multi_item_zh.json
        └── edge_case_empty.json
```

> **注意**：此 Skill 目录中**不包含** R2 枚举文件。R2 枚举文件位于全局 `references/R2-enums/` 目录，通过 `--enums-dir` 参数传入。

---

## 十四、SKILL.md 设计

```yaml
---
name: ParseRequirementSkill
slug: parse-requirement-skill
version: 1.0.0
homepage: https://github.com/09okjk/PingGu
description: 解析客户邮件中的自然语言服务需求，自动拆分多服务项并映射至枚举编码，输出标准化结果供后续Skill消费
changelog: |
  - 1.0.0: 首版实现，支持多服务项拆分、R2枚举匹配、多语言NLU、LLM降级关键词匹配
metadata:
  clawdbot:
    emoji: 📋
    requires:
      bins: ["python3"]
      env: []
    os: ["linux", "darwin", "win32"]
---

# ParseRequirementSkill

用于智能评估 Agent 的 S5 需求解析技能。
接收客户原始邮件文本，自动识别并拆分服务项，映射至 R2 枚举编码，输出标准化解析结果。

## When to Use（何时使用）

✅ 适用场景：
- Agent 收到新的评估需求时（第一步必调）
- 用户提交了客户邮件或自然语言的服务需求描述时
- 需要将自然语言需求转换为结构化字段时

## When NOT to Use（何时不用）

❌ 不适用场景：
- 输入已经是结构化的编码字段（直接传给 S1 即可）
- 仅做历史案例检索（请使用 S1 SearchHistoryCasesSkill）
- 仅做风险匹配（请使用 S2 MatchRisksSkill）

## Setup（安装配置）

1. 确保 Python 3.10+ 可用
2. 安装依赖
3. 确认 R2 枚举目录可访问
4. 执行解析命令

```bash
cd {baseDir}
pip install -r requirements.txt
python scripts/main.py --input ./input.example.json --enums-dir ../references/R2-enums --pretty
```

## Options（选项说明）

- `--input <path>`: 输入 JSON 文件路径（必填）
- `--enums-dir <path>`: R2 枚举字典目录路径（默认 `../references/R2-enums`）
- `--pretty`: 以格式化 JSON 输出（可选）
- `--fallback-only`: 强制使用降级关键词匹配模式，不调用 LLM（调试用）

## Core Rules（核心规则）

1. **S5 是 Agent 流程的入口 Skill**，必须最先执行。
2. 输入为自然语言邮件文本，**不是结构化表单**。
3. 自动识别邮件中的多个服务需求，按 R2 服务描述枚举进行拆分。
4. 拆分规则：
   - 不同设备大类 → 不同服务项
   - 同一设备大类的不同独立工作 → 酌情拆分
   - 同一工作的子任务 → 不拆分
5. 枚举匹配使用 LLM 语义理解 + R2 规则校验双保险。
6. LLM 使用 Agent 当前配置的模型，不单独配置。
7. LLM 不可用时降级为关键词匹配，不阻断流程。
8. 每个服务项输出包含 `search_params`，与 S1 输入格式完全对齐。
9. 所有匹配结果附带 `confidence` 置信度和 `match_reason` 依据说明。

## Security & Privacy（安全说明）

- 原始邮件文本仅用于内部评估流程，不外发至非授权服务。
- LLM 调用由 Agent 编排层统一管控，S5 不自行管理 API Key。
- 不在日志中打印完整客户邮件内容。
- 输出中的 `remark` 字段透传原文，下游 Skill 需同样注意隐私保护。

## Related Skills（相关技能）

- S1: SearchHistoryCasesSkill（消费 S5 的 `search_params` 输出）
- S2: MatchRisksSkill（消费 S5 的服务描述、设备、备注信息）
- S4: EstimateManpowerSkill（消费 S5 的任务维度信息）
- S6: GenerateReportSkill（消费 S5 的完整解析结果）
- R2: 枚举字典与业务规则库（S5 的核心依赖）

## Feedback（反馈）

- 若拆分不准确，优先检查 R2 枚举覆盖度，补充缺失的服务描述枚举项。
- 若枚举匹配不准确，优先调整 prompt 中的枚举描述或增加示例。
- 可在第二版中增加：附件解析（PDF/图片 OCR）、上下文多轮对话确认、拆分结果人工编辑回流。

---

## 十五、与后续 Skill 的接口衔接

### 15.1 S5 → S1 接口衔接

S5 每个 `ParsedServiceItem` 的 `search_params` 字段与 S1 的 `input.json` 格式**完全对齐**：

| S5 输出字段 (`search_params`) | S1 输入字段 | 说明 |
|------------------------------|-----------|------|
| `business_type` | `business_type` | 必填，从服务描述自动推导 |
| `service_desc_code` | `service_desc_code` | 必填 |
| `service_type_code` | `service_type_code` | 允许 null，S1 已兼容 |
| `equipment_model_code` | `equipment_model_code` | 允许 null，S1 已兼容 |
| `task_description` | `task_description` | S5 组合生成，S1 用于 pg_trgm 排序 |
| `remark` | `remark` | 原始邮件全文透传，S1 Step 3 备注相似度 |

### 15.2 编排层调用链路

```
场景：邮件包含 3 个服务项

原始邮件
    │
    ▼
┌────────────────────────────────────────────┐
│  S5 ParseRequirementSkill                  │
│  输出：ParsedRequirementResult             │
│  └── service_items: [Item1, Item2, Item3]  │
└────────────────────────────────────────────┘
    │
    ▼  编排层对每个 service_item 独立编排后续流程
    │
    ├── Item1.search_params → S1 → S2 → S4 → S6 → 评估报告草稿 1
    ├── Item2.search_params → S1 → S2 → S4 → S6 → 评估报告草稿 2
    └── Item3.search_params → S1 → S2 → S4 → S6 → 评估报告草稿 3
    │
    ▼
最终输出：3 份独立的评估报告草稿
```

### 15.3 S5 → S2 接口衔接

S2 MatchRisksSkill 需要的输入：

| S2 需要 | S5 提供的来源 |
|--------|------------|
| 服务类型 | `service_item.service_type.code` |
| 设备类型 | `service_item.service_desc.code` + `service_item.equipment` |
| 备注文本 | `service_item.raw_description` + `global_context.special_requirements` |

### 15.4 S5 → S4 接口衔接

S4 EstimateManpowerSkill 需要的输入：

| S4 需要 | S5 提供的来源 |
|--------|------------|
| 任务维度信息 | `service_item.item_notes.work_scope` |
| 设备数量 | `service_item.equipment.qty` |
| 业务归口 | `service_item.business_type` |

### 15.5 S5 → S6 接口衔接

S6 GenerateReportSkill 作为最终合成 Skill，需要 S5 的完整输出：
- `global_context`（紧迫性、地点、时间约束等全局信息）
- 每个 `service_item` 的所有解析结果
- `validation` 信息（用于报告中的置信度标注）

---

## 十六、扩展性预留

### 16.1 附件解析（第二期+）

当前 S5 仅处理纯文本输入。后续邮件可能包含附件（PDF 工单、图片、技术图纸等）。

**预留设计**：

```typescript
// 输入扩展
interface RawRequirementV2 {
  raw_text: string;
  attachments?: Attachment[];    // 第二期新增
}

interface Attachment {
  filename: string;
  mime_type: string;             // "application/pdf" | "image/png" | ...
  content_url?: string;          // 文件 URL
  extracted_text?: string;       // 预提取的文本（OCR 或 PDF 解析后）
}
```

**扩展策略**：
- S5 的 LLM prompt 扩展为接收 `attachments[].extracted_text`
- 附件的 OCR / PDF 解析由编排层或专用预处理模块完成，S5 只消费文本结果
- `main.py` 的 `--input` JSON 格式向后兼容，新增的 `attachments` 字段可选

### 16.2 人工编辑回流（第二期）

业务人员审核 S5 的拆分结果后，可能做以下修改：
- 合并两个不应拆分的服务项
- 拆分一个应被拆分的服务项
- 修改错误的枚举匹配

**预留设计**：
- S5 输出包含 `item_index` 和 `raw_description`，便于业务人员定位修改
- 差异记录结构预留（与数据飞轮对接）：

```json
{
  "original_item_count": 3,
  "final_item_count": 2,
  "changes": [
    {"type": "merge", "merged_items": [2, 3], "reason": "锅炉阀门更换和检测属于同一服务项"},
    {"type": "field_correction", "item": 1, "field": "service_type_code", "from": "CS0007", "to": "CS0001"}
  ]
}
```

### 16.3 多轮对话确认（第三期）

当 S5 遇到无法确定的拆分或匹配时，可以通过编排层向用户发起确认：

```
S5: 检测到邮件中包含"main engine overhaul"，
    可匹配"坞修保养"(CS0007) 或"维修"(CS0001)。
    请确认应使用哪个服务类型？

用户: 坞修保养

S5: 已确认，继续处理。
```

当前 MVP 阶段不实现此功能，S5 直接选择最高���信度的匹配并标记 warning。

---

## 十七、待确认事项

### ✅ 已确认

| 编号 | 问题 | 确认结论 |
|------|------|---------|
| 1 | R2 枚举字典是否每个 Skill 都复制一份 | 否。R2 全局共享，各 Skill 通过路径引用 |
| 2 | LLM 是否需要为 S5 单独配置 | 否。使用 Agent 当前配置的模型 |
| 3 | 是否需要处理附件 | 当前不需要，预留扩展性（第二期） |
| 4 | 备注/邮件长度 | 最多几百个单词，token 消耗可控 |
| 5 | 是否需要支持批量需求单 | 不需要，一次处理一封邮件 |
| 6 | 输入是否为标准表单 | 否。输入为自然语言邮件文本 |
| 7 | 邮件是否可能包含多个服务项 | 是。需自动拆分，每个服务项对应一个需求单 |
| 8 | R2 枚举数据 | 先使用默认占位数据，后续拿到真实枚举内容自行替换 |

### 🔴 高优先级（影响实现）

| 编号 | 问题 | 说明 |
|------|------|------|
| 1 | R2 真实枚举数据 | 当前使用占位数据，需替换为业务方提供的完整枚举。直接影响匹配准确性 |
| 2 | Agent 编排层如何传递 LLM 调用能力给 S5 | 方式 A（prompt 透传）还是方式 B（S5 内部调用）？影响 `main.py` 的实现方式 |

### 🟡 中优先级（影响体验）

| 编号 | 问题 | 说明 |
|------|------|------|
| 3 | 拆分错误的容忍度 | 如果 S5 将"主机保养含活塞检查"拆成了 2 项，最坏后果是什么？（决定拆分策略的保守/激进程度） |
| 4 | 业务人员是否需要在 S5 输出后确认拆分结果再继续 | 是强制确认还是自动流转？影响编排层设计 |

### 🟢 低优先级（影响未来扩展）

| 编号 | 问题 | 说明 |
|------|------|------|
| 5 | 附件类型范围 | 第二期附件解析需要支持哪些格式？PDF / 图片 / Word？ |
| 6 | 是否需要记录 S5 拆分的人工修正数据用于飞轮 | 影响回流数据结构设计 |

---

## 附录 A：requirements.txt

```
# parse-requirement-skill 依赖（极简）
# LLM 调用由 Agent 编排层处理，S5 本身不需要 LLM SDK

# 仅在降级模式/独立测试时需要直接调用 LLM，以下可选：
# openai>=1.0.0
# httpx>=0.25.0

# 无额外依赖，仅使用 Python 标准库：
# json, argparse, pathlib, re, difflib(模糊匹配)
```

### 说明

S5 的 Python 依赖**极简**，核心逻辑仅使用标准库：
- `json`：JSON 解析
- `argparse`：命令行参数
- `pathlib`：路径处理
- `re`：正则表达式（降级关键词匹配）
- `difflib`：模糊字符串匹配（枚举名称兜底匹配）

LLM 调用由 Agent 编排层统一处理，S5 不直接依赖 `openai` 等 SDK。

---

## 附录 B：_meta.json

```json
{
  "name": "parse-requirement-skill",
  "version": "1.0.0",
  "description": "S5 ParseRequirementSkill - 自然语言需求解析与多服务项拆分",
  "author": "09okjk",
  "license": "MIT",
  "homepage": "https://github.com/09okjk/PingGu",
  "tags": ["nlu", "parsing", "requirement", "multi-item-split", "enum-matching"]
}
```

---

## 附录 C：输入示例文件

### input.example.json（英文单项）

```json
{
  "raw_text": "Dear team,\n\nWe need health check service for our main engine 5S50ME-B during the upcoming drydocking in Singapore. Please advise on scheduling.\n\nBest regards"
}
```

### input.multi.json（英文多服务项）

```json
{
  "raw_text": "Hi,\n\nDuring our vessel's scheduled drydocking, we need the following services:\n1. Main engine overhaul for 9K98ME-C, including piston inspection\n2. Boiler safety valve replacement and testing\n3. ICCP system maintenance\n\nThe vessel will be at shipyard from April 15-30.\nPlease provide assessment asap.\n\nThanks"
}
```

### input.chinese.json（中文多服务项）

```json
{
  "raw_text": "您好，\n\n我司船舶将于下月进坞，需要以下服务：\n- 主机（MAN B&W 6S50MC-C）坞修保养\n- 发电机组检修（2台）\n- 锅炉安全阀更换\n\n请尽快安排技术评估。"
}
```

---

*文档持续更新中，最后修改：2026-03-23*
