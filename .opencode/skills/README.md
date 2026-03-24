# Skills 使用指南

本目录包含智能评估 Agent 的核心 Skills，用于需求解析和历史案例检索。

## 快速开始

### 前置要求

| Skill | 运行环境 | 依赖服务 |
|-------|----------|----------|
| S5 ParseRequirementSkill | Python 3.8+ | 无 |
| S1 SearchHistoryCasesSkill | Node.js 18+ | PostgreSQL 9.5+ (带 pg_trgm) |

### 一键测试

**S5 测试** (复制粘贴运行):
```bash
cd .opencode/skills/parse-requirement-skill
uv run python scripts/main.py --action parse --input "The main engine shows abnormal vibration" --refs references/r2-sample-enums.json --pretty
```

**S1 测试** (复制粘贴运行):
```bash
cd .opencode/skills/search-history-cases-skill
npm run search
```

### 环境配置

#### 1. Python 环境（S5）

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -r requirements.txt
```

#### 2. Node.js 环境（S1）

```bash
cd search-history-cases-skill
npm install
cp .env.example .env
# 编辑 .env 配置数据库连接
```

#### 3. PostgreSQL 配置（S1）

```sql
-- 启用 pg_trgm 扩展
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 创建索引（可选，提升性能）
CREATE INDEX IF NOT EXISTS idx_task_description_trgm 
ON evaluation_records USING gin (task_description gin_trgm_ops);
```

---

## S5 ParseRequirementSkill - 需求解析

将自然语言邮件解析为结构化需求单。

### 快速测试

```bash
cd parse-requirement-skill

# 方式 1: 直接输入文本
uv run python scripts/main.py --action parse \
  --input "The main engine shows abnormal vibration" \
  --refs references/r2-sample-enums.json \
  --pretty

# 方式 2: 从文件读取
uv run python scripts/main.py --action parse \
  --input-file samples/sample-email.txt \
  --refs references/r2-sample-enums.json \
  --pretty

# 方式 3: JSON 输入
uv run python scripts/main.py --action parse \
  --json-input-file samples/sample-input.json \
  --refs references/r2-sample-enums.json \
  --pretty
```

### 完整工作流

```
parse → revise → confirm
```

1. **parse**: 初始解析，输出需求草稿
2. **revise**: 根据反馈修改（可选，多轮）
3. **confirm**: 确认最终需求单

### 输出示例

```json
{
  "success": true,
  "data": {
    "session_id": "sess-xxx",
    "status": "needs_confirmation",
    "requirements": [
      {
        "requirement_id": "REQ-001",
        "summary": "主机 / 检测",
        "business_type": {"code": "BT001", "name": "轮机"},
        "service_desc": {"code": "SD001", "name": "主机"},
        "service_type": {"code": "ST001", "name": "检测"},
        "confidence": "high"
      }
    ],
    "next_questions": ["确认需求是否准确？"]
  }
}
```

### 常见问题

- **字段为 null**: 参考枚举文件中没有匹配项，需添加别名
- **识别多个服务项**: 邮件包含多个动作，可在 revise 阶段合并
- **语言检测错误**: 使用 `--lang` 强制指定

📖 详细文档：[parse-requirement-skill/SKILL.md](parse-requirement-skill/SKILL.md)

---

## S1 SearchHistoryCasesSkill - 历史案例检索

根据结构化需求检索相似历史案例。

### 快速测试

```bash
cd search-history-cases-skill

# 使用预设输入
npm run search           # 默认输入
npm run search:engine    # 主机案例
npm run search:electrical # 电气案例

# 自定义输入
node scripts/main.mjs --input ./input.json --pretty
```

### 输入格式

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

### 输出示例

```json
{
  "skill": "SearchHistoryCasesSkill",
  "candidate_count": 5,
  "returned_count": 5,
  "results": [
    {
      "case_id": "RH-2025-xxx",
      "match_reason": "命中：业务归口 (电气) + 服务描述 + 服务类型",
      "task_sim_score": 0.85,
      "task_description": "...",
      "personnel": [...],
      "tools": [...]
    }
  ]
}
```

### 检索策略

1. **第一轮**: 使用全部条件（含 service_type）
2. **自动放宽**: 候选数 < threshold 时移除 service_type 重查
3. **排序**: 设备型号命中 > 任务相似度 > 时间衰减 > 最新评估

### 常见问题

- **无法连接数据库**: 检查 .env 配置和网络
- **参数类型错误**: 已修复，确保使用 v1.0.1+ 版本
- **检索结果为空**: 放宽条件或检查枚举编码

📖 详细文档：[search-history-cases-skill/SKILL.md](search-history-cases-skill/SKILL.md)

---

## 完整工作流

```
用户邮件 
  ↓
S5 ParseRequirementSkill (解析为结构化需求)
  ↓
S1 SearchHistoryCasesSkill (检索相似案例)
  ↓
S2 MatchRisksSkill (风险匹配) → 待实现
  ↓
S4 EstimateManpowerSkill (人力估算) → 待实现
  ↓
S6 GenerateReportSkill (生成报告) → 待实现
```

---

## 分发给同事

### 打包步骤

1. **复制目录**:
   ```
   .opencode/skills/parse-requirement-skill/
   .opencode/skills/search-history-cases-skill/
   ```

2. **告知同事配置要求**:
   - S5: 需要 Python 3.8+ 或 uv
   - S1: 需要 Node.js 18+ 和 PostgreSQL 连接

3. **提供测试命令**:
   ```bash
   # S5 测试
   uv run python scripts/main.py --action parse \
     --input "test" --refs references/r2-sample-enums.json --pretty
   
   # S1 测试
   npm run search
   ```

### 环境检查清单

- [ ] Python 3.8+ 可用 (`python --version`)
- [ ] Node.js 18+ 可用 (`node --version`)
- [ ] PostgreSQL 可连接 (`psql -h <host> -U <user> -d <db>`)
- [ ] pg_trgm 扩展已启用
- [ ] .env 文件已配置（S1）
- [ ] 依赖已安装（`npm install` / `uv sync`）

---

## 版本信息

| Skill | 当前版本 | 更新日期 |
|-------|----------|----------|
| ParseRequirementSkill | 2.0.0 | 2026-03 |
| SearchHistoryCasesSkill | 1.0.1 | 2026-03 |

## 更新日志

### SearchHistoryCasesSkill v1.0.1 (2026-03)
- 🐛 修复 PostgreSQL 参数类型推断错误
- 📝 添加详细使用文档和常见问题
- 🔧 优化空值处理逻辑

### ParseRequirementSkill v2.0.0 (2026-03)
- ✨ 新增 parse/revise/confirm 三阶段支持
- ✨ 支持多服务项拆分
- 📝 完善命令行选项
