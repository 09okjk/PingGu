# OpenClaw / OpenCode 风格集成片段（示例）

## 1) 技能调用约定

- 技能名：`search-history-cases-skill`
- 执行命令：
  - `node {baseDir}/scripts/main.mjs --input {inputFile} --pretty`
- 入参对象（JSON）：
  - `business_type` (required)
  - `service_desc_code` (required)
  - `service_type_code` (optional)
  - `equipment_model_code` (optional)
  - `task_description` (optional)
  - `remark` (optional)
  - `top_k` (optional)

## 2) 上层 Agent 编排建议（伪配置）

```yaml
skill:
  name: search-history-cases-skill
  trigger:
    - "search similar"
    - "历史案例检索"
    - "找相似评估案例"
  input_mapping:
    business_type: requirement.business_type
    service_desc_code: requirement.service_desc_code
    service_type_code: requirement.service_type_code
    equipment_model_code: requirement.equipment_model_code
    task_description: requirement.task_description
    remark: requirement.remark
    top_k: runtime.top_k
  command: node {baseDir}/scripts/main.mjs --input {runtime.input_json_path} --pretty
  output_mapping:
    similar_cases: results
    retrieval_meta:
      top_k: top_k
      candidate_count: candidate_count
      relaxed: service_type_relaxed