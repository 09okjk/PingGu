# AssessmentReasoningSkill

本 Skill 用于统一执行：

- 风险识别 (match_risks)
- 工时估算 (estimate_workhours)
- 人数推理 (estimate_manpower)

当前版本支持两种模式：

1. **JSON 模式**：从 `references/*.json` 读取规则（默认）
2. **PostgreSQL 模式**：从 `pinggu` 数据库读取规则（可选）

---

## 快速测试

### 完整评估链路

```bash
python scripts/main.py --action reason_assessment \
  --json-input samples/sample-input.json \
  --refs-dir references \
  --pretty
```

### 单独测试子功能

```bash
# 风险识别
python scripts/main.py --action match_risks \
  --json-input samples/sample-input.json \
  --refs-dir references \
  --pretty

# 工时估算
python scripts/main.py --action estimate_workhours \
  --json-input samples/sample-input.json \
  --refs-dir references \
  --pretty

# 人力推理
python scripts/main.py --action estimate_manpower \
  --json-input samples/sample-input.json \
  --refs-dir references \
  --pretty
```

---

## Windows 兼容性

✅ 已修复 Windows 控制台 UTF-8 编码问题，可直接运行。

如遇编码问题，可设置环境变量：

**PowerShell**:
```powershell
$env:PYTHONUTF8=1
python scripts/main.py --action reason_assessment \
  --json-input samples/sample-input.json \
  --refs-dir references \
  --pretty
```

**CMD**:
```cmd
set PYTHONUTF8=1
python scripts/main.py --action reason_assessment ^
  --json-input samples/sample-input.json ^
  --refs-dir references ^
  --pretty
```

---

## 安装依赖

如果你要启用 PostgreSQL 模式，请安装：

```bash
pip install psycopg2-binary
```

---

## JSON 模式测试

```bash
python3 scripts/main.py \
  --action reason_assessment \
  --json-input samples/sample-input.json \
  --refs-dir references \
  --pretty
```

---

## PostgreSQL 模式测试

### 1. 配置 .env

```bash
cp .env.example .env
```

示例：

```env
PINGGU_USE_DB=true
PINGGU_DB_HOST=localhost
PINGGU_DB_PORT=5432
PINGGU_DB_NAME=pinggu
PINGGU_DB_USER=postgres
PINGGU_DB_PASSWORD=your_password
PINGGU_DB_SSLMODE=disable
```

### 2. 安装 psycopg2

```bash
pip install psycopg2-binary
```

### 3. 运行

```bash
python3 scripts/main.py \
  --action reason_assessment \
  --json-input samples/sample-input.json \
  --refs-dir references \
  --pretty
```

---

## PostgreSQL 表要求

当前读取以下表：

- `risk_rules`
- `workhour_rules`
- `manpower_global_rules`
- `manpower_level_cover_rules`

如数据库未配置完整，可先关闭 `PINGGU_USE_DB`，继续使用 JSON 模式。

---

## 当前限制

1. 工时仅输出单值 + 置信度
2. 人数推理仅输出理论最小人数
3. 历史案例输入需由上游先准备好
4. 数据库模式当前只负责读取 Reference，不读取历史案例

---

## 后续建议

- 接入 `evaluation_records` / `evaluation_personnel`
- 扩展数据库回流与离线统计更新
- 升级人数推理为时间窗口建模