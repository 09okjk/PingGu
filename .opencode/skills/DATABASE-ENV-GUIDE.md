# 数据库环境配置指南

> 最后更新：2026-03-25  
> 适用版本：S1/S2/S3/S5/S6

---

## 📋 环境说明

| 环境 | 用途 | 数据库 | 访问限制 |
|------|------|--------|----------|
| **开发环境 (dev)** | 本地开发调试 | `pinggu_dev` | 开发团队 |
| **测试环境 (test)** | 集成测试/验收测试 | `pinggu_test` | 测试团队 |
| **生产环境 (prod)** | 正式生产使用 | `pinggu_prod` | 仅生产服务器 |

---

## 🔧 配置方法

### 方法 1：使用 .env 文件（推荐）

#### 开发环境
```bash
cd .opencode/skills/search-history-cases-skill
cp .env.example .env
# 编辑 .env，设置 APP_ENV=dev
```

#### 测试环境
```bash
cd .opencode/skills/search-history-cases-skill
cp .env.example .env.test
# 编辑 .env.test，设置 APP_ENV=test 并填写测试库配置
```

#### 生产环境
```bash
# 在生产服务器上
cp .env.example .env.prod
# 编辑 .env.prod，设置 APP_ENV=prod 并填写生产库配置
```

---

### 方法 2：环境变量切换

#### Linux/macOS
```bash
# 开发环境
export APP_ENV=dev
npm run search

# 生产环境
export APP_ENV=prod
npm run search
```

#### Windows PowerShell
```powershell
# 开发环境
$env:APP_ENV="dev"
npm run search

# 生产环境
$env:APP_ENV="prod"
npm run search
```

---

## 🗄️ 生产数据库创建步骤

### Step 1：准备 PostgreSQL 服务器

```bash
# 确保 PostgreSQL 9.5+ 已安装
psql --version

# 创建生产数据库用户
sudo -u postgres createuser -P pinggu_app
# 输入安全密码

# 创建生产数据库
sudo -u postgres createdb -O pinggu_app pinggu_prod
```

### Step 2：启用 pg_trgm 扩展

```sql
-- 连接到生产数据库
psql -h <生产数据库 IP> -U pinggu_app -d pinggu_prod

-- 启用 pg_trgm 扩展（S1 历史检索需要）
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 验证扩展
\dx
```

### Step 3：创建数据表

```bash
# 执行建表脚本
psql -h <生产数据库 IP> -U pinggu_app -d pinggu_prod -f db/schema.sql
```

### Step 4：导入基础数据

```bash
# 导入 R2 枚举数据
psql -h <生产数据库 IP> -U pinggu_app -d pinggu_prod -f db/seed-enums.sql

# 导入初始规则数据
psql -h <生产数据库 IP> -U pinggu_app -d pinggu_prod -f db/seed-rules.sql
```

### Step 5：配置生产环境

```bash
# 在生产服务器上
cd .opencode/skills/search-history-cases-skill
cp .env.example .env.prod

# 编辑 .env.prod
vi .env.prod
```

**生产环境配置示例**：
```ini
APP_ENV=prod

# 生产数据库配置
PGHOST_PROD=10.0.0.100
PGPORT_PROD=5432
PGDATABASE_PROD=pinggu_prod
PGUSER_PROD=pinggu_app
PGPASSWORD_PROD=<安全密码>

# 当前使用配置（自动切换）
PGHOST=${PGHOST_PROD}
PGPORT=${PGPORT_PROD}
PGDATABASE=${PGDATABASE_PROD}
PGUSER=${PGUSER_PROD}
PGPASSWORD=${PGPASSWORD_PROD}
```

---

## 🔒 安全建议

### 生产环境安全清单

