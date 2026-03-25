import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import Json

# 加载 .env 文件
load_dotenv(Path(__file__).parent.parent / ".env")


class LearningFlywheelRepository:
    """Repository for PostgreSQL persistence of learning flywheel outputs."""

    def __init__(self) -> None:
        self.conn = psycopg2.connect(
            host=os.getenv("S3_DB_HOST", "127.0.0.1"),
            port=int(os.getenv("S3_DB_PORT", "5432")),
            dbname=os.getenv("S3_DB_NAME", "pinggu"),
            user=os.getenv("S3_DB_USER", "postgres"),
            password=os.getenv("S3_DB_PASSWORD", ""),
            sslmode=os.getenv("S3_DB_SSLMODE", "disable"),
        )
        self.conn.autocommit = False

    def close(self) -> None:
        """Close DB connection."""
        if self.conn:
            self.conn.close()

    def save_revision_record(
        self,
        context: Dict[str, Any],
        requirement_id: Optional[str],
        revision_diff: List[Dict[str, Any]],
        initial_report_json: Dict[str, Any],
        final_report_json: Dict[str, Any],
        versions: Dict[str, Any],
    ) -> int:
        """Insert revision record and return DB id."""
        sql = """
        INSERT INTO learning_revision_records (
            task_id,
            org_id,
            user_id,
            requirement_id,
            revision_diff,
            initial_report_json,
            final_report_json,
            versions
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        with self.conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    context.get("task_id"),
                    context.get("org_id"),
                    context.get("user_id"),
                    requirement_id,
                    Json(revision_diff),
                    Json(initial_report_json),
                    Json(final_report_json),
                    Json(versions),
                ),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError("Failed to insert learning_revision_records")
            return int(row[0])

    def save_feedback_tags(
        self,
        revision_record_id: int,
        feedback_tags: List[Dict[str, Any]],
    ) -> int:
        """Insert feedback tags."""
        sql = """
        INSERT INTO learning_feedback_tags (
            revision_record_id,
            tag_code,
            tag_confidence
        ) VALUES (%s, %s, %s)
        """
        count = 0
        with self.conn.cursor() as cur:
            for item in feedback_tags:
                cur.execute(
                    sql,
                    (
                        revision_record_id,
                        item.get("tag_code"),
                        item.get("tag_confidence"),
                    ),
                )
                count += 1
        return count

    def save_learning_sample(
        self,
        learning_sample: Dict[str, Any],
    ) -> Optional[int]:
        """Insert learning sample when store=true."""
        if not learning_sample.get("store"):
            return None

        scenario = learning_sample.get("scenario") or {}
        sample_id = f"LF-{learning_sample.get('source_task_id') or 'UNKNOWN'}"

        sql = """
        INSERT INTO learning_samples (
            sample_id,
            task_id,
            scenario,
            revision_summary,
            quality_score,
            status
        ) VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        with self.conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    sample_id,
                    learning_sample.get("source_task_id"),
                    Json(scenario),
                    "；".join(learning_sample.get("reason_summary") or []),
                    learning_sample.get("quality_score"),
                    learning_sample.get("status", "candidate"),
                ),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError("Failed to insert learning_samples")
            return int(row[0])

    def save_rule_candidates(self, rule_candidates: List[Dict[str, Any]]) -> int:
        """Insert rule candidates."""
        sql = """
        INSERT INTO learning_rule_candidates (
            candidate_rule_id,
            trigger,
            suggestion,
            confidence,
            status
        ) VALUES (%s, %s, %s, %s, %s)
        """
        count = 0
        with self.conn.cursor() as cur:
            for item in rule_candidates:
                cur.execute(
                    sql,
                    (
                        item.get("candidate_rule_id"),
                        Json(item.get("trigger") or {}),
                        Json(item.get("suggestion") or {}),
                        item.get("confidence_score"),
                        item.get("status", "pending_review"),
                    ),
                )
                count += 1
        return count

    def save_report_preferences(self, preferences: List[Dict[str, Any]]) -> int:
        """Insert report preference candidates."""
        sql = """
        INSERT INTO learning_report_preferences (
            preference_id,
            scenario,
            preference_content,
            status
        ) VALUES (%s, %s, %s, %s)
        """
        count = 0
        with self.conn.cursor() as cur:
            for item in preferences:
                scenario_obj = item.get("scenario") or {}
                cur.execute(
                    sql,
                    (
                        item.get("preference_id"),
                        str(scenario_obj),
                        Json(item),
                        item.get("status", "pending_review"),
                    ),
                )
                count += 1
        return count

    def commit(self) -> None:
        """Commit transaction."""
        self.conn.commit()

    def rollback(self) -> None:
        """Rollback transaction."""
        self.conn.rollback()
