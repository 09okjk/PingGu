# S2 DB 模式测试结果

## 测试日期
2026-03-24

## 测试环境
- **OS**: Windows 11
- **Python**: 3.12 (uv 虚拟环境)
- **PostgreSQL**: 9.5+ (远程服务器 192.168.124.126)
- **数据库**: pinggu

## 测试配置

### .env 文件
```env
PINGGU_USE_DB=true
PINGGU_DB_HOST=192.168.124.126
PINGGU_DB_PORT=5432
PINGGU_DB_NAME=pinggu
PINGGU_DB_USER=postgres
PINGGU_DB_PASSWORD=wk888
PINGGU_DB_SSLMODE=disable
```

### 数据库表数据
| 表名 | 记录数 |
|------|--------|
| risk_rules | 3 条 |
| workhour_rules | 3 条 |
| manpower_global_rules | 3 条 |
| manpower_level_cover_rules | 10 条 |

## 测试结果

### ✅ 测试通过

**测试命令**:
```bash
cd .opencode/skills/assessment-reasoning-skill
uv run python scripts/main.py --action reason_assessment \
  --json-input samples/sample-input.json \
  --refs-dir references \
  --pretty
```

**输出结果**:
```json
{
  "success": true,
  "data": {
    "requirement_id": "req-001",
    "status": "ok",
    "risk_results": [
      {
        "risk_id": "RISK-001",
        "risk_name": "船厂交叉作业导致工期延误",
        "risk_level": "high",
        "confidence": "high",
        "trigger_basis": [
          "service_type:CS0017",
          "equipment_name:EN0001",
          "remark_keyword:交叉作业",
          "remark_keyword:船厂常规工作",
          "remark_keyword:备件等待",
          "history_case:RH-2025-0009611001"
        ]
      },
      {
        "risk_id": "RISK-002",
        "risk_name": "备件等待影响施工进度",
        "risk_level": "medium"
      },
      {
        "risk_id": "RISK-003",
        "risk_name": "现场安全审批或动火限制影响施工",
        "risk_level": "medium"
      }
    ],
    "workhour_results": [
      {
        "task_tag": "主机常规坞修保养工作",
        "suggested_hours": 139,
        "confidence": "medium"
      }
    ],
    "manpower_result": {
      "total_persons": 3,
      "confidence": "medium"
    }
  }
}
```

### 关键验证点

1. **✅ 数据库连接成功**
   - 成功连接到远程 PostgreSQL 服务器
   - 正确读取 .env 配置

2. **✅ 风险规则从数据库读取**
   - 读取到 3 条风险规则（RISK-001, RISK-002, RISK-003）
   - 比 JSON 文件多 1 条（RISK-003 仅在数据库中有）

3. **✅ 工时规则从数据库读取**
   - 读取到 WH-001 规则
   - 基准工时：100 小时
   - 应用风险修正后：139 小时

4. **✅ 人力规则从数据库读取**
   - 读取到全局规则和职级覆盖规则
   - 推理出总人数：3 人

5. **✅ Windows 编码兼容**
   - 中文输出正常
   - 无 GBK 编码错误

---

## 修复内容

### 1. 添加 load_env_file() 调用

**文件**: `scripts/db.py`

```python
from env_loader import get_bool_env, get_env, load_env_file
from utils import load_json_file, refs_path

# 加载 .env 文件中的环境变量
load_env_file()
```

**作用**: 自动加载 skill 根目录下的 .env 文件，无需手动设置环境变量。

---

## 使用指南

### 启用 DB 模式

1. **配置 .env 文件**:
   ```bash
   cd .opencode/skills/assessment-reasoning-skill
   cp .env.example .env
   # 编辑 .env，设置 PINGGU_USE_DB=true 和数据库连接信息
   ```

2. **安装依赖**:
   ```bash
   uv pip install psycopg2-binary
   ```

3. **运行测试**:
   ```bash
   uv run python scripts/main.py --action reason_assessment \
     --json-input samples/sample-input.json \
     --refs-dir references \
     --pretty
   ```

### 切换回 JSON 模式

只需修改 .env：
```env
PINGGU_USE_DB=false
```

---

## 对比：DB 模式 vs JSON 模式

| 维度 | JSON 模式 | DB 模式 |
|------|----------|---------|
| **数据源** | references/*.json | PostgreSQL 表 |
| **更新方式** | 手动编辑文件 | 数据库 UPDATE |
| **同步性** | 需手动同步 | 实时同步 |
| **适用场景** | 单机测试 | 多用户生产环境 |
| **依赖** | 无 | psycopg2-binary |

---

## 结论

✅ **S2 DB 模式运行正常**

- 成功从 PostgreSQL 数据库读取风险规则、工时规则、人力规则
- 推理结果正确，与 JSON 模式输出格式一致
- 支持多用户实时数据同步
- Windows 编码兼容性良好

**建议**: 
- 生产环境使用 DB 模式，确保数据同步
- 开发测试使用 JSON 模式，快速迭代
