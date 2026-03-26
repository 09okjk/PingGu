# 技能包迁移快速参考卡

> 打印此卡片或保存在手机中，迁移时快速查阅

---

## 📦 一键打包（源机器）

```powershell
cd C:\Users\L_09o\.openclaw\workspace-assessment\skills
.\package-skills.ps1 -Action pack
```

**输出**: `skills-package.zip` (~5-10 MB)

---

## 📥 一键解压（目标机器）

```powershell
# 将 skills-package.zip 复制到目标目录
.\package-skills.ps1 -Action unpack -OutputPath skills-package.zip
```

**输出**: `skills/` 目录

---

## ✅ 一键验证

```powershell
.\package-skills.ps1 -Action verify -SourcePath skills
```

**检查项**: Python/Node.js/uv/npm + 技能文件完整性

---

## 🔧 5 分钟快速配置

### 1️⃣ 配置环境变量 (2 分钟)

```bash
cd skills

# S1
cd search-history-cases-skill && cp .env.example .env
# 编辑 .env: PGHOST, PGUSER, PGPASSWORD, PGDATABASE

# S2
cd ../assessment-reasoning-skill && cp .env.example .env
# 单机测试：PINGGU_USE_DB=false

# S3
cd ../learning-flywheel-skill && cp .env.example .env

# S4
cd ../s4-dialog-intent-detector && cp .env.example .env
# 编辑 .env: REDIS_HOST, REDIS_PORT

# S5 (无需配置)
cd ../parse-requirement-skill

# S6
cd ../generate-report-skill && cp .env.example .env

# S7
cd ../s7-review-persistence-skill && cp .env.example .env
# 编辑 .env: REDIS_HOST, REDIS_PORT
```

### 2️⃣ 安装依赖 (2 分钟)

```bash
# S1 - Node.js
cd search-history-cases-skill
npm install

# Python 技能 (S2-S7) - uv 自动管理，无需手动安装
```

### 3️⃣ 验证安装 (1 分钟)

```bash
# S5 (无依赖，最简单)
cd parse-requirement-skill
uv run python scripts/main.py --action parse --input "主机异常振动" --pretty

# S4 (对话意图检测)
cd ../s4-dialog-intent-detector
uv run python dialog_intent_detector.py "好的，确认"

# S7 (Redis 连接)
cd ../s7-review-persistence-skill
uv run python -m scripts.main status
```

---

## 🚨 常见问题速查

| 问题 | 快速解决 |
|------|---------|
| `ModuleNotFoundError` | `uv pip install -r requirements.txt` |
| `Cannot find module 'pg'` | `npm install` |
| `connection refused` (PostgreSQL) | 检查 `.env` 配置 + 服务是否运行 |
| `ConnectionError` (Redis) | `redis-cli ping` 测试连接 |
| 中文乱码 | `chcp 65001` (Windows) |
| 权限错误 | 管理员身份运行 PowerShell |

---

## 📊 依赖清单

| 技能 | 必需 | 可选 | 降级方案 |
|------|------|------|---------|
| S1 | PostgreSQL | - | 无 |
| S2 | - | PostgreSQL | 本地模式 |
| S3 | - | PostgreSQL | 本地存储 |
| S4 | - | Redis | 跳过持久化 |
| S5 | 无 | - | 完全可用 |
| S6 | - | PostgreSQL | 本地模式 |
| S7 | - | Redis | 功能不可用 |

---

## 🔐 安全提醒

- ⚠️ **不要复制 `.env` 文件**（包含密码）
- ✅ **在目标机器重新创建** `.env`
- 🔒 **使用专用数据库用户**（只读权限）
- 🛡️ **Redis 设置密码**（如暴露在网络中）

---

## 📞 完整文档

详细指南：`MIGRATION_GUIDE.md`

---

_5 分钟完成迁移，30 分钟完成验证_
