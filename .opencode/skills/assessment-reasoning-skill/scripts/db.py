import json
import os
from typing import Any, Dict, List, Optional

from env_loader import get_bool_env, get_env, load_env_file
from utils import load_json_file, refs_path

# 加载 .env 文件中的环境变量
load_env_file()


class ReferenceRepository:
    """
    Reference 读取仓储：
    - 数据库优先模式（生产推荐）
    - 本地 JSON 降级模式（离线调试）
    """

    def __init__(self, refs_dir: str):
        self.refs_dir = refs_dir
        self.use_db = get_bool_env("PINGGU_USE_DB", True)  # 默认启用数据库模式

        if not self.use_db:
            import warnings

            warnings.warn(
                "⚠️  当前使用本地 JSON 模式（离线调试）。"
                "生产环境应设置 PINGGU_USE_DB=true 从数据库读取规则。",
                UserWarning,
                stacklevel=2,
            )

        self._conn = None

    def _ensure_connection(self):
        if not self.use_db:
            return None

        if self._conn is not None:
            return self._conn

        try:
            import psycopg2
        except ImportError as e:
            raise RuntimeError(
                "数据库模式需要安装 psycopg2。请执行: pip install psycopg2-binary"
            ) from e

        self._conn = psycopg2.connect(
            host=get_env("PINGGU_DB_HOST", "localhost"),
            port=int(get_env("PINGGU_DB_PORT", "5432")),
            dbname=get_env("PINGGU_DB_NAME", "pinggu"),
            user=get_env("PINGGU_DB_USER", "postgres"),
            password=get_env("PINGGU_DB_PASSWORD", ""),
            sslmode=get_env("PINGGU_DB_SSLMODE", "disable"),
        )
        return self._conn

    def _fetch_all(
        self, sql: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        conn = self._ensure_connection()
        if conn is None:
            return []

        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

        results = []
        for row in rows:
            item = {}
            for idx, value in enumerate(row):
                item[columns[idx]] = value
            results.append(item)
        return results

    @staticmethod
    def _parse_jsonish(value: Any, default):
        if value is None:
            return default
        if isinstance(value, (list, dict)):
            return value
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return default
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return default
        return default

    def get_risk_rules(self) -> List[Dict[str, Any]]:
        if self.use_db:
            sql = """
                SELECT
                    risk_id,
                    risk_name,
                    risk_level,
                    description,
                    suggested_action,
                    service_type_codes,
                    equipment_name_codes,
                    equipment_model_codes,
                    keyword_triggers,
                    is_active
                FROM risk_rules
                WHERE is_active = TRUE
                ORDER BY risk_id;
            """
            rows = self._fetch_all(sql)
            if rows:
                normalized = []
                for row in rows:
                    normalized.append(
                        {
                            "risk_id": row["risk_id"],
                            "risk_name": row["risk_name"],
                            "risk_level": row["risk_level"],
                            "description": row["description"],
                            "suggested_action": row["suggested_action"],
                            "service_type_codes": self._parse_jsonish(
                                row.get("service_type_codes"), []
                            ),
                            "equipment_name_codes": self._parse_jsonish(
                                row.get("equipment_name_codes"), []
                            ),
                            "equipment_model_codes": self._parse_jsonish(
                                row.get("equipment_model_codes"), []
                            ),
                            "keyword_triggers": self._parse_jsonish(
                                row.get("keyword_triggers"), []
                            ),
                            "is_active": bool(row.get("is_active", True)),
                        }
                    )
                return normalized

        return load_json_file(refs_path(self.refs_dir, "r3-risk-rules.json"))

    def get_workhour_rules(self) -> List[Dict[str, Any]]:
        if self.use_db:
            sql = """
                SELECT
                    rule_id,
                    service_type_code,
                    equipment_name_code,
                    task_tag,
                    work_type_code,
                    baseline_hours,
                    quantity_factor,
                    risk_adjustments,
                    sample_size,
                    is_active
                FROM workhour_rules
                WHERE is_active = TRUE
                ORDER BY rule_id;
            """
            rows = self._fetch_all(sql)
            if rows:
                normalized = []
                for row in rows:
                    normalized.append(
                        {
                            "rule_id": row["rule_id"],
                            "service_type_code": row["service_type_code"],
                            "equipment_name_code": row["equipment_name_code"],
                            "task_tag": row["task_tag"],
                            "work_type_code": row["work_type_code"],
                            "baseline_hours": float(row["baseline_hours"])
                            if row["baseline_hours"] is not None
                            else 0,
                            "quantity_factor": float(row["quantity_factor"])
                            if row["quantity_factor"] is not None
                            else 0,
                            "risk_adjustments": self._parse_jsonish(
                                row.get("risk_adjustments"), []
                            ),
                            "sample_size": int(row["sample_size"])
                            if row["sample_size"] is not None
                            else 0,
                            "is_active": bool(row.get("is_active", True)),
                        }
                    )
                return normalized

        return load_json_file(refs_path(self.refs_dir, "r5-workhour-rules.json"))

    def get_manpower_rules(self) -> Dict[str, Any]:
        if self.use_db:
            global_sql = """
                SELECT rule_key, rule_value, description
                FROM manpower_global_rules
                ORDER BY rule_key;
            """
            level_sql = """
                SELECT
                    work_type_code,
                    higher_level_code,
                    lower_level_code,
                    is_active
                FROM manpower_level_cover_rules
                WHERE is_active = TRUE
                ORDER BY work_type_code, higher_level_code, lower_level_code;
            """

            global_rows = self._fetch_all(global_sql)
            level_rows = self._fetch_all(level_sql)

            if global_rows or level_rows:
                global_rules: Dict[str, Any] = {}
                for row in global_rows:
                    raw = row.get("rule_value")
                    if isinstance(raw, str) and raw.strip().lower() in {
                        "true",
                        "false",
                    }:
                        global_rules[row["rule_key"]] = raw.strip().lower() == "true"
                    else:
                        global_rules[row["rule_key"]] = raw

                return {
                    "global_rules": global_rules,
                    "level_cover_rules": [
                        {
                            "work_type_code": row["work_type_code"],
                            "higher_level_code": row["higher_level_code"],
                            "lower_level_code": row["lower_level_code"],
                            "is_active": bool(row.get("is_active", True)),
                        }
                        for row in level_rows
                    ],
                }

        return load_json_file(refs_path(self.refs_dir, "r6-manpower-rules.json"))

    def close(self):
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None
