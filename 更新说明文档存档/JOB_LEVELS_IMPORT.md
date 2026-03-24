# 工种 - 职级数据导入完成

## 导入结果

✅ **成功导入数据库表**:
- `work_types` (工种表): 25 条记录
- `job_levels` (职级表): 193 条记录

## 数据库表结构

### work_types (工种表)
```sql
CREATE TABLE work_types (
    work_type_code VARCHAR(20) PRIMARY KEY,      -- 工种编号 (如 JN0001)
    work_type_name_cn VARCHAR(100) NOT NULL,     -- 中文名 (如 电气工程师)
    work_type_name_en VARCHAR(100),              -- 英文名
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### job_levels (职级表)
```sql
CREATE TABLE job_levels (
    id SERIAL PRIMARY KEY,
    work_type_code VARCHAR(20) NOT NULL,         -- 工种编号 (外键)
    job_level_code VARCHAR(20) NOT NULL,         -- 职级代码 (如 ET1, MT3)
    job_level_name VARCHAR(50) NOT NULL,         -- 职级名称
    job_level_title VARCHAR(50),                 -- 职级职务名称
    level_order INTEGER NOT NULL,                -- 职级顺序 (数字越小级别越低)
    created_at TIMESTAMP,
    FOREIGN KEY (work_type_code) REFERENCES work_types(work_type_code),
    UNIQUE(work_type_code, job_level_code)
);
```

## 工种列表

| 工种代码 | 中文名称 | 英文名称 | 职级数 |
|---------|---------|---------|--------|
| JN0001 | 电气工程师 | 电气工程师 | 6 |
| JN0002 | 轮机工程师 | 轮机工程师 | 6 |
| JN0008 | 电工 | 电工 | 6 |
| JN0009 | 轮机钳工 | 轮机钳工 | 6 |
| JN0010 | 焊工 | 焊工 | 6 |
| JN0011 | 管工 | 管工 | 6 |
| JN0012 | 液压工程师 | 液压工程师 | 6 |
| JN0013 | 液压钳工 | 液压钳工 | 6 |
| JN0014 | 结构设计师 | Structural Engineer | 20 |
| JN0015 | 检测工程师 | 检测工程师 | 1 |
| JN0016-JN0026 | 软件/IT 类 |  various | 各 4 |
| JN0028-JN0031 | 设计师类 | various | 各 20 |

## 职级体系示例

### 电气工程师 (JN0001)
- ET1 → ET2 → ET3 → ET4 → ET5 → ET6 (共 6 级)

### 轮机工程师 (JN0002)
- MT1 → MT2 → MT3 → MT4 → MT5 → MT6 (共 6 级)

### 设计师类 (JN0014, JN0028-JN0031)
- D1 → D2 → ... → D20 (共 20 级)

### 软件/IT 类 (JN0016-JN0026)
- 初级 → 中级 → 高级 → 资深 (共 4 级)

## 查询示例

### 1. 查询某个工种的所有职级
```sql
SELECT job_level_code, job_level_name, level_order
FROM job_levels
WHERE work_type_code = 'JN0001'
ORDER BY level_order;
```

### 2. 查询所有工种及其职级数量
```sql
SELECT 
    wt.work_type_code,
    wt.work_type_name_cn,
    COUNT(jl.id) as level_count
FROM work_types wt
LEFT JOIN job_levels jl ON wt.work_type_code = jl.work_type_code
GROUP BY wt.work_type_code, wt.work_type_name_cn
ORDER BY level_count DESC;
```

### 3. 查询职级覆盖范围最广的工种
```sql
SELECT 
    work_type_code,
    work_type_name_cn,
    MIN(level_order) as min_level,
    MAX(level_order) as max_level,
    COUNT(*) as total_levels
FROM job_levels jl
JOIN work_types wt ON jl.work_type_code = wt.work_type_code
GROUP BY work_type_code, work_type_name_cn
ORDER BY total_levels DESC;
```

## 与评估 Agent 集成

### S2 (Assessment Reasoning) 使用示例
```python
# 从数据库读取工种职级配置
cur.execute("""
    SELECT wt.work_type_code, wt.work_type_name_cn,
           jl.job_level_code, jl.job_level_name, jl.level_order
    FROM job_levels jl
    JOIN work_types wt ON jl.work_type_code = wt.work_type_code
    ORDER BY wt.work_type_code, jl.level_order
""")
```

### 人力配置推理规则
- **同工种覆盖**: 高职级可覆盖低职级任务 (`higher_level_can_cover_lower_level=true`)
- **跨工种限制**: 不可跨工种替代 (`cross_work_type_substitution=false`)
- **串行复用**: 允许人员串行复用 (`allow_serial_reuse=true`)

## 文件清单

- `工种_职级 - 副本.csv` - 原始 CSV 配置表
- `import_job_levels_v2.py` - 导入脚本
- `import_job_levels.py` - 早期版本 (已废弃)
- `import_job_levels_fixed.py` - 修复版本 (已废弃)

## 下次更新

如需更新工种职级数据：
1. 替换 CSV 文件
2. 运行 `uv run python import_job_levels_v2.py`
3. 验证数据：查询 `work_types` 和 `job_levels` 表

---
**导入时间**: 2026-03-24  
**数据来源**: 工种_职级配置表  
**数据库**: PostgreSQL (192.168.124.126:5432/pinggu)
