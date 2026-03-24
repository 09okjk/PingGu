# AssessmentReasoningSkill References 说明

当前本地测试模式使用以下文件：

- `r3-risk-rules.sample.json`
- `r5-workhour-rules.sample.json`
- `r6-manpower-rules.sample.json`

后续生产模式建议迁移到 `pinggu` 数据库：

- `risk_rules`
- `workhour_rules`
- `manpower_global_rules`
- `manpower_level_cover_rules`

## 当前读取优先级

1. 若启用数据库模式，则优先读数据库
2. 否则读取本地 JSON sample 文件

## 说明

- 本地 sample 数据仅用于功能联调与本地验证
- 不代表正式业务规则全量数据