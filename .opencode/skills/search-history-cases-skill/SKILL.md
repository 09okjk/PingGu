---
name: search-history-cases-skill
description: 根据服务需求单在历史评估库中执行渐进式检索并返回 Top-K 相似案例
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
npm install pg dotenv
cp .env.example .env
node ./scripts/main.mjs --input ./input.json
```

## Options（选项说明）

- `--input <path>`: 输入 JSON 文件路径（必填）
- `--topk <number>`: 返回数量，默认 `5`
- `--threshold <number>`: 触发放宽条件阈值，默认 `5`
- `--pretty`: 以格式化 JSON 输出（可选）

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

- 仅连接你本地/内网 PostgreSQL，不外发数据。
- 建议数据库账号使用最小权限（只读）。
- 不在日志打印明文密码、完整敏感备注。
- 输出用于内部评估，不应直接对外披露原始客户隐私文本。

## Related Skills（相关技能）

- S2: MatchRisksSkill
- S4: EstimateManpowerSkill
- S6: GenerateReportSkill

## Feedback（反馈）

- 若检索效果不足，优先调参（threshold/topk/相似度阈值）再升级实现。
- 可在第二版中增加：tsvector/zhparser、缓存层、召回质量评估脚本。