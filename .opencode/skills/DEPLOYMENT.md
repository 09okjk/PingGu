# 智能评估 Agent - 部署配置指南

> 适用版本：S1/S2/S5/S6 | 最后更新：2026-03-25

## 快速开始

### 1. 环境准备

**Python Skills (S5/S2/S6)**:
```bash
# 安装 uv（如果未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 验证安装
uv --version
```

**Node.js Skill (S1)**:
```bash
# 需要 Node.js 18+
node --version

# 安装依赖
cd .opencode/skills/search-history-cases-skill
npm install
```

---

## 数据库配置（S1/S2）

### PostgreSQL 要求

- **版本**: 9.5+（需要 `pg_trgm` 扩展）
- **扩展**: 启用相似度检索

```sql
-- 连接数据库后执行
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### 配置步骤

**S1 - SearchHistoryCasesSkill**:
```bash
cd .opencode/skills/search-history-cases-skill

# 复制配置模板
cp .env.example .env

# 编辑 .env 文件，填入实际数据库信息
# PGHOST=你的数据库地址
# PGDATABASE=你的数据库名
# PGUSER=你的用户名
# PGPASSWORD=你的密码
```

**S2 - AssessmentReasoningSkill**:
```bash
cd .opencode/skills/assessment-reasoning-skill

# 复制配置模板
cp .env.example .env

# 编辑 .env 文件
# 单机测试：PINGGU_USE_DB=false（使用本地 references）
# 多用户/生产：PINGGU_USE_DB=true（使用数据库）
```

### .env 配置示例

**S1 (.opencode/skills/search-history-cases-skill/.env)**:
```env
PGHOST=192.168.124.126
PGPORT=5432
PGDATABASE=pinggu
PGUSER=postgres
PGPASSWORD=your_password
PGSSLMODE=disable
```

**S2 (.opencode/skills/assessment-reasoning-skill/.env)**:
```env
PINGGU_USE_DB=false
PINGGU_DB_HOST=192.168.124.126
PINGGU_DB_PORT=5432
PINGGU_DB_NAME=pinggu
PINGGU_DB_USER=postgres
PINGGU_DB_PASSWORD=your_password
PINGGU_DB_SSLMODE=disable
```

> ⚠️ **重要**: `.env` 文件已加入 `.gitignore`，不会被提交到版本控制

---

## 测试验证

### S5 - 需求解析（Python）
```bash
cd .opencode/skills/parse-requirement-skill
uv run python scripts/main.py \
  --action parse \
  --json-input-file samples/sample-input.json \
  --refs references/r2-enums.json \
  --pretty
```

### S1 - 历史检索（Node.js）
```bash
cd .opencode/skills/search-history-cases-skill
npm run search
```

### S2 - 评估推理（Python）
```bash
cd .opencode/skills/assessment-reasoning-skill
uv run python scripts/main.py \
  --action reason_assessment \
  --json-input "samples/sample-input.json" \
  --refs-dir references \
  --pretty
```

### S6 - 报告生成（Python）
```bash
cd .opencode/skills/generate-report-skill
uv run python scripts/main.py \
  --action generate_report \
  --json-input-file samples/sample-input.json \
  --pretty
```

---

## 常见问题

### 1. 数据库连接失败

**错误**: `connection refused` 或 `database "pinggu" does not exist`

**解决**:
```bash
# 1. 检查 .env 配置是否正确
cat .env

# 2. 测试数据库连接
psql -h <PGHOST> -U <PGUSER> -d <PGDATABASE>

# 3. 确认 pg_trgm 扩展已启用
psql -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

### 2. 找不到参考文件

**错误**: `FILE_NOT_FOUND: references/r2-enums.json`

**解决**:
- 确保从 skill 目录执行命令
- 检查 references 目录是否存在

### 3. 中文乱码问题

**Windows 用户**:
```bash
# 设置控制台编码为 UTF-8
chcp 65001
```

所有 Python scripts 已内置 UTF-8 输出支持。

---

## 目录结构

```
.opencode/skills/
├── parse-requirement-skill/    # S5 - 需求解析
│   ├── scripts/main.py
│   ├── references/
│   └── samples/
├── search-history-cases-skill/ # S1 - 历史检索
│   ├── scripts/main.mjs
│   ├── .env.example
│   └── samples/
├── assessment-reasoning-skill/ # S2 - 评估推理
│   ├── scripts/main.py
│   ├── .env.example
│   └── samples/
└── generate-report-skill/      # S6 - 报告生成
    ├── scripts/main.py
    └── samples/
```

---

## 安全提示

1. **不要提交 `.env` 文件** - 已加入 `.gitignore`
2. **生产环境使用独立数据库** - 不要使用开发/测试数据库
3. **使用最小权限原则** - 数据库账号仅授予只读权限
4. **定期更换密码** - 特别是生产环境

---

## 技术支持

- 查看各 Skill 的 `SKILL.md` 获取详细文档
- 查看 `README.md` 获取快速入门指南
- 检查 `samples/` 目录获取示例输入
