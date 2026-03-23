# ParseRequirementSkill 配置说明

## 概述

本目录包含 ParseRequirementSkill 运行所需的所有参考数据和配置。

---

## 文件清单

| 文件 | 用途 | 必需 |
|------|------|------|
| `r2-sample-enums.json` | R2 枚举映射参考数据 | ✅ 必需 |
| `aliases.json` | 术语别名扩展配置 | ❌ 可选 |
| `requirement-input.schema.json` | 输入 JSON Schema | ❌ 可选 |
| `requirement-revise-input.schema.json` | 修订输入 Schema | ❌ 可选 |
| `requirement-confirm-input.schema.json` | 确认输入 Schema | ❌ 可选 |
| `requirement-output.schema.json` | 输出 JSON Schema | ❌ 可选 |

---

## R2 Reference 配置

### r2-sample-enums.json 结构

```json
{
  "service_desc_enum": [],      // 服务描述枚举
  "service_type_enum": [],      // 服务类型枚举
  "business_type_enum": [],     // 业务归口枚举
  "equipment_name_enum": [],    // 设备名称枚举
  "unit_enum": [],              // 单位枚举
  "business_type_inference": {}, // 业务归口推断映射
  "model_patterns": [],         // 型号提取正则
  "split_keywords": []          // 服务项拆分关键词
}
```

### 枚举项格式

每个枚举项必须包含：

```json
{
  "code": "SD001",              // 唯一编码
  "name": "主机",               // 标准名称
  "aliases": ["main engine", "M/E"]  // 别名列表
}
```

### 业务归口推断规则

`business_type_inference` 定义从服务描述/设备到业务归口的映射：

```json
{
  "SD001": "BT001",  // 主机 → 轮机
  "SD005": "BT002"   // 电气系统 → 电气
}
```

---

## 环境变量

当前版本不强依赖环境变量，但预留以下配置：

| 变量名 | 用途 | 默认值 |
|--------|------|--------|
| `OPENAI_API_KEY` | 接入 LLM 时使用 | 无 |
| `MODEL_NAME` | 指定模型名称 | 无 |
| `LOG_LEVEL` | 日志级别 | `INFO` |

详见 `.env.example`。

---

## 自定义配置

### 添加新枚举

1. 在对应 enum 数组中添加新项
2. 确保 `code` 唯一
3. 尽量补充 `aliases` 提升识别率

### 扩展型号提取

在 `model_patterns` 中添加正则：

```json
{
  "model_patterns": [
    "[0-9]{1,2}[A-Z][0-9]{2}[A-Z]{1,3}(?:-[A-Z0-9\\.]+)?",
    "你的新正则模式"
  ]
}
```

### 自定义拆分规则

在 `split_keywords` 中添加服务项拆分关键词：

```json
{
  "split_keywords": [
    "also",
    "另外",
    "你的关键词"
  ]
}
```

---

## 注意事项

1. 所有 JSON 文件必须使用 UTF-8 编码
2. 枚举 `code` 必须保持唯一
3. 修改配置后建议重新运行测试
4. 生产环境请使用正式 R2 枚举，而非 sample 版本
