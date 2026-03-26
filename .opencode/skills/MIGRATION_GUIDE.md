# 技能包迁移指南

> **版本**: 1.0.0  
> **最后更新**: 2026-03-26  
> **适用技能**: S1/S2/S3/S4/S5/S6/S7 全套评估技能

---

## 📦 技能包清单

| 编号 | 技能名称 | 类型 | 依赖 | 外部服务 |
|------|---------|------|------|---------|
| **S1** | search-history-cases-skill | Node.js | npm (dotenv, pg) | PostgreSQL |
| **S2** | assessment-reasoning-skill | Python | uv (psycopg, python-dotenv) | PostgreSQL (可选) |
| **S3** | learning-flywheel-skill | Python | uv (psycopg, python-dotenv) | PostgreSQL (可选) |
| **S4** | dialog-intent-detector | Python | uv (redis) | Redis (可选) |
| **S5** | parse-requirement-skill | Python | uv (无外部依赖) | 无 |
| **S6** | generate-report-skill | Python | uv (psycopg, python-dotenv) | PostgreSQL (可选) |
| **S7** | review-persistence-skill | Python | uv (redis, python-dotenv) | Redis |

---

## ⚠️ 迁移前检查清单

### 1. 环境依赖检查

**目标机器必须安装**:
```bash
# Python 3.8+ (推荐 3.10+)
python --version

# uv 包管理器 (Python 技能)
# uv 会自动安装，无需手动安装

# Node.js 18+ (S1 技能)
node --version

# PostgreSQL 9.5+ (S1/S2/S3/S6，需 pg_trgm 扩展)
psql --version

# Redis 6+ (S4/S7，可选但推荐)
redis-server --version
```

### 2. 数据库扩展检查 (PostgreSQL)

```sql
-- 连接到目标数据库
\c pinggu

-- 检查 pg_trgm 扩展
SELECT * FROM pg_extension WHERE extname = 'pg_trgm';

-- 如未安装，执行：
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### 3. 网络连通性检查

```bash
# PostgreSQL 默认端口 5432
telnet <数据库 IP> 5432

# Redis 默认端口 6379
telnet <Redis IP> 6379
```

---

## 🚀 迁移步骤

### 步骤 1: 打包技能文件

**在源机器上执行**:
```bash
# 排除 .env 文件（包含敏感信息）
cd C:\Users\L_09o\.openclaw\workspace-assessment\skills

# 创建压缩包 (PowerShell)
Compress-Archive -Path * -DestinationPath skills-package.zip -Force

# 或使用 7-Zip
7z a skills-package.zip * -x!.env -x!*.pyc -x!__pycache__ -x!node_modules
```

**排除文件清单**:
```
.env                    # 敏感配置（目标机器需重新创建）
*.pyc                   # Python 字节码
__pycache__/            # Python 缓存
node_modules/           # Node.js 依赖（目标机器需重新安装）
*.log                   # 日志文件
```

### 步骤 2: 传输到目标机器

```bash
# 使用 scp (Linux/Mac)
scp skills-package.zip user@target-host:/path/to/workspace/

# 或使用网络共享/U 盘/云存储
```

### 步骤 3: 解压到目标机器

```bash
# Windows PowerShell
Expand-Archive -Path skills-package.zip -DestinationPath skills -Force

# Linux/Mac
unzip skills-package.zip -d skills/
```

### 步骤 4: 配置环境变量

**为每个技能创建 .env 文件**:

```bash
cd skills/

# S1 - search-history-cases-skill
cd search-history-cases-skill
cp .env.example .env
# 编辑 .env 填入实际数据库信息

# S2 - assessment-reasoning-skill
cd ../assessment-reasoning-skill
cp .env.example .env
# 编辑 .env（单机测试设置 PINGGU_USE_DB=false）

# S3 - learning-flywheel-skill
cd ../learning-flywheel-skill
cp .env.example .env

# S4 - s4-dialog-intent-detector
cd ../s4-dialog-intent-detector
cp .env.example .env
# 编辑 .env 填入 Redis 配置

# S5 - parse-requirement-skill
cd ../parse-requirement-skill
# 无需配置（无外部依赖）

