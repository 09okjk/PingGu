# LearningFlywheelSkill 反馈标签说明

## 标签列表

| 标签 | 含义 |
|------|------|
| `PARSE_INCOMPLETE` | 需求解析不完整 |
| `RETRIEVAL_MISS` | 历史检索参考不足或偏差 |
| `RISK_UNDER_ESTIMATED` | 风险评估偏低 |
| `RISK_OVER_ESTIMATED` | 风险评估偏高 |
| `WORKHOUR_UNDER_ESTIMATED` | 工时估算偏低 |
| `WORKHOUR_OVER_ESTIMATED` | 工时估算偏高 |
| `MANPOWER_UNDER_ESTIMATED` | 人数估算偏低 |
| `MANPOWER_OVER_ESTIMATED` | 人数估算偏高 |
| `MISSING_DIMENSION` | 漏掉关键业务维度 |
| `MISSING_RECOMMENDATION` | 缺少建议项 |
| `WRONG_TERMINOLOGY` | 术语不专业或不符合习惯 |
| `UNCLEAR_EXPRESSION` | 表达不清晰 |
| `FORMAT_NOT_PRACTICAL` | 报告格式不利于实际审核 |
| `ORG_SPECIFIC_PREFERENCE` | 组织特定偏好 |

## 使用建议

- 单次修订可命中多个标签
- 标签用于：
  - 统计高频问题
  - 生成候选规则
  - 生成偏好候选
  - 后续管理看板展示