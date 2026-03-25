import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from db import LearningFlywheelRepository
from utils import env_bool, safe_get


def maybe_store_result_locally(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optionally persist result to local file storage for dev testing.
    """
    enabled = env_bool("S3_ENABLE_FILE_STORAGE", False)
    if not enabled:
        return {
            "stored": False,
            "storage_backend": "disabled",
        }

    storage_dir = os.getenv("S3_STORAGE_DIR", "./runtime-data")
    path = Path(storage_dir)
    path.mkdir(parents=True, exist_ok=True)

    filename = datetime.now().strftime("learning-flywheel-%Y%m%d-%H%M%S.json")
    full_path = path / filename
    full_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "stored": True,
        "storage_backend": "local_file",
        "path": str(full_path),
    }


def maybe_store_result_in_db(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optionally persist result to PostgreSQL.
    """
    enabled = env_bool("S3_ENABLE_DB", False)
    if not enabled:
        return {
            "stored": False,
            "storage_backend": "db_disabled",
        }

    repo = LearningFlywheelRepository()
    try:
        context = safe_get(data, "context", {})
        versions = safe_get(data, "versions", {})
        artifacts = safe_get(data, "artifacts_snapshot", {})
        learning_sample = safe_get(data, "learning_sample", {})
        rule_candidates = safe_get(data, "rule_candidates", [])
        preference_candidates = safe_get(data, "report_preference_candidates", [])

        requirement = safe_get(artifacts, "requirement_json", {})
        requirement_id = requirement.get("requirement_id")

        revision_record_id = repo.save_revision_record(
            context=context,
            requirement_id=requirement_id,
            revision_diff=safe_get(data, "revision_diff", []),
            initial_report_json=safe_get(artifacts, "initial_report_json", {}),
            final_report_json=safe_get(artifacts, "final_report_json", {}),
            versions=versions,
        )

        feedback_tag_count = repo.save_feedback_tags(
            revision_record_id=revision_record_id,
            feedback_tags=safe_get(data, "feedback_tags", []),
        )

        sample_id = repo.save_learning_sample(learning_sample)
        rule_count = repo.save_rule_candidates(rule_candidates)
        preference_count = repo.save_report_preferences(preference_candidates)

        repo.commit()

        return {
            "stored": True,
            "storage_backend": "postgresql",
            "revision_record_id": revision_record_id,
            "feedback_tag_count": feedback_tag_count,
            "learning_sample_row_id": sample_id,
            "rule_candidate_count": rule_count,
            "report_preference_count": preference_count,
        }
    except Exception:
        repo.rollback()
        raise
    finally:
        repo.close()