# S6 - generate-report-skill
cd ../generate-report-skill
cp .env.example .env

# S7 - s7-review-persistence-skill
cd ../s7-review-persistence-skill
cp .env.example .env
# 编辑 .env 填入 Redis 配置
```

### 步骤 5: 安装依赖

```bash
# S1 - Node.js 依赖
cd search-history-cases-skill
npm install

# Python 技能 (S2/S3/S4/S5/S6/S7) - uv 自动管理
# 首次运行时 uv 会自动安装依赖，无需手动执行
```

### 步骤 6: 验证安装

```bash
# S1 - 历史检索测试
cd search-history-cases-skill
npm run search

# S2 - 评估推理测试（单机模式）
cd ../assessment-reasoning-skill
uv run python scripts/main.py --action reason_assessment \
 --json-input-file samples/sample-input.json --refs-dir references --pretty

# S4 - 对话意图检测测试
cd ../s4-dialog-intent-detector
uv run python dialog_intent_detector.py "好的，确认"

# S7 - 状态持久化测试
cd ../s7-review-persistence-skill
uv run python -m scripts.main status
```

---

## 🔧 常见问题与解决方案

### 问题 1: Python 技能依赖安装失败

**症状**:
```
ModuleNotFoundError: No module named 'redis'
或
ModuleNotFoundError: No module named 'psycopg'
```

**解决方案**:
```bash
# 手动安装依赖
cd skills/<skill-name>
uv pip install -r requirements.txt

# 或清理缓存后重试
uv cache clean
uv run python scripts/main.py --help
```

### 问题 2: Node.js 技能依赖安装失败

**症状**:
```
Error: Cannot find module 'pg'
```

**解决方案**:
```bash
cd skills/search-history-cases-skill
rm -rf node_modules package-lock.json
npm install
```

### 问题 3: PostgreSQL 连接失败

**症状**:
```
psycopg.OperationalError: connection refused
或
could not translate host name to server
```

**解决方案**:
1. 检查 PostgreSQL 服务是否运行
2. 检查 `.env` 文件中的数据库配置
3. 检查防火墙规则（端口 5432）
4. 确认 pg_trgm 扩展已安装

```sql
-- 检查扩展
SELECT * FROM pg_extension WHERE extname = 'pg_trgm';
```

### 问题 4: Redis 连接失败

**症状**:
```
redis.exceptions.ConnectionError: Error connecting to localhost:6379
```

**解决方案**:
1. 检查 Redis 服务是否运行
2. 检查 `.env` 文件中的 Redis 配置
3. 检查防火墙规则（端口 6379）

```bash
# Windows (检查服务)
Get-Service Redis

# Linux (检查服务)
systemctl status redis

# 测试连接
redis-cli ping
# 应返回：PONG
```

### 问题 5: Windows 编码问题（中文乱码）

**症状**:
```
输出显示为乱码
```

**解决方案**:
```powershell
# 设置控制台为 UTF-8
chcp 65001

# 或在 PowerShell 配置文件中添加
$OutputEncoding = [System.Text.Encoding]::UTF8
```

**已修复**: S4/S7 技能已内置 Windows 编码修复，无需手动设置。

### 问题 6: 权限问题

**症状**:
```
PermissionError: [Errno 13] Permission denied
```

**解决方案**:
```bash
# Linux/Mac - 修复文件权限
chmod -R 755 skills/
chown -R $USER:$USER skills/

