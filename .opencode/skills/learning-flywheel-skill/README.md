# LearningFlywheelSkill v1.1.0

S3 学习飞轮 Skill，用于从“评估初稿 → 人工修订 → 最终确认”中��取学习资产，并支持写入 PostgreSQL。

## 目录结构

```text
learning-flywheel-skill/
├── SKILL.md
├── README.md
├── _meta.json
├── .env.example
├── .gitignore
├── scripts/
│   ├── main.py
│   ├── diff_extractor.py
│   ├── feedback_classifier.py
│   ├── sample_scorer.py
│   ├── rule_miner.py
│   ├── preference_miner.py
│   ├── storage.py
│   ├── db.py
│   └── utils.py
├── references/
│   ├── config.md
│   ├── feedback-tags.md
│   ├── output.schema.json
│   └── learning-tables.sql
└── samples/
    ├── sample-input.json
    └── sample-output.json
```

## 快速测试（本地模式）

```bash
cd .opencode/skills/learning-flywheel-skill

python scripts/main.py \
  --action learn_from_revision \
  --json-input-file samples/sample-input.json \
  --pretty
```

## PostgreSQL 模式测试

### 1. 安装依赖

```bash
uv pip install psycopg2-binary python-dotenv
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

### 3. 建表

执行：

```sql
-- 见 references/learning-tables.sql
```

### 4. 启用数据库模式

在 `.env` 中设置：

```env
S3_ENABLE_DB=true
S3_DB_HOST=127.0.0.1
S3_DB_PORT=5432
S3_DB_NAME=pinggu
S3_DB_USER=postgres
S3_DB_PASSWORD=your_password
S3_DB_SSLMODE=disable
```

### 5. 运行

```bash
python scripts/main.py \
  --action learn_from_revision \
  --json-input-file samples/sample-input.json \
  --pretty
```

## 当前版本特点

- 支持 revision diff 提取
- 支持 feedback tags 归因
- 支持 learning sample 质量评分
- 支持候选规则提炼
- 支持输出偏好候选提炼
- 支持本地文件持久化（可选）
- 支持 PostgreSQL 写入（可选）
- 支持 Windows UTF-8 输出兼容
- **依赖 python-dotenv 加载环境变量**

## 常见故障

### 唯一约束冲突

重复运行测试时报错，清理测试数据：

```sql
DELETE FROM learning_report_preferences WHERE preference_id LIKE 'PF-%';
DELETE FROM learning_rule_candidates WHERE candidate_rule_id LIKE 'CR-%';
DELETE FROM learning_samples WHERE sample_id LIKE 'LF-%';
DELETE FROM learning_feedback_tags;
DELETE FROM learning_revision_records;
```

### 缺少依赖

```bash
uv pip install psycopg2-binary python-dotenv
```

## 当前实现边界

- 不自动生效候选规则
- 不做批量聚类
- 不读取历史学习资产进行反向检索
- 不替代 S1 / S2 / S6 的主职责

## 写入的数据库表

- `learning_revision_records`
- `learning_feedback_tags`
- `learning_samples`
- `learning_rule_candidates`
- `learning_report_preferences`

## 后续建议

- 增加批量规则聚类
- 增加审核状态流转接口
- 与 S1 / S2 / S6 形成正式反哺链路
- 增加管理员审核看板