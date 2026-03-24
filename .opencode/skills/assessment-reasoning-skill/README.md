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

### 核心规则表
- `risk_rules` - 风险识别规则
- `workhour_rules` - 工时估算规则
- `manpower_global_rules` - 人力配置全局规则
- `manpower_level_cover_rules` - 职级覆盖规则（基于工种代码和职级代码）

### 基础数据表（可选）
- `work_types` - 工种配置表（25 个工种）
- `job_levels` - 职级配置表（193 个职级）

### 表结构说明

**manpower_level_cover_rules**:
```sql
CREATE TABLE manpower_level_cover_rules (
    id BIGSERIAL PRIMARY KEY,
    work_type_code VARCHAR(20) NOT NULL,  -- 工种代码 (如 JN0001)
    higher_level_code VARCHAR(20) NOT NULL, -- 高职级代码 (如 ET3)
    lower_level_code VARCHAR(20) NOT NULL,  -- 低职级代码 (如 ET1)
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (work_type_code) REFERENCES work_types(work_type_code)
);
```

**work_types**:
```sql
CREATE TABLE work_types (
    work_type_code VARCHAR(20) PRIMARY KEY,  -- JN0001
    work_type_name_cn VARCHAR(100),          -- 电气工程师
    work_type_name_en VARCHAR(100)           -- Electrical Engineer
);
```

**job_levels**:
```sql
CREATE TABLE job_levels (
    id SERIAL PRIMARY KEY,
    work_type_code VARCHAR(20) NOT NULL,
    job_level_code VARCHAR(20) NOT NULL,  -- ET1, MT5, D10 等
    job_level_name VARCHAR(50),
    level_order INTEGER NOT NULL,
    FOREIGN KEY (work_type_code) REFERENCES work_types(work_type_code)
);
```

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