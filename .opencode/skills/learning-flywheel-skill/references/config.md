# LearningFlywheelSkill 配置说明

## 当前版本

- 版本：1.1.0
- 默认运行模式：本地内存处理
- 默认数据库模式：关闭
- 默认本地文件存储：关闭

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `S3_ENABLE_FILE_STORAGE` | `false` | 是否将结果写入本地文件 |
| `S3_STORAGE_DIR` | `./runtime-data` | 本地存储目录 |
| `S3_ENABLE_DB` | `false` | 是否启用 PostgreSQL 写入 |
| `S3_DB_HOST` | `127.0.0.1` | PostgreSQL 主机 |
| `S3_DB_PORT` | `5432` | PostgreSQL 端口 |
| `S3_DB_NAME` | `pinggu` | 数据库名 |
| `S3_DB_USER` | `postgres` | 用户名 |
| `S3_DB_PASSWORD` | 空 | 密码 |
| `S3_DB_SSLMODE` | `disable` | SSL 模式 |

## 输出原则

- 所有输出必须包含 `success`, `data`, `error`
- 所有核心学习对象应包含 `confidence`
- 所有候选知识默认状态应为 `pending_review` 或 `candidate`

## 数据库写入说明

当前版本可写入以下表：

- `learning_revision_records`
- `learning_feedback_tags`
- `learning_samples`
- `learning_rule_candidates`
- `learning_report_preferences`

建表脚本见：`learning-tables.sql`

## 使用建议

- 本地调试先关闭数据库模式
- 联调时再开启 `S3_ENABLE_DB=true`
- 数据库异常不应通过业务逻辑 silently 忽略，建议尽早暴露