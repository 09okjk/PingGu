# 数据库优先架构说明

**更新时间**: 2026-03-24  
**架构模式**: 数据库优先 + JSON 降级

---

## 📊 架构演进

### V1.0 - JSON 文件模式 (已废弃)
```
┌─────────────┐
│ JSON 文件    │ → 读取规则 → 评估引擎
│ (本地磁盘)  │
└─────────────┘
```
**问题**:
- ❌ 数据更新需要修改文件
- ❌ 多用户数据不一致
- ❌ 无法追溯历史变更
- ❌ 难以统计分析

### V2.0 - 双模式并存 (当前)
```
┌─────────────┐     ┌─────────────┐
│ 数据库      │     │ JSON 文件    │
│ (生产)      │ OR  │ (降级)      │
└─────────────┘     └─────────────┘
         ↓               ↓
      └─────────────────┘
              ↓
        评估引擎
```
**问题**:
- ⚠️ JSON 文件可能过期
- ⚠️ 维护两套数据源

### V3.0 - 数据库优先 (推荐) ✅
```
┌─────────────┐
│ 数据库      │ → 读取规则 → 评估引擎
│ (生产环境)  │
└─────────────┘
       ↓
┌─────────────┐
│ JSON 文件    │ (仅降级备份)
│ (离线调试)  │
└─────────────┘
```
**优点**:
- ✅ 单一数据源（数据库）
- ✅ 实时同步更新
- ✅ 完整的版本历史
- ✅ 支持统计分析
- ✅ 离线可用（降级）

---

## 🎯 数据源优先级

### 生产环境（推荐）

```bash
# .env 配置
PINGGU_USE_DB=true
PINGGU_DB_HOST=192.168.124.126
PINGGU_DB_NAME=pinggu
```

**数据流向**:
```
PostgreSQL (pinggu)
  ├── risk_rules (22 条)
  ├── workhour_rules (4 条+)
  ├── manpower_global_rules (3 条)
  ├── manpower_level_cover_rules (1146 条)
  ├── work_types (25 条)
  └── job_levels (193 条)
       ↓
  AssessmentReasoningSkill
       ↓
  评估报告
```

### 离线调试模式

```bash
# .env 配置
PINGGU_USE_DB=false  # 临时降级
```

**警告提示**:
```
UserWarning: ⚠️  当前使用本地 JSON 模式（离线调试）。
             生产环境应设置 PINGGU_USE_DB=true 从数据库读取规则。
```

---

## 📁 文件角色重新定义

### 生产数据源（数据库）

| 表名 | 用途 | 数据量 | 更新频率 |
|------|------|--------|----------|
| `risk_rules` | 风险识别规则 | 22 条 | 按需更新 |
| `workhour_rules` | 工时估算规则 | 4+ 条 | 持续积累 |
| `manpower_global_rules` | 人力全局规则 | 3 条 | 稳定 |
| `manpower_level_cover_rules` | 职级覆盖规则 | 1146 条 | 自动生成 |
| `work_types` | 工种配置 | 25 条 | 稳定 |
| `job_levels` | 职级配置 | 193 条 | 稳定 |

### 降级备份（JSON 文件）

| 文件 | 作用 | 状态 |
|------|------|------|
| `r3-risk-rules.json` | 离线降级备份 | ⚠️ 可能过期 |
| `r5-workhour-rules.json` | 离线降级备份 | ⚠️ 可能过期 |
| `r6-manpower-rules.json` | 离线降级备份 | ⚠️ 可能过期 |
| `sample-history-cases.json` | 测试用例 | ✅ 保留 |

**重要**: JSON 文件仅用于离线调试，生产环境不应依赖！

---

## 🔧 配置管理

### 环境变量优先级

```
1. 系统环境变量 (最高优先级)
   ↓
2. .env 文件
   ↓
3. 代码默认值 (PINGGU_USE_DB=true)
```

### 推荐配置

**生产环境** (`/etc/pinggu/.env`):
```bash
PINGGU_USE_DB=true
PINGGU_DB_HOST=192.168.124.126
PINGGU_DB_PORT=5432
PINGGU_DB_NAME=pinggu
PINGGU_DB_USER=app_user
PINGGU_DB_PASSWORD=<secure_password>
PINGGU_DB_SSLMODE=require
```

