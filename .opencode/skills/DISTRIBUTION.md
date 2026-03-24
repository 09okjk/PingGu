# Skills 分发清单

## 文件清单

发送给同事时，请包含以下文件和目录：

```
.opencode/skills/
├── README.md                          # 总使用指南
├── DISTRIBUTION.md                    # 本文件
├── parse-requirement-skill/           # S5 需求解析 Skill
│   ├── SKILL.md                       # Skill 说明文档
│   ├── scripts/
│   │   └── main.py                    # 主程序
│   ├── references/
│   │   ├── r2-sample-enums.json       # 枚举参考文件
│   │   ├── aliases.json               # 别名配置
│   │   └── *.schema.json              # JSON Schema
│   └── samples/                       # 示例文件
│       ├── sample-input.json
│       ├── sample-email.txt
│       ├── sample-revise-input.json
│       └── sample-confirm-input.json
└── search-history-cases-skill/        # S1 历史案例检索 Skill
    ├── SKILL.md                       # Skill 说明文档
    ├── scripts/
    │   ├── main.mjs                   # 主程序
    │   └── db.mjs                     # 数据库连接
    ├── input.json                     # 示例输入
    ├── input.engine.json              # 主机示例
    ├── input.electrical.json          # 电气示例
    ├── package.json                   # Node.js 依赖
    ├── .env.example                   # 环境变量模板
    └── .env                           # 环境变量配置 (需手动创建)
```

## 接收后配置步骤

### 1. 检查环境

```bash
# 检查 Python
python --version    # 需要 3.8+

# 检查 Node.js
node --version      # 需要 18+

# 检查 PostgreSQL (S1 需要)
psql --version      # 需要 9.5+
```

### 2. 安装依赖

**S5 (Python)**:
```bash
cd .opencode/skills/parse-requirement-skill
# 使用 uv (推荐)
uv sync
# 或使用 pip
pip install -r requirements.txt  # 如无 requirements.txt 则无需安装额外依赖
```

**S1 (Node.js)**:
```bash
cd .opencode/skills/search-history-cases-skill
npm install
```

### 3. 配置数据库 (仅 S1)

```bash
cd .opencode/skills/search-history-cases-skill
cp .env.example .env
```

编辑 `.env` 文件：
```ini
PGHOST=你的数据库主机
PGPORT=5432
PGDATABASE=pinggu
PGUSER=postgres
PGPASSWORD=你的密码
```

### 4. 启用 PostgreSQL 扩展 (仅首次)

```sql
-- 连接数据库后执行
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 可选：创建索引提升性能
CREATE INDEX IF NOT EXISTS idx_task_description_trgm 
ON evaluation_records USING gin (task_description gin_trgm_ops);
```

### 5. 运行测试

**S5 测试**:
```bash
cd .opencode/skills/parse-requirement-skill
uv run python scripts/main.py --action parse \
  --input "The main engine shows abnormal vibration" \
  --refs references/r2-sample-enums.json --pretty
```

期望输出：
```json
{
  "success": true,
  "data": {
    "session_id": "sess-xxx",
    "requirements": [...],
    ...
  }
}
```

**S1 测试**:
```bash
cd .opencode/skills/search-history-cases-skill
npm run search
```

期望输出：
```json
{
  "skill": "SearchHistoryCasesSkill",
  "candidate_count": 5,
  "results": [...]
}
```

## 常见问题快速排查

### S5 问题

| 问题 | 解决方法 |
|------|----------|
| `FILE_NOT_FOUND` | 使用绝对路径或从 skill 目录运行 |
| `INVALID_JSON` | 检查 JSON 格式，确保 UTF-8 编码 |
| 字段为 null | 在 `references/r2-sample-enums.json` 中添加别名 |

### S1 问题

| 问题 | 解决方法 |
|------|----------|
| `connection refused` | 检查 `.env` 配置和数据库连接 |
| `无法确定参数类型` | 已修复，确保使用最新版本脚本 |
| 检索结果为空 | 检查 `business_type` 和 `service_desc_code` |
| `pg_trgm` 错误 | 执行 `CREATE EXTENSION pg_trgm;` |

## 版本兼容性

| Skill | 最低版本 | 推荐版本 | 备注 |
|-------|----------|----------|------|
| Python | 3.8 | 3.10+ | 需要 f-string 和类型注解支持 |
| Node.js | 18 | 20+ | 需要 ES Modules 支持 |
| PostgreSQL | 9.5 | 12+ | 需要 pg_trgm 扩展 |

## 已知限制

1. **S5 ParseRequirementSkill**:
   - 暂不支持附件内容解析
   - 依赖枚举参考文件进行匹配
   - 多语言混合邮件可能识别不准确

2. **S1 SearchHistoryCasesSkill**:
   - 仅支持 PostgreSQL 数据库
   - 需要数据库表 `evaluation_records` 和 `evaluation_personnel`
   - 相似度计算依赖 pg_trgm 扩展

## 获取帮助

- 查看各 Skill 的 `SKILL.md` 详细文档
- 查看 `README.md` 总使用指南
- 检查 `samples/` 目录中的示例文件

## 更新记录

### 2026-03
- S5 v2.0.0: 新增 revise/confirm 阶段
- S1 v1.0.1: 修复 PostgreSQL 参数类型问题
- 新增 DISTRIBUTION.md 分发文档
- 新增 Troubleshooting 章节

---

**分发日期**: 2026-03-23  
**维护者**: 智能评估 Agent 团队
