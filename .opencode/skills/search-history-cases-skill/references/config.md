# 配置说明

## 输入字段（RequirementInput）

- business_type: string（必填）
- service_desc_code: string（必填）
- service_type_code: string | null（可选）
- equipment_model_code: string | null（可选）
- task_description: string | null（可选）
- remark: string | null（可选）
- top_k: number（可选，默认5）

## 运行参数建议

- top_k: 5（默认）
- candidate_threshold: 5（默认）
- remark_similarity_threshold: 0.1（SQL中固定，可按需调整）