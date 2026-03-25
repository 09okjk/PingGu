CREATE TABLE IF NOT EXISTS learning_revision_records (
  id BIGSERIAL PRIMARY KEY,
  task_id VARCHAR(50) NOT NULL,
  org_id VARCHAR(50),
  user_id VARCHAR(50),
  requirement_id VARCHAR(50),
  revision_diff JSONB NOT NULL,
  initial_report_json JSONB NOT NULL,
  final_report_json JSONB NOT NULL,
  versions JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_learning_revision_task_id
  ON learning_revision_records(task_id);

CREATE INDEX IF NOT EXISTS idx_learning_revision_requirement_id
  ON learning_revision_records(requirement_id);

CREATE TABLE IF NOT EXISTS learning_feedback_tags (
  id BIGSERIAL PRIMARY KEY,
  revision_record_id BIGINT NOT NULL REFERENCES learning_revision_records(id) ON DELETE CASCADE,
  tag_code VARCHAR(50) NOT NULL,
  tag_confidence DECIMAL(4,2),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_learning_feedback_tag_code
  ON learning_feedback_tags(tag_code);

CREATE TABLE IF NOT EXISTS learning_samples (
  id BIGSERIAL PRIMARY KEY,
  sample_id VARCHAR(100) UNIQUE NOT NULL,
  task_id VARCHAR(50) NOT NULL,
  scenario JSONB NOT NULL,
  revision_summary TEXT,
  quality_score DECIMAL(4,2),
  status VARCHAR(20) DEFAULT 'candidate',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_learning_samples_task_id
  ON learning_samples(task_id);

CREATE INDEX IF NOT EXISTS idx_learning_samples_status
  ON learning_samples(status);

CREATE TABLE IF NOT EXISTS learning_rule_candidates (
  id BIGSERIAL PRIMARY KEY,
  candidate_rule_id VARCHAR(100) UNIQUE NOT NULL,
  trigger JSONB NOT NULL,
  suggestion JSONB NOT NULL,
  confidence DECIMAL(4,2),
  status VARCHAR(20) DEFAULT 'pending_review',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_learning_rule_candidates_status
  ON learning_rule_candidates(status);

CREATE TABLE IF NOT EXISTS learning_report_preferences (
  id BIGSERIAL PRIMARY KEY,
  preference_id VARCHAR(100) UNIQUE NOT NULL,
  scenario VARCHAR(200) NOT NULL,
  preference_content JSONB NOT NULL,
  status VARCHAR(20) DEFAULT 'pending_review',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_learning_report_preferences_status
  ON learning_report_preferences(status);