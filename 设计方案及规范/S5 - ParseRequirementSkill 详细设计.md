# S5 - ParseRequirementSkill 详细设计

> 创建日期：2026-03-23  
> 最后修改：2026-03-23  
> 状态：设计确认  
> 所属模块：智能评估 Agent — Skills 层

---

## 目录

1. [Skill 定位与职责](#一skill-定位与职责)
2. [输入现实与设计前提](#二输入现实与设计前提)
3. [为什么 S5 必须最先执行](#三为什么-s5-必须最先执行)
4. [核心设计目标](#四核心设计目标)
5. [与 R2 Reference 的关系](#五与-r2-reference-的关系)
6. [多服务项拆分设计](#六多服务项拆分设计)
7. [字段提取与标准化映射](#七字段提取与标准化映射)
8. [Skill 输出结构设计](#八skill-输出结构设计)
9. [执行流程设计](#九执行流程设计)
10. [Prompt / 推理规则设计](#十prompt--推理规则设计)
11. [脚本实现建议](#十一脚本实现建议)
12. [SKILL.md 创建建议](#十二skillmd-创建建议)
13. [与后续 Skills 的衔接方式](#十三与后续-skills-的衔接方式)
14. [异常场景与降级策略](#十四异常场景与降级策略)
15. [未来扩展设计](#十五未来扩展设计)
16. [待确认事项](#十六待确认事项)

---

## 一、Skill 定位与职责

| 项目 | 内容 |
|------|------|
| **Skill 名称** | ParseRequirementSkill |
| **核心职责** | 将用户原始自然语言邮件解析为 1~N 个结构化服务需求项（RequirementItem），供后续 S1/S2/S4/S6 使用 |
| **输入形式** | 非结构化自然语言邮件，可能包含多个服务项 |
| **输出形式** | 标准化 RequirementItem 列表 + 解析依据 + 置信度 + 待确认项 |
| **调用方** | 上层 Agent 主流程 / `assess()` 主接口 |
| **实施阶段** | MVP 必须 |

### 重新定义后的职责边界

S5 不再只是“从标准表单里抽字段”，而是承担以下四项职责：

1. **需求拆分**：识别一封邮件中包含几个独立服务项  
2. **字段提取**：从每个服务项中提取结构化字段  
3. **标准映射**：将自然语言表达映射到 R2 枚举编码  
4. **歧义标注**：对不确定字段给出候选值和置信度，便于人工确认

---

## 二、输入现实与设计前提

### 2.1 当前输入不是标准需求单，而是自然语言邮件

当前用户输入通常具备以下特征：

- 主要是自然语言正文，不是字段化表单
- 可能夹杂专业术语、设备型号、故障现象、服务诉求
- 可能同时提到多个设备或多个问题
- 文本长度通常不长，基本为几百个单词以内
- 现阶段不考虑附件，但后续要保留扩展性

### 2.2 输入样例特征

可能类似：

```text
Dear team,

We have an issue with our main engine and boiler.
The main engine shows abnormal vibration and may need inspection.
The boiler has leakage and we want to know whether repair or replacement is needed.
Please advise the service scope and estimated manpower.

Best regards
```

该输入中至少包含两个潜在服务项：

- 主机相关问题
- 锅炉相关问题

因此不能直接当作“一个需求单”处理，必须先拆分。

---

## 三、为什么 S5 必须最先执行

### 结论

**S5 必须作为主流程中的第一个 Skill 执行。**

### 原因

后续多个 Skill 都依赖结构化字段：

- **S1 SearchHistoryCasesSkill** 依赖：
  - `business_type`
  - `service_desc_code`
  - `service_type_code`
  - `equipment_model_code`
  - `task_description`（可选）
- **S2 MatchRisksSkill** 依赖：
  - 服务类型
  - 设备类型
  - 备注/补充说明
- **S4 EstimateManpowerSkill** 依赖：
  - 任务拆解结果
- **S6 GenerateReportSkill** 依赖：
  - 所有前置结构化结果

而原始邮件并不直接提供这些规范字段，因此必须先由 S5 完成“非结构化 → 结构化”的转换。

### 推荐主流程

```text
原始邮件输入
    ↓
S5 ParseRequirementSkill
    ↓
输出：RequirementItem[]
    ↓
对每个 RequirementItem 并行执行：
  - S1 SearchHistoryCasesSkill
  - S2 MatchRisksSkill
  - 其他后续 Skills
    ↓
S6 GenerateReportSkill 汇总生成
```

---

## 四、核心设计目标

### 4.1 MVP 阶段目标

S5 在 MVP 阶段应优先实现以下能力：

1. 从自然语言邮件中识别服务意图
2. 将一封邮件拆分为 1~N 个服务项
3. 为每个服务项提取核心检索字段
4. 将字段映射到 R2 枚举体系
5. 对不确定字段给出候选项和置信度
6. 输出统一 JSON 结构，作为后续 Skill 的标准输入

### 4.2 非目标

MVP 阶段暂不做：

- 附件内容解析
- 图片/PDF/OCR 提取
- 超长上下文文档理解
- 完全自动零歧义决策
- 脱离人工确认的强自动化提交

---

## 五、与 R2 Reference 的关系

## 5.1 结论

**R2 是全局共享的权威 Reference，但不是每个 Skill 都必须完整携带全部 R2 内容。**

### 5.2 对 S5 而言，实际需要的 R2 子集

S5 主要使用以下枚举与规则：

| R2 子集 | 用途 |
|--------|------|
| 服务描述枚举 | 识别每个服务项属于哪类服务对象/场景 |
| 服务类型枚举 | 识别维修、更换、检测、安装等动作类型 |
| 业务归口枚举 | 推断归属部门 |
| 设备名称枚举 | 标准化设备对象 |
| 设备名称 → 型号映射 | 校验型号归属关系 |
| 服务设备单位枚举 | 标准化数量单位 |
| 同义词/别名词典 | 将邮件自然语言映射到标准枚举 |
| 规则库 | 多服务项拆分、优先级判断、冲突消解 |

### 5.3 设计原则

- R2 作为**统一维护的数据源**
- S5 运行时仅读取自己需要的部分
- 不在每个 Skill 内重复维护一套枚举
- 避免多处拷贝导致版本不一致

### 5.4 MVP 阶段的枚举策略

由于当前尚未拿到完整枚举，可先提供少量占位枚举用于开发验证，后续可由你自行替换。

---

## 六、多服务项拆分设计

### 6.1 为什么必须支持拆分

业务上，一封邮件可能同时描述多个设备、多个问题、多个服务诉求。  
而你们实际处理时，会将其拆成多个需求单，每个服务项对应一个独立需求单。

因此 S5 的输出不能是单对象，必须是数组：

```json
{
  "requirements": [
    { "requirement_id": "REQ-001", "...": "..." },
    { "requirement_id": "REQ-002", "...": "..." }
  ]
}
```

### 6.2 拆分原则

当邮件中出现以下情况时，应考虑拆分为多个服务项：

#### 规则 A：不同服务对象
例如同时出现：

- 主机
- 锅炉
- 阀
- 燃油系统

则通常拆分为多个服务项。

#### 规则 B：同一对象但不同服务意图显著分离
例如：

- 对主机做健康检查
- 对主机某部件做更换

若两者可独立形成评估单，可拆分。

#### 规则 C：同一对象下多个并列问题
例如：

- boiler leakage
- boiler ignition failure

若业务上通常合并处理，则可保留为一个服务项下的多个问题描述，不必强拆。

### 6.3 拆分输出要求

每个拆分后的服务项都应包含：

- 独立摘要
- 原文数据片段
- 字段提取结果
- 置信度
- 是否建议人工确认

### 6.4 拆分示例

输入邮件：

```text
The main engine needs inspection due to abnormal vibration.
Also, the boiler has leakage and may require repair.
```

输出：

- RequirementItem 1：
  - 设备：主机
  - 服务类型：检测 / 检查
- RequirementItem 2：
  - 设备：锅炉
  - 服务类型：维修

---

## 七、字段提取与标准化映射

### 7.1 S5 输出的目标字段

每个 RequirementItem 建议至少包含以下字段：

| 字段名 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `requirement_id` | string | 是 | 当前邮件内的服务项编号 |
| `summary` | string | 是 | 服务项摘要 |
| `business_type` | object/null | 否 | 业务归口编码与名称 |
| `service_desc` | object/null | 是 | 服务描述编码与名称 |
| `service_type` | object/null | 否 | 服务类型编码与名称 |
| `equipment_name` | object/null | 否 | 所属设备名称编码与名称 |
| `equipment_model` | object/null | 否 | 所属设备型号编码与名称 |
| `equipment_manufacturer` | string/null | 否 | 厂家 |
| `equipment_quantity` | number/null | 否 | 数量 |
| `equipment_unit` | object/null | 否 | 单位编码与名称 |
| `service_device_models` | array | 否 | 服务设备型号文本列表 |
| `remark` | string/null | 是 | 当前服务项相关补充描述 |
| `original_evidence` | array | 是 | 原文证据片段 |
| `confidence` | string | 是 | high / medium / low |
| `ambiguities` | array | 否 | 歧义项列表 |
| `needs_user_confirmation` | boolean | 是 | 是否建议人工确认 |

### 7.2 字段提取原则

#### 服务描述 `service_desc`
这是最核心字段之一。  
它决定后续是否能命中 S1 的主检索维度。

如果邮件中提到：

- main engine
- two-stroke diesel engine
- boiler
- fuel pipe
- valve

则应优先映射到标准服务描述枚举。

#### 服务类型 `service_type`
从动作词中提取：

- inspect / inspection → 检测 / 检查
- repair / fix → 维修
- replace / renewal → 更换
- install → 安装
- overhaul → 检修 / 保养（需结合业务映射）

#### 业务归口 `business_type`
可通过服务描述或设备类型推断，例如：

- 主机/锅炉/轮机设备 → 轮机
- 电气系统/控制系统 → 电气

若无法可靠判断，可输出 null，并标记待确认。

#### 设备型号 `equipment_model`
优先从文本中抽取显式型号，如：

- 5S50ME-B
- 9K98ME-C
- MAN B&W-9S90ME-C9.2-TII

若抽到的是自由文本但未命中标准枚举，可保留：
- 原始型号文本
- 未标准化标记

#### 数量与单位
从文本中提取如：
- 2 units
- 1 set
- 3 pcs

若未明确，则留空。

### 7.3 同义词/别名映射的重要性

由于邮件不是标准表单，必须允许自然语言 → 标准枚举映射。

例如：

| 自然语言 | 标准枚举 |
|---------|---------|
| main engine | 主机 |
| M/E | 主机 |
| boiler unit | 锅炉 |
| inspection | 检查 |
| troubleshooting | 检测/维修（需上下文判断） |
| overhaul | 坞修保养 / 检修（需结合设备与业务规则） |

因此 S5 必须依赖一份 **alias / synonym mapping**。

---

## 八、Skill 输出结构设计

### 8.1 顶层输出结构

```json
{
  "input_type": "email_text",
  "language": "en",
  "requirement_count": 2,
  "requirements": [...],
  "global_ambiguities": [],
  "parsing_notes": [],
  "success": true
}
```

### 8.2 RequirementItem 结构

```json
{
  "requirement_id": "REQ-001",
  "summary": "主机异常振动，需检查评估",
  "business_type": {
    "code": "BT001",
    "name": "轮机",
    "confidence": "medium"
  },
  "service_desc": {
    "code": "SD001",
    "name": "主机",
    "confidence": "high"
  },
  "service_type": {
    "code": "ST001",
    "name": "检测",
    "confidence": "medium"
  },
  "equipment_name": {
    "code": "EQ001",
    "name": "主机",
    "confidence": "high"
  },
  "equipment_model": {
    "code": null,
    "name": "5S50ME-B",
    "confidence": "medium"
  },
  "equipment_manufacturer": "MAN B&W",
  "equipment_quantity": 1,
  "equipment_unit": {
    "code": "UM0005",
    "name": "台",
    "confidence": "medium"
  },
  "service_device_models": ["5S50ME-B"],
  "remark": "abnormal vibration",
  "original_evidence": [
    "The main engine shows abnormal vibration and may need inspection."
  ],
  "ambiguities": [
    {
      "field": "service_type",
      "reason": "邮件表达 may need inspection，可能也隐含维修诉求",
      "candidates": [
        { "code": "ST001", "name": "检测" },
        { "code": "ST002", "name": "维修" }
      ]
    }
  ],
  "confidence": "medium",
  "needs_user_confirmation": true
}
```

### 8.3 设计原则

- **允许字段为 null**
- **允许候选项共存**
- **必须保留原文证据**
- **必须输出置信度**
- **必须支持 1~N 服务项**

---

## 九、执行流程设计

```text
输入：原始邮件文本
  ↓
Step 1：基础预处理
  - 文本清洗
  - 段落切分
  - 语言识别
  - 去除签名等弱语义尾部内容
  ↓
Step 2：服务项识别与拆分
  - 识别设备对象
  - 识别并列问题/并列诉求
  - 生成 1~N 个候选服务项
  ↓
Step 3：字段提取
  - 服务描述
  - 服务类型
  - 业务归口
  - 设备名称/型号/厂家
  - 数量/单位
  - remark 摘要
  ↓
Step 4：R2 标准映射
  - 枚举命中
  - 同义词映射
  - 候选项排序
  ↓
Step 5：歧义分析
  - 字段缺失
  - 多候选冲突
  - 置信度评估
  ↓
Step 6：输出结构化 RequirementItem[]
```

---

## 十、Prompt / 推理规则设计

### 10.1 LLM 使用原则

**本 Skill 不单独配置模型，应复用当前 Agent 已配置的 LLM。**

原因：

- Skill 是整体 Agent 能力的一部分
- 模型配置应由上层统一管理
- 避免不同 Skill 各自配置模型导致维护复杂
- 便于统一升级、统一成本控制、统一效果评估

### 10.2 LLM 在 S5 中的角色

LLM 主要负责：

1. 多服务项识别与拆分
2. 语义理解与字段抽取
3. 歧义分析
4. 候选映射解释

### 10.3 规则优先于模型自由发挥

S5 不应完全依赖自由生成，建议采用：

- **规则约束 + LLM 提取**
- **枚举候选约束 + LLM 选择**
- **输出 JSON schema 强约束**

### 10.4 推荐提示词策略

将 Prompt 分三层：

#### 第一层：角色定义
告诉模型它是“服务需求解析器”，职责是把邮件拆成多个标准服务项。

#### 第二层：字段规则
明确每个字段含义、允许为空、必须保留证据、不允许臆造。

#### 第三层：输出约束
强制输出 JSON，不输出解释性散文。

### 10.5 关键规则

- 不得虚构邮件中不存在的信息
- 若字段无法确定，输出 null
- 若存在多个候选，输出歧义列表
- 若同一邮件包含多个独立设备/服务对象，应拆分
- 同一服务项必须附带原文证据片段

---

## 十一、脚本实现建议

### 11.1 推荐实现语言

**推荐 Python 优先。**

原因：

- 更适合文本处理与规则解析
- 便于后续增加 NLP 预处理
- 便于未来接入附件解析/OCR/分词等能力

### 11.2 但与现有 S1 的 `.mjs` 不冲突

S1 用 `.mjs`，S5 用 Python，不会造成 Skill 间逻辑冲突。  
关键在于统一接口协议，而不是统一语言。

### 11.3 建议统一的 Skill I/O 协议

输入：

```json
{
  "email_text": "...",
  "attachments": [],
  "r2_refs": {
    "service_desc_enum": [],
    "service_type_enum": [],
    "business_type_enum": [],
    "equipment_name_enum": [],
    "unit_enum": [],
    "aliases": {}
  }
}
```

输出：

```json
{
  "success": true,
  "data": {
    "requirement_count": 2,
    "requirements": []
  },
  "error": null
}
```

### 11.4 脚本职责边界

建议脚本内部拆为：

- `preprocess_email()`
- `split_requirements()`
- `extract_fields()`
- `map_to_enums()`
- `build_output()`

---

## 十二、SKILL.md 创建建议

按照你提供的 OpenClaw Skill 创建规范，S5 目录建议如下：

```text
parse-requirement-skill/
├── SKILL.md
├── README.md
├── .env.example
├── scripts/
│   └── main.py
└── references/
    └── r2-sample-enums.json
```

### 12.1 建议的 slug

```yaml
slug: parse-requirement-skill
```

### 12.2 SKILL.md 中应强调的 Use Case

#### When to Use
- 用户输入为自然语言邮件
- 邮件中可能包含多个服务项
- 需要先拆分再进入后续评估流程
- 需要将自然语言映射为标准枚举字段

#### When NOT to Use
- 输入已经是标准化结构化需求单
- 已经完成字段提取和拆分
- 仅需做历史案例检索时

---

## 十三、与后续 Skills 的衔接方式

### 13.1 S5 → S1

S5 为每个 RequirementItem 提供：

- `business_type.code`
- `service_desc.code`
- `service_type.code`
- `equipment_model.code/name`
- `remark`

作为 S1 的检索输入。

### 13.2 S5 → S2

S2 可直接使用：

- `service_type`
- `equipment_name` / `service_desc`
- `remark`

进行风险匹配。

### 13.3 S5 → S6

S6 负责汇总多个 RequirementItem 的后续处理结果，最终生成多个需求单或多个报告块。

### 13.4 多服务项并行执行建议

```text
S5 输出 requirements[0...N]
    ↓
for each requirement:
    并行执行 S1 / S2 / S4 / ...
```

这样能自然支持“一封邮件拆多个需求单”的业务模式。

---

## 十四、异常场景与降级策略

### 14.1 无法识别服务项
策略：
- 输出 1 个低置信度 RequirementItem
- 保留原始摘要
- 标记必须人工确认

### 14.2 可识别设备，但无法识别服务类型
策略：
- 保留设备信息
- `service_type = null`
- `needs_user_confirmation = true`

### 14.3 同一句话可能对应多个服务类型
策略：
- 输出主候选 + ambiguities
- 不强制单值拍板

### 14.4 型号抽取成功，但无法命中枚举
策略：
- 保留原始型号文本
- 标记“未标准化”

### 14.5 邮件同时描述多个设备，但边界不清
策略：
- 优先按设备对象拆分
- 若仍不清晰，则输出较少拆分结果并提升人工确认标记

---

## 十五、未来扩展设计

### 15.1 附件扩展

虽然当前阶段不处理附件，但应保留输入结构：

```json
"attachments": []
```

未来可扩展支持：

- PDF
- Word
- Excel
- 图片/OCR
- 邮件附件中的设备清单

### 15.2 更强的别名映射库

后续可将别名体系扩展为：

- 英文别名
- 中文别名
- 缩写词
- 历史高频表达
- 错拼纠正

### 15.3 交互式补问能力

当前 S5 先输出待确认项。  
未来可扩展为由上层 Agent 自动追问：

- “这里提到的 boiler 是指辅锅炉还是废气锅炉？”
- “inspection 是仅检查还是包含维修？”

---

## 十六、待确认事项

### ✅ 当前已确认

| 编号 | 问题 | 当前结论 |
|------|------|---------|
| 1 | 输入形式 | 非结构化自然语言邮件，不是标准表单 |
| 2 | 文本长度 | 通常为几百个单词以内 |
| 3 | 是否包含附件 | 当前阶段不考虑，但保留扩展性 |
| 4 | 是否可能多个服务项 | 是，必须支持拆分为多个需求单 |
| 5 | 枚举是否完整 | 当前未齐备，可先用少量占位枚举 |
| 6 | 模型配置 | 不单独在 Skill 内配置，复用上层 Agent 当前模型 |
| 7 | R2 的使用方式 | 作为全局共享 Reference，Skill 按需读取子集 |

### 🔶 后续仍建议确认

1. 服务描述枚举的第一版占位集合
2. 服务类型枚举的第一版占位集合
3. 业务归口与设备对象之间是否存在固定映射
4. 同一设备对象下多问题是否默认合并还是细拆
5. 上层 Agent 是否允许 S5 输出后进行一次人工确认再进入 S1

---

*文档持续更新中，最后修改：2026-03-23*