# GenerateReportSkill 配置说明

当前 MVP 版本：

- 不直接连接数据库
- 不读取 R4 正式模板
- 直接消费上游输入：
  - requirement（S5）
  - history_cases（S1）
  - assessment_result（S2）

## 当前规则摘要

1. 一项一报
2. 结构化表格优先
3. 服务地点类型为“港口” → 判定为航修
4. 设备/备件需求拆为三栏：
   - customer_provided
   - provider_provided
   - to_be_confirmed
5. 工具/耗材不区分必需/建议

## 后续可增强点

- 接入 R4 模板
- 引入更稳定的任务骨架构建
- 引入更细的备件归属规则
- 增加工务交互修订回流