- [ ] 生产数据库密码使用强密码（16 位+，包含大小写/数字/特殊字符）
- [ ] 生产数据库用户仅授予最小权限（只读/写入特定表）
- [ ] 生产 `.env.prod` 文件权限设置为 `600`（仅所有者可读写）
- [ ] 生产数据库禁止外网访问（仅内网/白名单 IP）
- [ ] 启用 SSL 加密连接（`PGSSLMODE=require`）
- [ ] 定期备份生产数据库
- [ ] 开启数据库审计日志
- [ ] `.env.prod` 不提交到 Git 仓库

### 设置文件权限
```bash
# Linux/macOS
chmod 600 .env.prod
chown root:root .env.prod

# 验证权限
ls -la .env.prod
```

### 配置数据库权限
```sql
-- 创建只读用户（S1 检索使用）
CREATE USER pinggu_reader WITH PASSWORD '<password>';
GRANT SELECT ON evaluation_records TO pinggu_reader;
GRANT SELECT ON evaluation_personnel TO pinggu_reader;
GRANT SELECT ON learning_samples TO pinggu_reader;

-- 创建应用用户（S2/S5/S6 使用）
CREATE USER pinggu_app WITH PASSWORD '<password>';
GRANT SELECT ON risk_rules TO pinggu_app;
GRANT SELECT ON workhour_rules TO pinggu_app;
GRANT SELECT, INSERT, UPDATE ON learning_revision_records TO pinggu_app;
```

---

## 🚀 部署检查清单

### 上线前检查

- [ ] 生产数据库已创建并初始化
- [ ] 生产环境配置文件已准备（.env.prod）
- [ ] 数据库连接测试通过
- [ ] pg_trgm 扩展已启用
- [ ] 基础数据已导入
- [ ] 应用权限已配置
- [ ] 数据库备份策略已配置
- [ ] 监控告警已配置

### 测试验证

```bash
# 1. 测试数据库连接
psql -h <生产 IP> -U pinggu_app -d pinggu_prod -c "SELECT version();"

# 2. 测试 S1 检索
export APP_ENV=prod
npm run search

# 3. 测试 S2 推理
uv run python scripts/main.py --action reason_assessment \
  --json-input samples/sample-input.json --refs-dir references

# 4. 测试 S6 报告生成
uv run python scripts/main.py --action generate_report \
  --json-input-file samples/sample-input.json
```

---

## 📦 环境切换脚本

### switch-env.sh（Linux/macOS）
```bash
#!/bin/bash

ENV=${1:-dev}

if [[ ! "$ENV" =~ ^(dev|test|prod)$ ]]; then
  echo "错误：环境参数必须是 dev/test/prod"
  exit 1
fi

echo "切换到 $ENV 环境..."

# 备份当前配置
if [ -f .env ]; then
  cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
fi

# 复制对应环境配置
cp .env.$ENV .env

echo "✓ 已切换到 $ENV 环境"
echo "当前数据库：$(grep PGDATABASE .env | cut -d'=' -f2)"
```

**使用方法**：
```bash
# 切换到开发环境
./switch-env.sh dev

# 切换到生产环境
./switch-env.sh prod
```

---

## 🔧 故障排查

### 问题 1：无法连接数据库
```
Error: connection refused
```

**解决方法**：
```bash
# 检查网络连通性
ping <数据库 IP>

# 检查端口
telnet <数据库 IP> 5432

# 检查防火墙
sudo ufw status
```

### 问题 2：权限不足
```
Error: permission denied for table evaluation_records
```

**解决方法**：
```sql
-- 检查用户权限
\du

-- 授予权限
GRANT SELECT ON evaluation_records TO pinggu_app;
```

### 问题 3：pg_trgm 未启用
```
Error: function similarity(text, text) does not exist
```

**解决方法**：
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

---

## 📚 相关文档

- [S1 历史检索技能配置](../search-history-cases-skill/SKILL.md)
- [S2 评估推理技能配置](../assessment-reasoning-skill/SKILL.md)
- [数据库表结构设计](../../db/schema.sql)
- [生产部署手册](../../docs/production-deployment.md)

---

*文档持续更新中，最后修改：2026-03-25*