**开发环境** (`.opencode/skills/assessment-reasoning-skill/.env`):
```bash
PINGGU_USE_DB=true
PINGGU_DB_HOST=192.168.124.126
PINGGU_DB_NAME=pinggu
PINGGU_DB_USER=postgres
PINGGU_DB_PASSWORD=wk888
```

**离线调试** (临时):
```bash
export PINGGU_USE_DB=false
python scripts/main.py --action reason_assessment ...
```

---

## 📊 数据同步策略

### 数据库更新流程

```mermaid
graph LR
    A[业务规则变更] --> B[更新数据库]
    B --> C[验证测试]
    C --> D[部署生效]
    D --> E[JSON 备份可选]
```

### JSON 备份更新（可选）

```bash
# 导出数据库规则为 JSON（用于备份）
python scripts/export_rules_to_json.py \
  --output references/r3-risk-rules.json \
  --table risk_rules
```

---

## 🚀 迁移指南

### 从 JSON 模式迁移到数据库模式

**步骤 1: 检查数据库表**
```bash
cd .opencode/skills/search-history-cases-skill
node -e "
const pg = require('pg');
const pool = new pg.Pool({...});
(async () => {
  const tables = ['risk_rules', 'workhour_rules', 'manpower_level_cover_rules'];
  for (const t of tables) {
    const r = await pool.query(\`SELECT COUNT(*) FROM \${t}\`);
    console.log(t, ':', r.rows[0].count, '条');
  }
})();
"
```

**步骤 2: 更新 .env**
```bash
# 编辑 .env
vi .opencode/skills/assessment-reasoning-skill/.env

# 修改为
PINGGU_USE_DB=true
```

**步骤 3: 验证**
```bash
uv run python .opencode/skills/assessment-reasoning-skill/scripts/main.py \
  --action reason_assessment \
  --json-input samples/sample-history-cases.json \
  --refs-dir references \
  --pretty

# 检查输出是否包含数据库数据
```

---

## ⚠️ 常见问题

### Q1: 数据库连接失败怎么办？

**A**: 自动降级到 JSON 模式（会显示警告）

```python
try:
    conn = psycopg2.connect(...)
except psycopg2.OperationalError:
    warnings.warn("数据库连接失败，降级到本地 JSON 模式")
    self.use_db = False
```

### Q2: 如何确保 JSON 文件与数据库同步？

**A**: 不建议同步！JSON 仅用于离线调试。生产环境应始终使用数据库。

### Q3: 可以在没有数据库的环境部署吗？

**A**: 可以，但需要：
1. 设置 `PINGGU_USE_DB=false`
2. 确保 JSON 文件是最新的
3. 接受警告提示

### Q4: 数据库规则如何更新？

**A**: 三种方式：
1. **手动 SQL**: 直接执行 UPDATE/INSERT
2. **管理工具**: pgAdmin, DBeaver 等
3. **API 接口**: (建议开发) 规则管理后台

---

## 📈 最佳实践

### ✅ 推荐做法

1. **生产环境始终使用数据库模式**
   ```bash
   PINGGU_USE_DB=true
   ```

2. **规则变更通过数据库操作**
   ```sql
   UPDATE risk_rules 
   SET is_active = FALSE 
   WHERE risk_id = 'RISK-001';
   
   INSERT INTO risk_rules (...) VALUES (...);
   ```

3. **定期备份数据库**
   ```bash
   pg_dump -h 192.168.124.126 -U postgres pinggu > backup.sql
   ```

4. **JSON 文件仅用于版本控制**
   - 提交到 Git 作为参考
   - 不依赖 JSON 文件运行生产

### ❌ 避免做法

1. **手动修改 JSON 文件而不更新数据库**
2. **在生产环境使用 `PINGGU_USE_DB=false`**
3. **依赖过期的 JSON 备份文件**
4. **不同环境使用不同的数据源**

---

## 🎯 下一步

### 短期 (1-2 周)

- [ ] 开发规则管理后台（可选）
- [ ] 实现数据库变更审计日志
- [ ] 添加规则版本管理

### 中期 (1 个月)

- [ ] 移除 JSON 降级模式（完全依赖数据库）
- [ ] 实现规则热更新（无需重启）
- [ ] 添加规则效果统计

### 长期 (3 个月+)

- [ ] 规则机器学习优化
- [ ] 自动规则发现
- [ ] A/B 测试框架

---

**架构决策记录**: 2026-03-24  
**决策者**: 技术团队  
**审核状态**: ✅ 已实施  
**下次评审**: 2026-06-24
