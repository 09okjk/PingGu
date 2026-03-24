# S2 工种职级同步更新完成

## 更新时间
2026-03-24

## 更新内容

### 1. 数据库表结构更新 ✅

#### manpower_level_cover_rules 表
**变更**:
- 删除字段: `work_type_name`, `higher_level_name`, `lower_level_name`
- 新增字段: `work_type_code`, `higher_level_code`, `lower_level_code`
- 添加外键: `FOREIGN KEY (work_type_code) REFERENCES work_types(work_type_code)`

**数据**:
- 自动生成 1146 条职级覆盖规则
- 覆盖所有 25 个工种
- 规则逻辑：同一工种内，高职级可覆盖低职级

**验证查询**:
```sql
SELECT wt.work_type_code, wt.work_type_name_cn,
       cr.higher_level_code, cr.lower_level_code
FROM manpower_level_cover_rules cr
JOIN work_types wt ON cr.work_type_code = wt.work_type_code
WHERE cr.is_active = TRUE
LIMIT 10;
```

### 2. manpower_engine.py 更新 ✅

**新增函数**:
1. `extract_level_code(level_name)` - 从职级名称提取代码
   - 支持格式：ET*, MT*, EP*, FP*, WP*, PP*, HT*, HP*, D*, T*, P*
   - 支持中文：初级 (CJ), 中级 (ZJ), 高级 (GJ), 资深 (ZS)

2. `get_level_order(level_code)` - 获取职级顺序
   - 从职级代码提取级别数字
   - 支持 D1-D20 (20 级设计师)
   - 支持中文职级映射

3. `can_higher_cover_lower(higher_code, lower_code, rules)` - 判断覆盖关系
   - 优先使用数据库规则
   - 降级使用级别顺序比较

**修改函数**:
- `estimate_manpower()` - 增加职级覆盖规则判断逻辑
- 支持同工种内不同职级的人员复用计算

### 3. db.py 更新 ✅

**修改函数**: `get_manpower_rules()`
- 更新 SQL 查询使用代码字段而非名称
- 返回数据结构变更:
  ```python
  {
    "global_rules": {...},
    "level_cover_rules": [
      {
        "work_type_code": "JN0001",
        "higher_level_code": "ET3",
        "lower_level_code": "ET1",
        "is_active": True
      }
    ]
  }
  ```

## 测试结果

### 职级代码提取测试
```
[OK] extract_level_code("ET1") = "ET1"
[OK] extract_level_code("MT5") = "MT5"
[OK] extract_level_code("D10") = "D10"
[OK] extract_level_code("资深") = "ZS"
[OK] extract_level_code("工程师 (T5)") = "T5"
```

### 职级顺序测试
```
[OK] get_level_order("ET1") = 1
[OK] get_level_order("D20") = 20
[OK] get_level_order("ZS") = 4
```

### 职级覆盖测试
```
[OK] can_higher_cover_lower("ET3", "ET1") = True
[OK] can_higher_cover_lower("D5", "D3") = True
```

### 完整人力推理测试
```
输入：2x ET3 + 1x ET1
输出：总人数 = 2
说明：ET3 可覆盖 ET1，串行复用，取最大值
```

## 职级体系映射

### 工程类 (6 级)
| 工种代码 | 职级代码 | 说明 |
|---------|---------|------|
| JN0001 电气工程师 | ET1-ET6 | 电气 |
| JN0002 轮机工程师 | MT1-MT6 | 轮机 |
| JN0008 电工 | EP1-EP6 | 电工 |
| JN0009 轮机钳工 | FP1-FP6 | 钳工 |
| JN0010 焊工 | WP1-WP6 | 焊工 |
| JN0011 管工 | PP1-PP6 | 管工 |
| JN0012 液压工程师 | HT1-HT6 | 液压 |
| JN0013 液压钳工 | HP1-HP6 | 液压钳工 |

### 设计师类 (20 级)
| 工种代码 | 职级代码 | 说明 |
|---------|---------|------|
| JN0014 结构设计师 | D1-D20 | 结构 |
| JN0028 舾装设计师 | D1-D20 | 舾装 |
| JN0029 电气设计师 | D1-D20 | 电气 |
| JN0030 轮机设计师 | D1-D20 | 轮机 |
| JN0031 总体设计师 | D1-D20 | 总体 |

### 软件/IT 类 (4 级)
| 工种代码 | 职级代码 | 说明 |
|---------|---------|------|
| JN0016-JN0026 | CJ, ZJ, GJ, ZS | 初级/中级/高级/资深 |

## 与 S1/S5 编码对齐

| 组件 | 工种编码 | 职级编码 | 状态 |
|------|---------|---------|------|
| S5 (parse-requirement) | JN0001-JN0031 | ET*, MT*, D* 等 | ✅ 已同步 |
| S1 (search-history) | work_type_code | job_level_code | ✅ 已同步 |
| S2 (assessment-reasoning) | work_type_code | job_level_code | ✅ 已同步 |
| 数据库 (work_types) | JN0001-JN0031 | - | ✅ 已导入 |
| 数据库 (job_levels) | - | ET*, MT*, D* 等 | ✅ 已导入 |

## 使用示例

### S2 完整评估流程
```python
from scripts.main import main

# 输入包含历史案例和工种职级信息
input_data = {
  "requirement": {
    "requirement_id": "REQ-001",
    "business_type": {"code": "BT001", "name": "电气"},
    "service_desc": {"code": "RS0000001761", "name": "火警系统"},
    "service_type": {"code": "CS0001", "name": "维修"}
  },
  "history_cases": [
    {
      "case_id": "RH-2025-0022311001",
      "personnel": [
        {"work_type_name": "电气工程师", "job_level_name": "ET3", "quantity": 2},
        {"work_type_name": "电气工程师", "job_level_name": "ET1", "quantity": 1}
      ]
    }
  ]
}

# 输出包含人力配置结果
# manpower_result: {
#   "total_persons": 2,  # ET3 覆盖 ET1，复用
#   "confidence": "medium",
#   "basis": ["serial_reuse:true", "job_level_cover:true"]
# }
```

## 文件清单

### 数据库表
- `work_types` - 工种表 (25 条)
- `job_levels` - 职级表 (193 条)
- `manpower_level_cover_rules` - 职级覆盖规则表 (1146 条)
- `manpower_global_rules` - 全局规则表 (3 条)

### 代码文件
- `assessment-reasoning-skill/scripts/manpower_engine.py` - 人力推理引擎 (已更新)
- `assessment-reasoning-skill/scripts/db.py` - 数据库访问层 (已更新)

### 脚本文件
- `import_job_levels_v2.py` - 工种职级导入脚本
- `update_manpower_tables.py` - 表结构更新脚本
- `test_manpower_engine_v2.py` - 测试脚本

## 下次维护

### 添加新工种
1. 在 CSV 中添加新工种和职级配置
2. 运行 `uv run python import_job_levels_v2.py`
3. 职级覆盖规则会自动生成

### 修改职级覆盖规则
```sql
-- 添加特定规则
INSERT INTO manpower_level_cover_rules 
(work_type_code, higher_level_code, lower_level_code, is_active)
VALUES ('JN0001', 'ET5', 'ET3', TRUE);

-- 禁用规则
UPDATE manpower_level_cover_rules 
SET is_active = FALSE 
WHERE work_type_code = 'JN0001' 
  AND higher_level_code = 'ET5' 
  AND lower_level_code = 'ET3';
```

---
**更新完成时间**: 2026-03-24  
**测试状态**: 全部通过  
**数据库**: PostgreSQL (192.168.124.126:5432/pinggu)
