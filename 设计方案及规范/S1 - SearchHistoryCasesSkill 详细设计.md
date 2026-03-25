# S1 - SearchHistoryCasesSkill 详细设计

> 创建日期：2026-03-21  
> 最后修改：2026-03-21  
> 状态：设计确认  
> 所属模块：智能评估 Agent — Skills 层

---

## 目录

1. [Skill 定位与职责](#一skill-定位与职责)
2. [数据来源与现状](#二数据来源与现状)
3. [字段取舍决策](#三字段取舍决策)
4. [数据洞察与关键规律](#四数据洞察与关键规律)
5. [数据库表结构设计（DDL）](#五数据库表结构设计ddl)
6. [数据入库流程](#六数据入库流程)
7. [渐进式 Agentic 检索流程](#七渐进式-agentic-检索流程)
8. [检索 SQL 设计](#八检索-sql-设计)
9. [Skill 逻辑伪代码](#九skill-逻辑伪代码)
10. [返回结果结构](#十返回结果结构)
11. [关于向量数据库的决策](#十一关于向量数据库的决策)
12. [待确认事项](#十二待确认事项)

---

## 一、Skill 定位与职责

| 项目 | 内容 |
|------|------|
| **Skill 名称** | SearchHistoryCasesSkill |
| **原形式** | R1 Reference → 升级为 Agentic Search Skill |
| **核心职责** | 根据当前服务需求单，从 8000 条历史评估记录中渐进式检索最相似的 Top-K 案例，作为评估报告生成的核心参考依据 |
| **调用方** | GenerateReportSkill（主流程）/ 上层 Agent 直接调用（`search_similar` 接口） |
| **实施阶段** | MVP 必须 |

### 为何从 RAG Reference 升级为 Agentic Search Skill

| 对比维度 | RAG Reference | Agentic Search Skill |
|---------|--------------|---------------------|
| 检索方式 | 单次检索，Top-K 全部塞入 context | 多步渐进，根据中间结果动态调整策略 |
| 候选集控制 | 无法动态调整 | 先宽筛后精排，自动扩大/收窄条件 |
| Context 占用 | 输出侧 JSON 内容复杂，Top-K 极易过长 | 按需返回，只传必要字段摘要 |
| 适合数据类型 | 非结构化文本块 | 结构化记录（本场景主检索维度均为枚举编码） |

---

## 二、数据来源与现状

| 项目 | 情况 |
|------|------|
| 数据量 | 8000 条 |
| 原始格式 | xlsx，约 2.46MB |
| 特殊结构 | 多列存储 JSON 格式内容（人员、工具、耗材等） |
| 备注填写率 | 约 50% |
| 服务类型填写率 | 约 95%（允许 NULL，不强制） |
| 综述总人数 / 总天数填写率 | 约 80% |
| 综述工作制填写率 | 约 60% |
| 工作制含义 | **仅非航修任务记录该值**；1~6 分别为：8小时/日，9小时/日，10小时/日，11小时/日，12小时/日，24小时/日 |
| 备注语言 | 英文为主，含简体中文、繁体中文、韩语、日语 |

### 原始表头（完整）

```
项目信息_询单号 / 项目信息_服务单号 / 项目信息_业务归口 /
项目信息_设备型号（已弃用）/ 项目信息_新设备型号 / 项目信息_设备厂家 /
项目信息_设备数量 / 项目信息_部件型号 / 项目信息_备注或项目描述 /
项目信息_技术评估结果 / 项目信息_主机阀评估 / 项目信息_评估审核状态 /
项目信息_设计数量 / 项目信息_服务单状态 / 项目信息_招标状态 /
项目信息_终止原因 / 项目信息_系统节点 / 项目信息_审核结果 /
项目信息_审核意见 / 项目信息_服务增值技术 / 项目信息_评估按钮控制 /
项目信息_阀评估按钮控制 / 项目信息_审核按钮控制 / 项目信息_指定评估大区 /
项目信息_预评估人 / 项目信息_创建时间 / 项目信息_更新时间 /
项目信息_评估时间 / 项目信息_审核时间 /
评估内容_风险提示类型（已弃用）/ 评估内容_风险提示 / 评估内容_附件编码列表 /
评估内容_施工工时 / 评估内容_检测工时 / 评估内容_施工任务描述 /
评估内容_评估内容描述 / 评估内容_评估备注 / 评估内容_第三方类型 /
评估内容_综述总人数 / 评估内容_综述总天数 / 评估内容_综述工作制 /
记录内容_服务描述内容 / 记录内容_服务类型内容 / 记录内容_设备内容 /
记录内容_单位内容 / 记录内容_人员内容 / 记录内容_需求工具 /
记录内容_耗材相关 / 记录内容_专业工具相关 /
记录内容_检测项目（已弃用）/ 记录内容_辅助费用（已弃用）/
记录内容_评估人姓名 / 记录内容_审核人姓名
```

---

## 三、字段取舍决策

### 🗑️ 完全丢弃（系统/流程/UI 管理类，及已确认弃用字段）

| 字段 | 丢弃原因 |
|------|---------|
| `项目信息_设备型号` | 官方已弃用，由新设备型号替代 |
| `评估内容_风险提示类型` | 业务方已确认弃用 |
| `记录内容_检测项目` | 业务方已确认不需要 |
| `记录内容_辅助费用` | 业务方已确认弃用 |
| `项目信息_服务单状态` | 流程状态字段，无评估语义 |
| `项目信息_招标状态` | 流程状态字段 |
| `项目信息_终止原因` | 异常流程字段 |
| `项目信息_系统节点` | JSON 流转节点（CREATE/EVALUATE/REVIEW），纯系统日志 |
| `项目信息_审核结果` | "通过"等，纯流程字段 |
| `项目信息_审核意见` | "合理/通过"等，纯流程字段 |
| `项目信息_评估审核状态` | 流程状态 |
| `项目信息_评估按钮控制` | 前端 UI 控制字段 |
| `项目信息_阀评估按钮控制` | 前端 UI 控制字段 |
| `项目信息_审核按钮控制` | 前端 UI 控制字段 |
| `项目信息_创建时间` | 无检索语义价值 |
| `项目信息_更新时间` | 无检索语义价值 |
| `项目信息_审核时间` | 无检索语义价值 |
| `评估内容_附件编码列表` | 附件引用，内容不可访问 |
| `项目信息_服务增值技术` | 当前数据均为空 |
| `项目信息_预评估人` | 当前数据均为空 |
| `项目信息_指定评估大区` | 当前数据均为"无大区" |
| `项目信息_设计数量` | 当前数据均为空 |
| `项目信息_技术评估结果` | 固定值"专家评估"，无区分意义 |

---

### ✅ 保留字段分类

#### 检索侧（主维度，精确匹配，必建索引）

| 原始字段 | 数据库字段名 | 类型 | 说明 |
|---------|------------|------|------|
| `项目信息_业务归口` | `business_type` | VARCHAR(20) | **主检索维度**，必填，精确匹配 |
| `记录内容_服务描述内容` → `serviceDescriptionCode` | `service_desc_code` | VARCHAR(50) | **主检索维度**，精确匹配 |
| `记录内容_服务描述内容` → `serviceDescriptionName` | `service_desc_name` | VARCHAR(100) | 名称冗余存储，展示用 |
| `记录内容_服务类型内容` → `serviceTypeCode` | `service_type_code` | VARCHAR(50) | **次检索维度**，允许 NULL，95% 有值 |
| `记录内容_服务类型内容` → `serviceTypeName` | `service_type_name` | VARCHAR(100) | 名称冗余存储，展示用 |
| `项目信息_新设备型号` → `newEquipmentModelCode` | `equipment_model_code` | VARCHAR(50) | 加权检索，允许 NULL |
| `项目信息_新设备型号` → `newEquipmentModelName` | `equipment_model_name` | VARCHAR(200) | 名称冗余存储，展示用 |

#### 检索侧（辅助维度，有则参与排序）

| 原始字段 | 数据库字段名 | 类型 | 说明 |
|---------|------------|------|------|
| `项目信息_设备厂家` | `equipment_manufacturer` | VARCHAR(200) | 当前多为空，保留备用 |
| `项目信息_部件型号` | `equipment_part_model` | VARCHAR(200) | 当前多为空，保留备用 |
| `项目信息_设备数量` | `equipment_qty` | INTEGER | 影响工时/人数推断 |
| `记录内容_单位内容` | `equipment_unit` | VARCHAR(20) | 计量单位（台/个/PC） |
| `记录内容_设备内容` | `device_content` | VARCHAR(200) | 设备文本描述，pg_trgm 辅助匹配 |
| `评估内容_施工任务描述` | `task_description` | TEXT | **pg_trgm 模糊匹配主目标** |
| `项目信息_评估时间` | `evaluated_at` | TIMESTAMP | 时间衰减加权（近2年权重更高） |

#### 输出侧（参考生成评估报告，按需读取）

| 原始字段 | 数据库字段名 | 类型 | 备注 |
|---------|------------|------|------|
| `评估内容_风险提示` | `risk_description` | TEXT | 供 S2 种子提取和展示。`风险提示类型`字段已弃用，不导入 |
| `评估内容_施工工时` | `construction_hours` | DECIMAL(8,1) | 供 S3 工时统计 |
| `评估内容_检测工时` | `inspection_hours` | DECIMAL(8,1) | 供 S3 工时统计 |
| `评估内容_综述总人数` | `total_persons` | INTEGER | 供 S4 人力推理参考，填写率约 80% |
| `评估内容_综述总天数` | `total_days` | DECIMAL(6,1) | 供 S4 人力推理参考，填写率约 80% |
| `评估内容_综述工作制` | `work_schedule` | SMALLINT | 枚举值 1~6，含义待业务方确认；填写率约 60%，允许 NULL |
| `记录内容_人员内容` | → 展开为 `evaluation_personnel` 子表 | JSONB + 子表 | **最核心输出侧字段**，详见第五节 |
| `记录内容_需求工具` | `tools_content` | JSONB | 工具清单，结构见第四节 4.5 |
| `记录内容_耗材相关` | `materials_content` | JSONB | 耗材清单，结构见第四节 4.5 |
| `记录内容_专业工具相关` | `special_tools_content` | JSONB | 专用工具清单，结构见第四节 4.5 |

#### 辅助参考字段

| 原始字段 | 数据库字段名 | 类型 | 说明 |
|---------|------------|------|------|
| `项目信息_主机阀评估` | `main_valve_assessment` | VARCHAR(50) | 影响任务类型判断（不需要 / 需要） |
| `评估内容_第三方类型` | `third_party_type` | VARCHAR(20) | 枚举：`儒海` / `第三方` |
| `项目信息_备注或项目描述` | `remark` | TEXT | 50% 填写率，**不用于相似案例检索，仅供 S2 MatchRisksSkill 使用** |
| `评估内容_评估内容描述` | `assessment_description` | TEXT | 综合评估描述 |
| `评估内容_评估备注` | `assessment_remark` | TEXT | 评估附加备注 |
| `记录内容_评估人姓名` | `evaluator_name` | VARCHAR(50) | 飞轮追踪用，预留按评估人过滤的扩展能力 |
| `记录内容_审核人姓名` | `reviewer_name` | VARCHAR(50) | 飞轮追踪用，预留按审核人过滤的扩展能力 |

---

## 四、数据洞察与关键规律

### 4.1 设备型号字段的稀疏性与格式不统一

```
RH-000947：新设备型号为空（燃油管路类，不依附于特定主机型号）
RH-000933：7H21/32 X 3 5H21/32 X 1（多机组合描述）
RH-000956：5S50ME-B
RH-000957：9K98ME-C
RH-000961：MAN B&W-9S90ME-C9.2-TII（含品牌前缀）
```

**结论**：设备型号不总是存在，格式也不统一。设计决策：
- **不能**作为必填检索条件
- 有值时作为**加权因子**（`equipment_model_code` 精确命中则排序优先）
- 依赖编码匹配，而非名称字符串匹配

### 4.2 服务类型的空值情况

同类任务（坞修保养）中，部分记录有服务类型值，部分没有：

```
RH-000956（电喷机坞修保养）  ：service_type_code = NULL
RH-000957（主机电喷机坞修保养）：service_type_code = NULL
RH-000961（主机常规坞修保养） ：service_type_code = CS0017（保养10年）
```

**结论**：服务类型条件必须允许 NULL，检索时用 `OR NULL` 逻辑处理，不能强制精确匹配。

### 4.3 `记录内容_人员内容` JSON 的任务分组规律

以 RH-000961（最复杂，9人配置）为例：

```
任务组1："主机常规坞修保养工作"
  - 高级工程师(T5) × 1，轮机工程师，110h
  - 技师(P5)       × 1，安装工，    110h
  - 高级技工(P4)   × 1，安装工，    110h
  - 中级技工(P3)   × 1，安装工，    110h
  - 初级工(P2)     × 1，安装工，    110h
  - 实习(P1)       × 1，安装工，    110h

任务组2："ICCP接地装置换新"
  - 中级工程师(T4) × 1，电气工程师，12h
  - 初级工(P2)     × 1，低压电工，  12h
```

**结论**：`detailedJobResponsibilities` 是**任务分组的关键字段**，相同描述的条目属于同一施工任务。这一规律对 S4 人力调度推理（总人数计算）至关重要，需在子表中保留此字段并建立索引。

### 4.4 备注字段的内容特征

有备注的样本内容分析：

```
RH-000947：动火作业报备；管路材料清关；现场施工安全要求
RH-000956：影响工期因素（交叉作业 / 盘车机 / 进出坞）
RH-000957：影响工期因素（备件等待 / 进出坞 / 交叉作业）
RH-000961：内含船厂常规工作；工期推迟因素；试航二次登轮
```

**结论**：备注内容高度接近**风险提示和工期影响因素**，与 `评估内容_风险提示` 字段语义重叠。备注**不适合作为检索维度**，适合作为 S2 风险匹配的辅助输入。

### 4.5 三类物料清单 JSON 结构对比

三类物料字段结构**各不相同**，主要差异在于：耗材和专用工具有 `model`（型号）字段，需求工具有 `toolTypeNo`（工具类型编码）字段，且耗材/专用工具的 `toolTypeNo` 均为 `null`。入库时直接以 JSONB 存储，不展开为子表，应用层解析时需按字段分别处理。

#### 需求工具（`tools_content`）

```json
[
  {
    "quantity": 1,
    "toolName": "LDM",
    "toolTypeNo": 4,
    "unitMeasurement": {
      "no": "UM0005",
      "zhName": "台"
    }
  }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `toolName` | string | 工具名称 |
| `toolTypeNo` | integer | 工具类型编码（对应 R2 枚举，**耗材/专用工具此字段为 null**） |
| `quantity` | integer | 数量 |
| `unitMeasurement.no` | string | 单位编码 |
| `unitMeasurement.zhName` | string | 单位名称 |

#### 耗材相关（`materials_content`）

```json
[
  {
    "model": "40L",
    "quantity": 3,
    "toolName": "氧气",
    "toolTypeNo": null,
    "unitMeasurement": {
      "no": "UM0018",
      "zhName": "瓶"
    }
  },
  {
    "model": "30L",
    "quantity": 1,
    "toolName": "丙烷",
    "toolTypeNo": null,
    "unitMeasurement": {
      "no": "UM0018",
      "zhName": "瓶"
    }
  },
  {
    "model": "1KG",
    "quantity": 1,
    "toolName": "铅皮",
    "toolTypeNo": null,
    "unitMeasurement": {
      "no": "UM0028",
      "zhName": "千克"
    }
  }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `toolName` | string | 耗材名称 |
| `model` | string | **耗材型号**（需求工具无此字段） |
| `toolTypeNo` | null | 固定为 null，耗材不使用此字段 |
| `quantity` | integer | 数量 |
| `unitMeasurement.no` | string | 单位编码 |
| `unitMeasurement.zhName` | string | 单位名称 |

#### 专用工具相关（`special_tools_content`）

```json
[
  {
    "model": "符合甲板面积",
    "quantity": 2,
    "toolName": "驳船",
    "toolTypeNo": null,
    "unitMeasurement": {
      "no": "UM0150",
      "zhName": "次"
    }
  }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `toolName` | string | 专用工具名称 |
| `model` | string | **专用工具型号**（与耗材相同，需求工具无此字段） |
| `toolTypeNo` | null | 固定为 null，专用工具不使用此字段 |
| `quantity` | integer | 数量 |
| `unitMeasurement.no` | string | 单位编码 |
| `unitMeasurement.zhName` | string | 单位名称 |

#### 三类物料字段差异汇总

| 字段 | 需求工具 | 耗材 | 专用工具 |
|------|---------|------|---------|
| `toolName` | ✅ | ✅ | ✅ |
| `model`（型号） | ❌ 无 | ✅ | ✅ |
| `toolTypeNo` | ✅ 有值 | ✅ 但固定 null | ✅ 但固定 null |
| `quantity` | ✅ | ✅ | ✅ |
| `unitMeasurement` | ✅ | ✅ | ✅ |

### 4.6 综述字段的填写率影响

| 字段 | 填写率 | 设计影响 |
|------|--------|---------|
| 综述总人数 | ~80% | S4 人力推理可参考，但需兜底（无值时纯推理） |
| 综述总天数 | ~80% | 同上 |
| 综述工作制 | ~60% | **仅非航修记录时填写**；S4 可辅助参考，允许 NULL。枚举值含义如下： |
| **工作制 1** | 8小时/日 | |
| **工作制 2** | 9小时/日 | |
| **工作制 3** | 10小时/日 | |
| **工作制 4** | 11小时/日 | |
| **工作制 5** | 12小时/日 | |
| **工作制 6** | 24小时/日 | |

### 4.7 第三方类型枚举值

`评估内容_第三方类型` 当前仅有两个值：`儒海` / `第三方`，属于**二值枚举**，数据库字段设计为 `VARCHAR(20)` 足够，无需单独建枚举表。

---

## 五、数据库表结构设计（DDL）

### 5.1 主表：evaluation_records

```sql
CREATE TABLE evaluation_records (

    -- =========================================================
    -- 主键与业务标识
    -- =========================================================
    id                      BIGSERIAL PRIMARY KEY,
    inquiry_no              VARCHAR(50) NOT NULL,
    -- 询单号（业务标识，如 RH-2025-000961）

    service_order_no        VARCHAR(50) NOT NULL UNIQUE,
    -- 服务单号（唯一，如 RH-2025-0009611001）

    -- =========================================================
    -- 检索侧：主维度（精确匹配，必建索引）
    -- =========================================================
    business_type           VARCHAR(20) NOT NULL,
    -- 业务归口：电气 / 轮机

    service_desc_code       VARCHAR(50),
    service_desc_name       VARCHAR(100),
    -- 服务描述编码/名称，如 RS0000000001 / 二冲程柴油机
    -- 来源：记录内容_服务描述内容 JSON 展开

    service_type_code       VARCHAR(50),
    service_type_name       VARCHAR(100),
    -- 服务类型编码/名称，如 CS0006 / 健康检查
    -- 允许 NULL（填写率约 95%，但同类任务命名不统一）
    -- 来源：记录内容_服务类型内容 JSON 展开

    -- =========================================================
    -- 检索侧：设备维度（允许 NULL，有则加权匹配）
    -- =========================================================
    equipment_model_code    VARCHAR(50),
    equipment_model_name    VARCHAR(200),
    -- 新设备型号编码/名称，如 ET000000000005 / 6S50MC
    -- 来源：项目信息_新设备型号 JSON 展开
    -- ⚠️ 项目信息_设备型号（旧字段）已弃用，不导入

    equipment_manufacturer  VARCHAR(200),
    -- 设备厂家（当前数据多为空，保留备用）

    equipment_part_model    VARCHAR(200),
    -- 部件型号（当前数据多为空，保留备用）

    equipment_qty           INTEGER,
    -- 设备数量

    equipment_unit          VARCHAR(20),
    -- 计量单位（台 / 个 / PC 等）
    -- 来源：记录内容_单位内容

    -- =========================================================
    -- 检索侧：任务描述文本（pg_trgm 模糊匹配）
    -- =========================================================
    task_description        TEXT,
    -- 施工任务描述，如"主机健康检查,LDM"
    -- 来源：评估内容_施工任务描述

    device_content          VARCHAR(200),
    -- 设备内容文本，如"传统二冲程柴油机"
    -- 来源：记录内容_设备内容

    -- =========================================================
    -- 输出侧：风险（供 S2 MatchRisksSkill 种子提取和展示）
    -- =========================================================
    risk_description        TEXT,
    -- 风险提示文字内容
    -- ⚠️ 风险提示类型字段已弃用，不导入

    -- =========================================================
    -- 输出侧：汇总工时与人力数据
    -- =========================================================
    construction_hours      DECIMAL(8,1),
    -- 施工工时（供 S3 工时统计）

    inspection_hours        DECIMAL(8,1),
    -- 检测工时（供 S3 工时统计）

    -- 综述字段
    total_persons           INTEGER, -- 综述总人数（供 S4 人力推理参考，填写率约 80%）
    total_days              DECIMAL(6,1), -- 综述总天数（填写率约 80%）
    work_schedule           SMALLINT, -- 工作制（非航修任务填写，1~6 枚举值 -- 8小时至24小时/日）
    -- 工作制枚举值（1~6），填写率约 60%，允许 NULL
    -- ⚠️ 各枚举值的业务含义待业务方确认后补充注释
    -- S4 仅作辅助参考，不能依赖此字段

    -- =========================================================
    -- 输出侧：三类物料清单 JSONB
    -- 三类结构不同，直接存储，应用层按字段分别解析
    -- =========================================================
    tools_content           JSONB,
    -- 需求工具清单
    -- 结构：[{quantity, toolName, toolTypeNo(有值), unitMeasurement:{no,zhName}}]

    materials_content       JSONB,
    -- 耗材相关清单
    -- 结构：[{model(型号), quantity, toolName, toolTypeNo(null), unitMeasurement:{no,zhName}}]

    special_tools_content   JSONB,
    -- 专业工具清单
    -- 结构：[{model(型号), quantity, toolName, toolTypeNo(null), unitMeasurement:{no,zhName}}]
    -- 与耗材结构相同，差异仅在语义（专用设备 vs 消耗物料）

    -- =========================================================
    -- 辅助参考字段
    -- =========================================================
    main_valve_assessment   VARCHAR(50),
    -- 主机阀评估（不需要 / 需要）

    third_party_type        VARCHAR(20),
    -- 第三方类型，枚举：儒海 / 第三方

    remark                  TEXT,
    -- 备注（填写率约 50%）
    -- ⚠️ 不用于相似案例检索，仅供 S2 MatchRisksSkill 使用

    assessment_description  TEXT,
    -- 评估内容描述

    assessment_remark       TEXT,
    -- 评估备注

    evaluator_name          VARCHAR(50),
    -- 评估人姓名（飞轮追踪用，预留按评估人过滤的扩展能力）

    reviewer_name           VARCHAR(50),
    -- 审核人姓名（飞轮追踪用，预留按审核人过滤的扩展能力）

    evaluated_at            TIMESTAMP,
    -- 评估时间（用于时间衰减加权，近2年权重更高）

    created_at              TIMESTAMP DEFAULT NOW()
);

-- =========================================================
-- 索引
-- =========================================================

-- 单列索引：高频过滤字段
CREATE INDEX idx_er_business_type    ON evaluation_records(business_type);
CREATE INDEX idx_er_service_desc     ON evaluation_records(service_desc_code);
CREATE INDEX idx_er_service_type     ON evaluation_records(service_type_code);
CREATE INDEX idx_er_equipment_model  ON evaluation_records(equipment_model_code);
CREATE INDEX idx_er_evaluated_at     ON evaluation_records(evaluated_at DESC);

-- 组合索引：最常用的三维度过滤组合
CREATE INDEX idx_er_core_search
    ON evaluation_records(business_type, service_desc_code, service_type_code);

-- pg_trgm 索引：任务描述与设备内容的模糊匹配
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX idx_er_task_trgm
    ON evaluation_records USING GIN(task_description gin_trgm_ops);

CREATE INDEX idx_er_device_trgm
    ON evaluation_records USING GIN(device_content gin_trgm_ops);
```

---

### 5.2 人员子表：evaluation_personnel

> 从 `记录内容_人员内容` JSON 数组逐条展开，便于 S3 工时统计和 S4 人力调度推理直接查询，避免每次在应用层解析 JSON 字符串。

```sql
CREATE TABLE evaluation_personnel (

    id                            BIGSERIAL PRIMARY KEY,
    record_id                     BIGINT NOT NULL
                                      REFERENCES evaluation_records(id)
                                      ON DELETE CASCADE,

    -- 工种
    work_type_code                VARCHAR(20),
    -- 如 JN0001

    work_type_name                VARCHAR(50),
    -- 如 电气工程师

    -- 职级
    job_level_code                VARCHAR(20),
    -- 如 RN0009

    job_level_name                VARCHAR(50),
    -- 如 中级工程师(T4)

    -- 任务明细
    quantity                      INTEGER,
    -- 该条目所需人数

    construction_hour             DECIMAL(6,1),
    -- 该条目工时（小时）

    detailed_job_responsibilities TEXT,
    -- 详细工作内容（任务分组键）
    -- 相同描述的条目属于同一施工任务，是 S4 人力调度的任务分组依据
    -- 允许 NULL（历史数据中存在未填写情况，标记为保留）

    sort_order                    INTEGER
    -- 保留原始 JSON 数组顺序
);

-- =========================================================
-- 索引
-- =========================================================

-- 关联查询
CREATE INDEX idx_ep_record_id     ON evaluation_personnel(record_id);

-- S3 工时统计：按工种聚合
CREATE INDEX idx_ep_work_type     ON evaluation_personnel(work_type_code);

-- S4 人力推理：按职级查询
CREATE INDEX idx_ep_job_level     ON evaluation_personnel(job_level_code);

-- S3 工时统计：按任务内容聚合（pg_trgm 支持相似任务归类）
CREATE INDEX idx_ep_job_resp_trgm
    ON evaluation_personnel
    USING GIN(detailed_job_responsibilities gin_trgm_ops);
```

---

### 5.3 表关系说明

```
evaluation_records              (主表，1条 = 1个历史评估案例)
        │
        │  1 : N
        ▼
evaluation_personnel            (人员明细子表，从人员内容 JSON 展开)

每条子表记录 = 1个「工种 + 职级 + 人数 + 工时 + 任务描述」条目

同一 record_id 下，相同 detailed_job_responsibilities 的多条记录
= 同一施工任务的多人配置（S4 任务分组的依据）
```

---

## 六、数据入库流程

```
原始 xlsx 文件
        │
        ▼
Step 1：列过滤与废弃列清除
        丢弃全部系统/流程/UI 控制字段（见第三节废弃列表）
        丢弃：项目信息_设备型号（旧）
        丢弃：评估内容_风险提示类型
        丢弃：记录内容_检测项目
        丢弃：记录内容_辅助费用
        统计各字段填写率，记录异常

        │
        ▼
Step 2：JSON 列展开
        ┌────────────────────────────────────────────────────┐
        │ 项目信息_新设备型号                                  │
        │   → 提取 newEquipmentModelCode / newEquipmentModelName│
        │                                                    │
        │ 记录内容_服务描述内容                                │
        │   → 提取 serviceDescriptionCode / Name             │
        │                                                    │
        │ 记录内容_服务类型内容                                │
        │   → 提取 serviceTypeCode / Name（允许整列为 NULL）   │
        │                                                    │
        │ 记录内容_人员内容（JSON 数组）                        │
        │   → 逐条展开为 evaluation_personnel 子表行           │
        │   → 保留 sort_order（数组下标）                     │
        │   → detailed_job_responsibilities 为 NULL 时保留    │
        │     该条目，字段值维持 NULL                          │
        │                                                    │
        │ 记录内容_需求工具 / 耗材相关 / 专业工具相关            │
        │   → 直接以 JSONB 存储，不展开                       │
        │   → 三类结构不同，应用层分别解析（见第四节 4.5）      │
        └────────────────────────────────────────────────────┘

        │
        ▼
Step 3：数据清洗
        枚举值归一化（修正历史不规范录入，如大小写、别名）
        equipment_unit 标准化：'PC' / 'pc' → 统一为 'PC'
        third_party_type 合法值校验：仅允许 '儒海' / '第三方'
        work_schedule 合法值校验：仅允许 1~6 或 NULL
        NULL 值处理：标记而非删除，保留不完整记录的部分价值

        │
        ▼
Step 4：知识挖掘（入库副产品，同步生成其他模块种子数据）
        ├── 提取高频 risk_description 内容
        │   → 写入 S2 MatchRisksSkill 风险库种子数据
        ├── 统计 tools_content 高频条目（按 toolName 聚合）
        │   统计 materials_content 高频条目（按 toolName + model 聚合）
        │   统计 special_tools_content 高频条目（按 toolName + model 聚合）
        │   → 写入 R4 工具耗材推荐模板种子数据
        └── 分析 evaluation_personnel 工时分布
            按（工种 × 服务类型）聚合 P50 / P80 / P95
            → 写入 S3 EstimateWorkHoursSkill 经验数据

        │
        ▼
Step 5：写入数据库
        ① 先写 evaluation_records 主表，获取自增 id
        ② 再写 evaluation_personnel 子表（关联 record_id）
        ③ JSONB 字段直接写入（tools / materials / special_tools）
        ④ 建议：批量导入完成后再统一建索引（提升导入速度）
```

---

## 七、渐进式 Agentic 检索流程

```
输入：RequirementInput
  ├── business_type        （必填）
  ├── service_desc_code    （必填）
  ├── service_type_code    （可 NULL）
  ├── equipment_model_code （可 NULL）
  ├── task_description     （可 NULL，用于 trgm 排序）
  ├── remark               （可 NULL，仅供备注相似度补充）
  └── top_k                （默认 5，上层 Agent 可动态配置）

        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1：精确结构化粗筛                                   │
│  条件：business_type（必须）                              │
│       + service_desc_code（必须）                        │
│       + service_type_code（允许 NULL，OR NULL 逻辑）      │
│  排序：设备型号精确命中 > trgm 相似度 > 时间衰减           │
│  返回：候选集最多 20 条                                   │
└─────────────────────────────────────────────────────────┘
        │
        ├─ 候选集 >= 5 条 ────────────────────────────────┐
        │                                                │
        └─ 候选集 < 5 条                                 │
                │                                       │
                ▼                                       │
┌──────────────────────────────────────┐                │
│  Step 2B：自动放宽条件重查             │                │
│  去掉 service_type_code 条件          │                │
│  仅保留：business_type               │                │
│         + service_desc_code          │                │
│  重新取候选集最多 20 条               │                │
│  ⚠️ 返回结果标注"服务类型条件已放宽"  │                │
└──────────────────────────────────────┘                │
        │                                               │
        └───────────────────────────────────────────────┘
                                                        │
                                                        ▼
                                        ┌───────────────────────────────┐
                                        │  Step 2A：取 Top-K            │
                                        │  候选集截取前 top_k 条         │
                                        │  拉取 evaluation_personnel    │
                                        │  子表明细（批量查询）          │
                                        └───────────────────────────────┘
                                                        │
                                                        ▼
                                        ┌───────────────────────────────┐
                                        │  Step 3：备注相似度补充（可选）│
                                        │  仅当输入有 remark 时执行      │
                                        │  计算 Top-K 各案例的备注相似度 │
                                        │  不改变排序，只增加匹配说明    │
                                        └───────────────────────────────┘
                                                        │
                                                        ▼
                                        ┌───────────────────────────────┐
                                        │  Step 4：构建返回结果          │
                                        │  生成每条结果的匹配依据说明    │
                                        └───────────────────────────────┘

输出：Top-K 历史案例列表（含匹配依据、人员明细、工具清单等）
```

---

## 八、检索 SQL 设计

### 8.1 Step 1：精确结构化粗筛

```sql
SELECT
    er.id,
    er.service_order_no,
    er.business_type,
    er.service_desc_name,
    er.service_type_name,
    er.equipment_model_code,
    er.equipment_model_name,
    er.equipment_qty,
    er.equipment_unit,
    er.task_description,
    er.device_content,
    er.risk_description,
    er.total_persons,
    er.total_days,
    er.work_schedule,
    er.construction_hours,
    er.inspection_hours,
    er.evaluated_at,
    er.tools_content,
    er.materials_content,
    er.special_tools_content,
    -- trgm 相似度：输入无任务描述时为 0
    CASE
        WHEN :input_task_desc IS NOT NULL
        THEN similarity(er.task_description, :input_task_desc)
        ELSE 0
    END AS task_sim_score
FROM evaluation_records er
WHERE
    er.business_type = :business_type
    AND er.service_desc_code = :service_desc_code
    AND (
        :service_type_code IS NULL
        OR er.service_type_code IS NULL
        OR er.service_type_code = :service_type_code
    )
ORDER BY
    -- 优先级1：设备型号编码精确命中
    CASE
        WHEN :equipment_model_code IS NOT NULL
             AND er.equipment_model_code = :equipment_model_code
        THEN 0 ELSE 1
    END ASC,
    -- 优先级2：任务描述 trgm 相似度（降序）
    task_sim_score DESC,
    -- 优先级3：时间衰减（近2年优先）
    CASE
        WHEN er.evaluated_at > NOW() - INTERVAL '2 years' THEN 0
        WHEN er.evaluated_at > NOW() - INTERVAL '3 years' THEN 1
        ELSE 2
    END ASC,
    er.evaluated_at DESC
LIMIT 20;
```

---

### 8.2 Step 2B：放宽条件重查（候选集不足时）

```sql
-- 去掉 service_type_code 条件，其余与 Step 1 相同
SELECT
    er.id,
    er.service_order_no,
    -- ... 同 Step 1 字段清单 ...
    CASE
        WHEN :input_task_desc IS NOT NULL
        THEN similarity(er.task_description, :input_task_desc)
        ELSE 0
    END AS task_sim_score
FROM evaluation_records er
WHERE
    er.business_type = :business_type
    AND er.service_desc_code = :service_desc_code
    -- ⚠️ 已去掉 service_type_code 条件
ORDER BY
    CASE
        WHEN :equipment_model_code IS NOT NULL
             AND er.equipment_model_code = :equipment_model_code
        THEN 0 ELSE 1
    END ASC,
    task_sim_score DESC,
    CASE
        WHEN er.evaluated_at > NOW() - INTERVAL '2 years' THEN 0
        WHEN er.evaluated_at > NOW() - INTERVAL '3 years' THEN 1
        ELSE 2
    END ASC,
    er.evaluated_at DESC
LIMIT 20;
```

---

### 8.3 拉取人员明细（Top-K 确定后）

```sql
SELECT
    ep.record_id,
    ep.work_type_code,
    ep.work_type_name,
    ep.job_level_code,
    ep.job_level_name,
    ep.quantity,
    ep.construction_hour,
    ep.detailed_job_responsibilities,
    ep.sort_order
FROM evaluation_personnel ep
WHERE ep.record_id = ANY(:top_k_record_ids)
ORDER BY ep.record_id, ep.sort_order;
```

---

### 8.4 Step 3：备注相似度补充（可选）

```sql
-- 仅当输入有备注时执行
-- 结果只用于增加匹配说明，不改变排序
SELECT
    id,
    similarity(remark, :input_remark) AS remark_sim_score
FROM evaluation_records
WHERE
    id = ANY(:top_k_record_ids)
    AND remark IS NOT NULL
    AND similarity(remark, :input_remark) > 0.1
ORDER BY remark_sim_score DESC;
```

---

## 九、Skill 逻辑伪代码

```python
def search_history_cases(
    requirement: RequirementInput,
    top_k: int = 5,                 # 上层 Agent 可动态配置
    candidate_threshold: int = 5    # 触发放宽的候选集阈值
) -> List[HistoryCaseResult]:
    """
    渐进式历史案例检索 Skill（S1）

    Args:
        requirement: 服务需求单输入对象
        top_k: 返回案例数，默认 5，上层 Agent 可动态传入
        candidate_threshold: 候选集不足时触发条件放宽的阈值
    """

    # ── Step 1：精确结构化粗筛 ────────────────────────────
    candidates = db.query_evaluation_records(
        business_type        = requirement.business_type,        # 必填
        service_desc_code    = requirement.service_desc_code,    # 必填
        service_type_code    = requirement.service_type_code,    # 可 NULL
        equipment_model_code = requirement.equipment_model_code, # 可 NULL
        input_task_desc      = requirement.task_description,     # trgm 排序
        limit = 20
    )

    # ── Step 2B：候选不足时自动放宽 ──────────────────────
    relaxed = False
    if len(candidates) < candidate_threshold:
        candidates = db.query_evaluation_records(
            business_type        = requirement.business_type,
            service_desc_code    = requirement.service_desc_code,
            # service_type_code 条件已去除
            equipment_model_code = requirement.equipment_model_code,
            input_task_desc      = requirement.task_description,
            limit = 20
        )
        relaxed = True

    # ── 取 Top-K ────────────────────────────────────────
    top_cases = candidates[:top_k]

    # ── Step 2A：批量拉取人员明细 ────────────────────────
    personnel_map = db.get_personnel_by_record_ids(
        [c.id for c in top_cases]
    )
    for case in top_cases:
        case.personnel = personnel_map.get(case.id, [])

    # ── Step 3：备注相似度补充（可选）────────────────────
    if requirement.remark:
        remark_scores = db.get_remark_similarity(
            record_ids   = [c.id for c in top_cases],
            input_remark = requirement.remark
        )
        for case in top_cases:
            case.remark_sim_score = remark_scores.get(case.id, 0.0)

    # ── Step 4：构建返回结果 ─────────────────────────────
    return [
        HistoryCaseResult(
            case_id          = c.service_order_no,
            match_reason     = build_match_reason(c, requirement, relaxed),
            # 示例："命中：业务归口(轮机) + 服务描述(二冲程柴油机)
            #        + 设备型号(5S50ME-B) | 任务相似度: 0.82"
            # 放宽时追加："⚠️ 服务类型条件已放宽"
            task_sim_score   = c.task_sim_score,
            remark_sim_score = getattr(c, 'remark_sim_score', None),
            evaluated_at     = c.evaluated_at,
            equipment_info   = {
                "model_code": c.equipment_model_code,
                "model_name": c.equipment_model_name,
                "qty":        c.equipment_qty,
                "unit":       c.equipment_unit,
            },
            risk_description   = c.risk_description,
            task_description   = c.task_description,
            total_persons      = c.total_persons,     # 80% 有值
            total_days         = c.total_days,         # 80% 有值
            work_schedule      = c.work_schedule,      # 60% 有值，可 NULL，枚举 1~6
            construction_hours = c.construction_hours,
            inspection_hours   = c.inspection_hours,
            personnel = [
                PersonnelItem(
                    work_type_name    = p.work_type_name,
                    job_level_name    = p.job_level_name,
                    quantity          = p.quantity,
                    construction_hour = p.construction_hour,
                    task_desc         = p.detailed_job_responsibilities,
                )
                for p in c.personnel
            ],
            tools         = c.tools_content,
            materials     = c.materials_content,
            special_tools = c.special_tools_content,
        )
        for c in top_cases
    ]
```

---

## 十、返回结果结构

每条历史案例的返回格式（JSON）：

```json
{
  "case_id": "RH-2025-0009611001",
  "match_reason": "命中：业务归口(轮机) + 服务描述(二冲程柴油机) + 服务类型(保养10年) + 设备型号(MAN B&W-9S90ME-C9.2-TII) | 任务相似度: 0.76",
  "task_sim_score": 0.76,
  "remark_sim_score": 0.31,
  "evaluated_at": "2026-02-20T14:23:24",
  "equipment_info": {
    "model_code": "ET000000000826",
    "model_name": "MAN B&W-9S90ME-C9.2-TII",
    "qty": 1,
    "unit": "PC"
  },
  "risk_description": "1、内含船厂常规工作，船厂管理费金额高，船厂限制作业\n2、工期因交叉作业、备件、船厂进出坞、盘车等因素导致工期延迟\n3、因试航需要，可能产生二次登轮情况",
  "task_description": "主机常规坞修保养工作",
  "total_persons": 9,
  "total_days": null,
  "work_schedule": null,
  "construction_hours": null,
  "inspection_hours": null,
  "personnel": [
    {
      "work_type_name": "轮机工程师",
      "job_level_name": "高级工程师(T5)",
      "quantity": 1,
      "construction_hour": 110.0,
      "task_desc": "主机常规坞修保养工作"
    },
    {
      "work_type_name": "安装工",
      "job_level_name": "技师(P5)",
      "quantity": 1,
      "construction_hour": 110.0,
      "task_desc": "主机常规坞修保养工作"
    },
    {
      "work_type_name": "安装工",
      "job_level_name": "高级技工(P4)",
      "quantity": 1,
      "construction_hour": 110.0,
      "task_desc": "主机常规坞修保养工作"
    },
    {
      "work_type_name": "安装工",
      "job_level_name": "中级技工(P3)",
      "quantity": 1,
      "construction_hour": 110.0,
      "task_desc": "主机常规坞修保养工作"
    },
    {
      "work_type_name": "安装工",
      "job_level_name": "初级工(P2)",
      "quantity": 1,
      "construction_hour": 110.0,
      "task_desc": "主机常规坞修保养工作"
    },
    {
      "work_type_name": "安装工",
      "job_level_name": "实习(P1)",
      "quantity": 1,
      "construction_hour": 110.0,
      "task_desc": "主机常规坞修保养工作"
    },
    {
      "work_type_name": "电气工程师",
      "job_level_name": "中级工程师(T4)",
      "quantity": 1,
      "construction_hour": 12.0,
      "task_desc": "ICCP接地装置换新"
    },
    {
      "work_type_name": "低压电工",
      "job_level_name": "初级工(P2)",
      "quantity": 1,
      "construction_hour": 12.0,
      "task_desc": "ICCP接地装置换新"
    }
  ],
  "tools": [
    {
      "toolName": "LDM",
      "toolTypeNo": 4,
      "quantity": 1,
      "unitMeasurement": { "no": "UM0005", "zhName": "台" }
    }
  ],
  "materials": [
    {
      "toolName": "氧气",
      "model": "40L",
      "quantity": 3,
      "unitMeasurement": { "no": "UM0018", "zhName": "瓶" }
    }
  ],
  "special_tools": [
    {
      "toolName": "驳船",
      "model": "符合甲板面积",
      "quantity": 2,
      "unitMeasurement": { "no": "UM0150", "zhName": "次" }
    }
  ]
}
```

---

## 十一、关于向量数据库的决策

**结论：省略向量数据库，仅使用 PostgreSQL + pg_trgm。**

### 决策依据

| 分析维度 | 结论 |
|---------|------|
| 主检索维度 | `business_type` / `service_desc_code` / `service_type_code` 均为枚举编码，SQL 精确匹配完全足够 |
| 设备型号匹配 | 有 `equipment_model_code` 编码，精确匹配，无需语义理解 |
| 任务描述匹配 | 短文本 + 专业术语（如"主机健康检查,LDM"），pg_trgm trigram 匹配效果可接受 |
| 备注字段 | 50% 填写率，内容偏向风险提示，不适合作为主检索维度，不值得向量化 |
| 数据规模 | 8000 条，PostgreSQL 全表扫描 + 索引性能完全充裕 |
| 跨语言需求 | 检索维度均为结构化编码，不存在跨语言语义匹配问题 |
| 运维复杂度 | 避免引入额外基础设施（向量 DB + embedding 服务），降低维护成本 |

### 未来升级路径（如需）

若 `task_description` 的 pg_trgm 效果不理想（尤其中文短文本），可按以下路径升级，**无需重构整体架构**：

```
方案A（优先）：升级中文分词
  → 安装 zhparser 插件
  → 将 task_description 改为 tsvector 全文检索
  → 仍在 PostgreSQL 内完成，零额外基础设施

方案B（备选）：引入向量检索
  → 仅对 task_description 字段做向量化
  → 使用 pgvector 扩展，仍在 PostgreSQL 内
  → 无需单独部署向量数据库
```

---

## 十二、待确认事项

### ✅ 已确认

| 编号 | 问题 | 确认结论 |
|------|------|---------|
| 1 | 综述总人数/天数的填写率 | 约 80%，S4 可参考但需兜底 |
| 2 | 综述工作制填写率 | 约 60%，S4 仅作辅助参考，允许 NULL |
| 3 | `评估内容_风险提示类型` 的处理 | 已弃用，不导入 |
| 4 | `记录内容_检测项目` 的处理 | 已弃用，不导入 |
| 5 | `记录内容_辅助费用` 的处理 | 已弃用，不导入 |
| 6 | `评估内容_第三方类型` 的枚举值 | 仅 `儒海` / `第三方`，VARCHAR(20) 存储 |
| 7 | `记录内容_耗材相关` 的 JSON 结构 | 含 `model`（型号）字段，`toolTypeNo` 固定为 null，见第四节 4.5 |
| 8 | `记录内容_专业工具相关` 的 JSON 结构 | 与耗材结构相同，含 `model` 字段，`toolTypeNo` 固定为 null，见第四节 4.5 |
| 9 | Top-K 默认值及配置方式 | 默认 5 条，上层 Agent 可通过参数动态配置 |
| 10 | 按评估人/审核人过滤的需求 | 当前不需要，字段已保留，预留扩展能力 |
| 11 | `评估内容_综述工作制` 的含义 | 确认非航修时填写，1~6 分别对应：8小时/日，9小时/日，10小时/日，11小时/日，12小时/日，24小时/日 |

---

*文档持续更新中，最后修改：2026-03-21*