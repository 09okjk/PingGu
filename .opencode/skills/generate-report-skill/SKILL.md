---
name: generate-report-skill
slug: generate-report-skill
version: 1.0.0
description: 整合已确认需求、历史案例与评估推理结果，生成供工务审核和服贸报价准备使用的结构化评估报告草稿。
changelog: |
  ## [1.0.0] - MVP 初始版本
  - 支持单个 RequirementItem 的结构化评估报告生成
  - 支持风险、任务、总计、工具、耗材、专用工具、设备/备件三栏输出
  - 支持 confidence / source / warnings / review_focus
  - 支持“港口=航修”规则
metadata:
  clawdbot:
    emoji: 📋
    requires:
      bins: ["python3"]
      env: []
    os: ["linux", "darwin", "win32"]
---

# GenerateReportSkill

这是智能评估 Agent 的 S6 报告合成技能。  
用于把 S5 的已确认需求、S1 的历史案例、S2 的风险/工时/人数推理结果，整理成一份结构化评估报告草稿。

该报告的使用顺序为：

1. 工务人员先查看
2. 工务人员与 Agent 对话调整
3. 工务人员审核通过
4. 交给服贸人员用于报价准备

---

## When to Use

✅ 适用于：

- 已经完成 S5 需求确认
- 已经有 S1 历史案例结果
- 已经有 S2 评估推理结果
- 需要生成结构化评估报告草稿
- 需要给工务人员审核
- 需要给服贸人员提供报价依据

---

## When NOT to Use

❌ 不适用于：

- 原始邮件解析（请使用 S5）
- 历史案例检索（请使用 S1）
- 风险 / 工时 / 人数推理（请使用 S2）
- 直接生成报价单
- 直接生成报价项建议
- 多服务项合并总报告

---

## Setup

### 基础用法

```bash
python3 {baseDir}/scripts/main.py \
  --action generate_report \
  --json-input-file "{baseDir}/samples/sample-input.json" \
  --pretty
```

### 快速测试

```bash
cd {baseDir}

python3 scripts/main.py \
  --action generate_report \
  --json-input-file samples/sample-input.json \
  --pretty
```

---

## Options

| 选项 | 类型 | 说明 | 必需 |
|------|------|------|------|
| `--action` | `generate_report` | 执行动作 | ✅ |
| `--json-input-file` | `path` | 输入 JSON 文件路径 | ❌ 与 `--json-input` 二选一 |
| `--json-input` | `json` | 直接传入 JSON 字符串 | ❌ 与 `--json-input-file` 二选一 |
| `--pretty` | `flag` | 格式化输出 JSON | ❌ |

### 输出格式选项

在输入 JSON 的 `options` 中设置 `output_format`：

| 值 | 说明 | 适用场景 |
|----|------|----------|
| `markdown` | 输出 Markdown 格式报告（默认） | 工务人员直接阅读、对话交互 |
| `json` | 输出 JSON 格式 | 程序调用、数据交换 |

**示例**：
```json
{
  "options": {
    "output_format": "markdown",
    "output_language": "zh-CN"
  }
}
```

---

## Input Contract

输入对象结构：

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

## Output Contract

### Markdown 格式（默认，人类可读）

```markdown
# 评估报告草稿

## 一、服务需求概要

- **业务归口**: 轮机
- **服务描述**: 火警系统
- **服务类型**: 维修
...
```

### JSON 格式（程序调用）

```json
{
  "success": true,
  "data": {
    "requirement_id": "req-001",
    "status": "ok",
    "report_version": "1.0.0",
    ...
  },
  "error": null
}
```

---

## Core Rules

1. **一项一报**
2. **结构化表格优先**
3. **是否航修取决于 S5 的服务地点类型**
   - 若 `service_location_type.name == "港口"`，则判定为航修
4. **设备 / 备件需求必须拆成三栏**
   - `customer_provided`
   - `provider_provided`
   - `to_be_confirmed`
5. **工具 / 耗材不区分必需/建议**
6. **S6 不重新做底层推理**
7. **核心字段必须带 `confidence` 与 `source`**

---

## Related Skills

- `parse-requirement-skill`: 需求解析与确认
- `search-history-cases-skill`: 历史案例检索
- `assessment-reasoning-skill`: 风险/工时/人数推理

---

## Feedback

- 有问题请继续补充样例
- 建议优先先固定 S6 输出 schema
- 后续可继续增强任务组织与备件归属逻辑