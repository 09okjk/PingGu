# AGENTS.md - 智能评估 Agent 项目指南

## 项目概述

本项目是一个智能评估 Agent，用于将船舶服务需求自动转换为结构化评估报告。核心功能包括需求解析、历史案例检索、风险匹配、人力估算和报告生成。

## 技术栈

- **Python 3.8+**: 需求解析脚本
- **Node.js 18+**: 历史案例检索脚本 (ESM)
- **PostgreSQL**: 历史评估记录数据库 (需 pg_trgm 扩展)
- **OpenCode/OpenClaw**: Agent 框架

## 目录结构

```
PingGu/
├── .opencode/skills/          # OpenCode Skills 目录
│   ├── parse-requirement-skill/    # S5: 需求解析 Skill
│   └── search-history-cases-skill/ # S1: 历史案例检索 Skill
├── AGENTS.md                  # 本文件
└── 设计方案及规范/             # 设计文档和规范
    ├── OpenClawSkill 创建规范.md
    ├── S5 - ParseRequirementSkill 详细设计.md
    ├── S1 - SearchHistoryCasesSkill 详细设计.md
    └── 智能评估 Agent Skill 规划方案.md
```

## 构建与运行命令

### Python (需求解析)

```bash
# 运行单个需求解析测试
python3 .opencode/skills/parse-requirement-skill/scripts/main.py \
  --input "The main engine shows abnormal vibration" \
  --refs .opencode/skills/parse-requirement-skill/references/r2-sample-enums.json \
  --pretty

# 从文件读取输入
python3 .opencode/skills/parse-requirement-skill/scripts/main.py \
  --input-file .opencode/skills/parse-requirement-skill/samples/sample-email.txt \
  --refs .opencode/skills/parse-requirement-skill/references/r2-sample-enums.json \
  --pretty
```

### Node.js (历史案例检索)

```bash
# 安装依赖
cd .opencode/skills/search-history-cases-skill
npm install

# 配置环境变量
cp .env.example .env
# 编辑 .env 填写 PostgreSQL 连接信息

# 运行检索测试
npm run search
npm run search:engine    # 主机案例
npm run search:electrical # 电气案例
```

### 数据库初始化

```sql
-- 启用 pg_trgm 扩展 (PostgreSQL)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 创建索引 (可选，提升相似度搜索性能)
CREATE INDEX IF NOT EXISTS idx_task_description_trgm 
ON evaluation_records USING gin (task_description gin_trgm_ops);
```

## 代码风格指南

### Python 规范

- **导入顺序**: 标准库 → 第三方库 → 本地模块
- **类型注解**: 所有函数必须标注参数和返回类型
- **命名约定**: 
  - 函数/变量: `snake_case`
  - 类: `PascalCase`
  - 常量: `UPPER_CASE`
- **错误处理**: 使用 `try/except` 捕获具体异常，返回统一错误结构
- **文档字符串**: 公共函数必须包含 docstring

```python
def ok(data: Dict[str, Any]) -> Dict[str, Any]:
    """返回成功响应结构"""
    return {"success": True, "data": data, "error": None}
```

### Node.js 规范

- **模块系统**: 使用 ES Modules (`import`/`export`)
- **文件扩展名**: `.mjs` 明确表示 ESM
- **异步处理**: 优先使用 `async/await`
- **错误处理**: 抛出 Error 对象，上层统一捕获

```javascript
async function queryCandidates(req, withServiceType) {
  if (!req.business_type) {
    throw new Error("business_type is required");
  }
  // ...
}
```

### JSON 数据规范

- **缩进**: 2 空格
- **编码**: UTF-8
- **键名**: `snake_case`
- **空值**: 使用 `null` 而非省略字段

### 错误处理模式

**Python**:
```python
try:
    result = parse_email_to_requirements(email_text, refs)
    dump(ok(result), pretty=True)
except FileNotFoundError as e:
    dump(fail("FILE_NOT_FOUND", str(e)), pretty=True)
except json.JSONDecodeError as e:
    dump(fail("INVALID_JSON", f"Failed to parse JSON: {e}"), pretty=True)
```

**Node.js**:
```javascript
try {
  const result = await searchHistoryCases(input);
  console.log(JSON.stringify(result, null, 2));
} catch (error) {
  console.error(JSON.stringify({ success: false, error: error.message }));
}
```

## Skill 开发规范

参考 `设计方案及规范/OpenClawSkill 创建规范.md`，核心要求：

1. **SKILL.md 必需**: 包含 frontmatter 和完整文档
2. **name 格式**: 小写连字符 (如 `parse-requirement-skill`)
3. **目录结构**: `scripts/` 放代码，`references/` 放配置
4. **环境变量**: 提供 `.env.example` 模板

## 测试指南

### 单元测试 (Python)

```bash
# 暂无正式测试框架，使用手动测试
python3 -c "
from scripts.main import parse_email_to_requirements
import json
refs = json.load(open('references/r2-sample-enums.json'))
result = parse_email_to_requirements('test input', refs)
print(json.dumps(result, indent=2))
"
```

### 集成测试 (Node.js)

```bash
# 使用预设输入文件测试
node scripts/main.mjs --input input.json --pretty
node scripts/main.mjs --input input.engine.json --pretty
```

## 核心工作流

```
用户原始邮件
    ↓
S5 ParseRequirementSkill (解析为结构化需求)
    ↓
S1 SearchHistoryCasesSkill (检索相似案例)
    ↓
S2 MatchRisksSkill (风险匹配)
    ↓
S4 EstimateManpowerSkill (人力估算)
    ↓
S6 GenerateReportSkill (生成报告)
```

## 相关文档

- `设计方案及规范/智能评估 Agent Skill 规划方案.md` - 整体架构设计
- `设计方案及规范/S5 - ParseRequirementSkill 详细设计.md` - 需求解析 Skill 详解
- `设计方案及规范/S1 - SearchHistoryCasesSkill 详细设计.md` - 历史案例检索 Skill 详解
- `.opencode/skills/*/SKILL.md` - 各 Skill 使用文档

## 注意事项

1. **数据库连接**: 仅支持 PostgreSQL 9.5+ (需 pg_trgm)
2. **语言支持**: 处理中文/英文/日文/韩文多语言输入
3. **枚举映射**: 所有字段映射依赖 R2 Reference 文件
4. **置信度标注**: 输出必须包含置信度和待确认标记
