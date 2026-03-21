CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_er_business_type    ON evaluation_records(business_type);
CREATE INDEX IF NOT EXISTS idx_er_service_desc     ON evaluation_records(service_desc_code);
CREATE INDEX IF NOT EXISTS idx_er_service_type     ON evaluation_records(service_type_code);
CREATE INDEX IF NOT EXISTS idx_er_equipment_model  ON evaluation_records(equipment_model_code);
CREATE INDEX IF NOT EXISTS idx_er_evaluated_at     ON evaluation_records(evaluated_at DESC);

CREATE INDEX IF NOT EXISTS idx_er_core_search
  ON evaluation_records(business_type, service_desc_code, service_type_code);

CREATE INDEX IF NOT EXISTS idx_er_task_trgm
  ON evaluation_records USING GIN(task_description gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_er_device_trgm
  ON evaluation_records USING GIN(device_content gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_ep_record_id
  ON evaluation_personnel(record_id);

CREATE INDEX IF NOT EXISTS idx_ep_work_type
  ON evaluation_personnel(work_type_code);

CREATE INDEX IF NOT EXISTS idx_ep_job_level
  ON evaluation_personnel(job_level_code);

CREATE INDEX IF NOT EXISTS idx_ep_job_resp_trgm
  ON evaluation_personnel USING GIN(detailed_job_responsibilities gin_trgm_ops);