# Windows - 以管理员身份运行 PowerShell
# 右键点击 PowerShell → 以管理员身份运行
```

---

## 📊 功能影响评估

### 完全兼容（无影响）✅

| 技能 | 功能 | 条件 |
|------|------|------|
| **S5** | 需求解析 | 无需外部服务，完全兼容 |
| **S2** | 评估推理 | 设置 `PINGGU_USE_DB=false` 时使用本地参考数据 |
| **S3** | 学习飞轮 | 设置 `STORE_IN_DB=false` 时使用本地存储 |
| **S6** | 报告生成 | 设置 `PINGGU_USE_DB=false` 时使用本地参考数据 |

### 部分兼容（需配置）⚠️

| 技能 | 功能 | 依赖服务 | 降级方案 |
|------|------|---------|---------|
| **S1** | 历史检索 | PostgreSQL | 无（必须配置数据库） |
| **S2** | 评估推理 (DB 模式) | PostgreSQL | 使用本地 references 目录 |
| **S3** | 学习飞轮 (DB 模式) | PostgreSQL | 使用本地存储 |
| **S4** | 对话意图检测 | Redis (可选) | 无 Redis 时跳过状态持久化 |
| **S6** | 报告生成 (DB 模式) | PostgreSQL | 使用本地参考数据 |
| **S7** | 状态持久化 | Redis | 无 Redis 时功能不可用 |

### 不兼容（需额外配置）❌

| 场景 | 问题 | 解决方案 |
|------|------|---------|
| PostgreSQL 版本 < 9.5 | pg_trgm 扩展不支持 | 升级 PostgreSQL 到 9.5+ |
| Python 版本 < 3.8 | 语法不支持 | 升级 Python 到 3.8+ |
| Node.js 版本 < 18 | ES Modules 不支持 | 升级 Node.js 到 18+ |
| 无 Redis 环境 | S4/S7 状态持久化不可用 | 安装 Redis 或禁用相关功能 |

---

## 🔐 安全注意事项

### 1. 敏感信息保护

**不要打包以下文件**:
- `.env` (包含数据库密码、Redis 密码等)
- `*.key`, `*.pem` (证书文件)
- `config.json` (可能包含 API Key)

**目标机器配置**:
```bash
# 在目标机器上创建新的 .env 文件
cp .env.example .env

# 编辑 .env，使用目标环境的凭证
# 不要直接复制源机器的 .env 文件
```

### 2. 数据库访问控制

**建议配置**:
```sql
-- 创建专用数据库用户（只读权限）
CREATE USER pinggu_readonly WITH PASSWORD 'secure_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO pinggu_readonly;

-- 限制 IP 访问
# 编辑 pg_hba.conf
host    pinggu    pinggu_readonly    192.168.1.0/24    md5
```

### 3. Redis 安全配置

**建议配置** (`redis.conf`):
```conf
# 设置密码
requirepass your_secure_password

# 绑定特定 IP
bind 127.0.0.1 192.168.1.100

# 禁用危险命令
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""
```

---

## 📝 迁移后验证清单

### 基础验证

- [ ] 所有技能文件已解压到目标目录
- [ ] 所有 `.env` 文件已创建并配置
- [ ] Node.js 依赖已安装 (`npm install`)
- [ ] Python 依赖可正常加载 (uv 自动管理)

### 功能验证

- [ ] S1: 历史检索测试通过
- [ ] S2: 评估推理测试通过（单机模式）
- [ ] S3: 学习飞轮测试通过
- [ ] S4: 对话意图检测测试通过
- [ ] S5: 需求解析测试通过
- [ ] S6: 报告生成测试通过
- [ ] S7: 状态持久化测试通过（Redis 连接）

### 集成验证

- [ ] 完整流程测试：S5 → S1 → S2 → S6 → S4 → S7
- [ ] 数据库连接正常（如使用 DB 模式）
- [ ] Redis 连接正常（如使用状态持久化）
- [ ] 中文输出正常（无乱码）

---

## 🆘 紧急回滚方案

如果迁移后出现问题，可以：

1. **保留源机器环境**: 迁移完成前不要删除源文件
2. **版本控制**: 使用 Git 管理技能代码
   ```bash
   git init
   git add .
   git commit -m "Pre-migration backup"
   ```
3. **增量迁移**: 先迁移 S5（无依赖），逐步验证其他技能
4. **并行运行**: 源机器和目标机器同时运行，对比输出结果

---

## 📞 技术支持

如遇到问题，请提供以下信息：

1. **环境信息**:
   ```bash
   python --version
   node --version
   psql --version
   redis-server --version
   ```

2. **错误日志**: 完整的错误输出

3. **配置文件**: `.env` 文件（隐藏敏感信息后）

4. **技能版本**: 
   ```bash
   # 查看技能目录结构
   ls -la skills/
   ```

---

_迁移顺利！如有问题请参考本指南或联系技术支持。_
