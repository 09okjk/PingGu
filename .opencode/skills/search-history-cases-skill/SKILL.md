---
name: search-history-cases-skill
description: 根据服务需求单在历史评估库中执行渐进式检索并返回 Top-K 相似案例
changelog: |
  ## [1.0.1] - Bug 修复版
  - 修复 PostgreSQL 参数类型推断错误（Windows/跨平台兼容）
  - 优化空值处理逻辑，使用 COALESCE() 函数
  - 添加详细使用文档和常见问题排查指南
  ## [1.0.0] - 初始版本
  - 基础检索功能
  - 支持 pg_trgm 相似度计算
  - 自动放宽检索条件
metadata:
  clawdbot:
    emoji: 🔎
    requires:
      bins: ["node"]
      env: ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"]
    os: ["linux", "darwin", "win32"]
---

# SearchHistoryCasesSkill

用于智能评估 Agent 的 S1 历史案例检索技能。  
根据业务归口、服务描述、服务类型、设备型号、任务描述等输入，返回最相似历史案例 Top-K。

## When to Use（何时使用）

✅ 适用场景：
- 需要“找相似历史评估案例”时
- 生成评估报告前，需要检索参考依据时
- 用户明确说“search similar / search history cases / 历史案例检索”时

## When NOT to Use（何时不用）

❌ 不适用场景：
- 仅做风险条目匹配（请使用 S2 MatchRisksSkill）
- 仅做人力最优人数推理（请使用 S4 EstimateManpowerSkill）
- 没有结构化输入（至少需要 business_type + service_desc_code）

## Setup（安装配置）

1. 安装依赖
2. 配置环境变量
3. 初始化数据库扩展和索引（可选）
4. 执行检索命令

```bash
cd {baseDir}
npm install
cp .env.example .env
# 编辑 .env 配置数据库连接信息
node ./scripts/main.mjs --input ./input.json
```

### 快速测试

```bash
# 使用预设输入文件
npm run search           # 默认输入
npm run search:engine    # 主机案例
npm run search:electrical # 电气案例
```

## Options（选项说明）

| 选项 | 说明 | 是否必填 | 示例 |
|------|------|----------|------|
| `--input <path>` | 输入 JSON 文件路径 | ✅ | `--input ./input.json` |
| `--topk <number>` | 返回结果数量 | ❌ (默认 5) | `--topk 10` |
| `--threshold <number>` | 触发放宽条件阈值 | ❌ (默认 5) | `--threshold 3` |
| `--pretty` | 格式化输出 JSON | ❌ | `--pretty` |

### 输入 JSON 格式

```json
{
  "business_type": "电气",
  "service_desc_code": "RS0000000001",
  "service_type_code": "CS0002",
  "equipment_model_code": null,
  "task_description": "火灾报警系统故障排除",
  "remark": "南通港登轮",
  "top_k": 5
}
```

**必填字段**:
- `business_type`: 业务归口（如 "轮机"、"电气"）
- `service_desc_code`: 服务描述编码

**可选字段**:
- `service_type_code`: 服务类型编码（为空时自动放宽检索）
- `equipment_model_code`: 设备型号编码
- `task_description`: 任务描述（用于相似度计算）
- `remark`: 备注信息（用于备注相似度计算）
- `top_k`: 返回结果数量

## Core Rules（核心规则）

1. `business_type` 与 `service_desc_code` 为必填主检索维度。  
2. 第一轮检索包含 `service_type_code` 的 “等值或NULL兼容” 条件。  
3. 候选集 `< threshold` 时自动放宽（移除 `service_type_code` 条件）重查。  
4. 排序优先级：
   - 设备型号编码精确命中优先
   - `task_description` 的 `pg_trgm similarity` 降序
   - 时间衰减（近2年优先）
   - 最新评估时间优先
5. 输入有 `remark` 时，仅对 Top-K 执行备注相似度补充，不改变排序。
6. 返回包含匹配依据 `match_reason` 和 `service_type_relaxed` 标记，便于可解释审查。

## Security & Privacy（安全说明）

- 仅连接你本地/内网 PostgreSQL，不外发数据
- 建议数据库账号使用最小权限（只读）
- 不在日志打印明文密码、完整敏感备注
- 输出用于内部评估，不应直接对外披露原始客户隐私文本

## Troubleshooting（常见问题）

### 1. 错误：`无法确定参数 $X 的数据类型`

**原因**: PostgreSQL 无法推断 NULL 参数的数据类型

**解决方法**: 
- 确保输入 JSON 中字符串字段使用空字符串 `""` 而非 `null`
- 已修复：v1.0.1+ 版本使用 `COALESCE()` 处理空值

### 2. 错误：`connection refused`

**原因**: 无法连接 PostgreSQL 数据库

**解决方法**:
```bash
# 检查 .env 配置
cat .env

# 测试数据库连接
psql -h <PGHOST> -U <PGUSER> -d <PGDATABASE>

# 确认 pg_trgm 扩展已启用
psql -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

### 3. 检索结果为空或过少

**原因**: 检索条件过于严格

**解决方法**:
- 检查 `business_type` 和 `service_desc_code` 是否正确
- 调大 `threshold` 参数（如 `--threshold 10`）
- 使用更通用的 `task_description` 描述

### 4. 相似度分数偏低

**原因**: 任务描述措辞差异较大

**解决方法**:
- 在 `task_description` 中使用更标准的行业术语
- 增加关键词（如设备品牌、故障类型）
- 调整检索策略：放宽 `service_type_code` 条件

## Related Skills（相关技能）

- S2: MatchRisksSkill
- S4: EstimateManpowerSkill
- S6: GenerateReportSkill

## Feedback（反馈）

- 若检索效果不足，优先调参（threshold/topk/相似度阈值）再升级实现。
- 可在第二版中增加：tsvector/zhparser、缓存层、召回质量评估脚本。