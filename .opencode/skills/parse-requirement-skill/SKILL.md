---
name: parse-requirement-skill
description: 将自然语言邮件解析为一个或多个标准化服务需求项，输出结构化字段、证据片段、歧义项与置信度，供后续历史检索与评估流程使用。
metadata:
  clawdbot:
    emoji: 🧩
    requires:
      bins: ["python3"]
      env: []
    os: ["linux", "darwin", "win32"]
---

# ParseRequirementSkill

将用户输入的原始自然语言邮件解析为 1~N 个结构化服务需求项（RequirementItem），支持：
- 多服务项拆分
- 服务描述/服务类型/业务归口/设备信息抽取
- 枚举映射
- 证据保留
- 歧义标注
- 统一 JSON 输出

---

## When to Use

✅ 适用于以下场景：

- 用户输入是自然语言邮件或描述，而不是标准表单
- 一段原始需求中可能包含多个服务项
- 需要在进入历史案例检索前，先完成结构化解析
- 需要把自然语言表达映射到标准枚举体系
- 需要输出可供下游 Skill 直接消费的 JSON

典型示例：
- “主机有异常振动，锅炉有泄漏，想咨询检查和维修方案”
- “Need inspection for main engine and possible repair for boiler”
- “客户邮件中提到了多个设备问题，需要拆成多个需求单”

---

## When NOT to Use

❌ 不适用于以下场景：

- 输入已经是标准化、字段齐全的需求单
- 仅需对已结构化字段执行历史检索
- 只做单纯翻译，不做需求拆分和字段映射
- 只做风险匹配或工时估算

---

## Setup

1. 准备目录结构：
   - `scripts/main.py`
   - `references/r2-sample-enums.json`

2. 可选：复制环境变量模板
```bash
cp .env.example .env
```

3. 直接运行脚本测试：
```bash
python3 {baseDir}/scripts/main.py \
  --input "The main engine shows abnormal vibration and may need inspection. The boiler has leakage and may require repair." \
  --refs "{baseDir}/references/r2-sample-enums.json"
```

4. 或从文件读取输入：
```bash
python3 {baseDir}/scripts/main.py \
  --input-file "{baseDir}/sample-email.txt" \
  --refs "{baseDir}/references/r2-sample-enums.json"
```

---

## Options

- `--input <text>`: 直接传入原始邮件文本
- `--input-file <path>`: 从文件读取邮件文本
- `--refs <path>`: R2 枚举/别名参考文件路径
- `--pretty`: 以格式化 JSON 输出
- `--strict`: 开启严格模式；未命中关键枚举时提高待确认标记
- `--lang <code>`: 手动指定输入语言（如 `en` / `zh`），默认自动粗识别

---

## Input Contract

输入为自然语言邮件文本，附件字段预留但当前不启用。

脚本标准输入逻辑：
- 优先使用 `--input`
- 其次使用 `--input-file`
- 若都未提供，则从 STDIN 读取

参考枚举文件必须是 JSON，包含至少：
- 服务描述枚举
- 服务类型枚举
- 业务归口枚举
- 设备名称枚举
- 单位枚举
- 别名映射

---

## Output Contract

脚本输出统一 JSON，结构如下：

```json
{
  "success": true,
  "data": {
    "input_type": "email_text",
    "language": "en",
    "requirement_count": 2,
    "requirements": [],
    "global_ambiguities": [],
    "parsing_notes": []
  },
  "error": null
}
```

要求：
- stdout 仅输出 JSON
- stderr 可输出调试日志
- 失败时返回：
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "PARSE_ERROR",
    "message": "..."
  }
}
```

---

## Core Rules

1. **不得臆造**
   - 邮件中没有明确或高概率推断的信息，不得虚构。
   - 无法判断时输出 `null` 或候选歧义项。

2. **必须支持多服务项拆分**
   - 一封邮件可能对应多个需求单。
   - 若识别到多个设备对象或多个独立服务诉求，应拆分为多个 RequirementItem。

3. **必须保留原文证据**
   - 每个 RequirementItem 都应保留 `original_evidence`。

4. **规则优先**
   - 优先通过别名词典、关键词规则、枚举映射完成解析。
   - 允许后续接入 LLM，但不依赖单独 Skill 模型配置。

5. **允许字段为空**
   - `service_type`、`equipment_model`、`business_type` 等都允许为 `null`。

6. **兼容后续扩展**
   - 预留 `attachments` 字段，但当前不处理附件内容。
   - 预留 LLM 接口适配位置。

---

## Security & Privacy

- 默认仅处理本地传入文本，不主动联网。
- 不上传附件、不外发原文。
- 若后续接入 LLM，请由上层 Agent 统一管理模型调用与数据边界。
- 建议在生产环境中对输入文本做脱敏审计。

---

## Related Skills

- `SearchHistoryCasesSkill`：消费结构化需求项进行相似案例检索
- `MatchRisksSkill`：基于解析结果进行风险匹配
- `GenerateReportSkill`：汇总多 Skill 输出生成评估报告

---

## Feedback

- 首轮测试建议优先验证“多服务项拆分是否准确”
- 第二轮验证“服务描述 / 服务类型 枚举映射是否稳定”
- 获取正式 R2 枚举后，优先更新 `references/r2-sample-enums.json`