"""
Search History Cases Skill — 数据库访问层
封装 asyncpg 连接池的创建、查询和 JSONB 解析。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import asyncpg

from config import SkillConfig
import queries

logger = logging.getLogger(__name__)


class DatabaseClient:
    """
    异步 PostgreSQL 客户端，基于 asyncpg 连接池。
    通过 DatabaseClient.create() 工厂方法创建实例。
    """

    def __init__(self, pool: asyncpg.Pool, config: SkillConfig) -> None:
        self._pool = pool
        self._config = config

    @classmethod
    async def create(cls, config: SkillConfig) -> "DatabaseClient":
        pool = await asyncpg.create_pool(
            dsn=config.dsn,
            min_size=config.db_pool_min,
            max_size=config.db_pool_max,
        )
        logger.info(
            "连接池已创建：%s:%s/%s",
            config.db_host, config.db_port, config.db_name,
        )
        return cls(pool, config)

    async def close(self) -> None:
        await self._pool.close()
        logger.info("连接池已关闭")

    # ── 主检索查询 ────────────────────────────────────────────

    async def search_records(
        self,
        *,
        business_type: str,
        service_desc_code: str,
        service_type_code: Optional[str],
        equipment_model_code: Optional[str],
        input_task_desc: Optional[str],
        with_service_type: bool,
        limit: int,
    ) -> list[dict[str, Any]]:
        """
        执行精确粗筛（Step 1）或放宽粗筛（Step 2B）。
        with_service_type=True  → Step 1（含 service_type_code 条件）
        with_service_type=False → Step 2B（去掉 service_type_code 条件）
        """
        tier1 = str(self._config.recency_tier1_years)
        tier2 = str(self._config.recency_tier2_years)

        async with self._pool.acquire() as conn:
            if with_service_type:
                rows = await conn.fetch(
                    queries.SEARCH_WITH_SERVICE_TYPE,
                    business_type,        # $1
                    service_desc_code,    # $2
                    service_type_code,    # $3  可 None
                    equipment_model_code, # $4  可 None
                    input_task_desc,      # $5  可 None
                    tier1,               # $6
                    tier2,               # $7
                    limit,               # $8
                )
            else:
                rows = await conn.fetch(
                    queries.SEARCH_WITHOUT_SERVICE_TYPE,
                    business_type,        # $1
                    service_desc_code,    # $2
                    equipment_model_code, # $3  可 None
                    input_task_desc,      # $4  可 None
                    tier1,               # $5
                    tier2,               # $6
                    limit,               # $7
                )
        return [dict(r) for r in rows]

    async def fetch_personnel(
        self, record_ids: list[int]
    ) -> dict[int, list[dict[str, Any]]]:
        """批量拉取人员明细，返回 {record_id: [row, ...]} 映射。"""
        if not record_ids:
            return {}
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(queries.FETCH_PERSONNEL, record_ids)
        result: dict[int, list[dict[str, Any]]] = {}
        for row in rows:
            d = dict(row)
            rid = d["record_id"]
            result.setdefault(rid, []).append(d)
        return result

    async def fetch_remark_similarity(
        self,
        record_ids: list[int],
        input_remark: str,
        threshold: float,
    ) -> dict[int, float]:
        """计算 Top-K 各案例与输入备注的相似度（Step 3，可选）。"""
        if not record_ids or not input_remark:
            return {}
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                queries.FETCH_REMARK_SIMILARITY,
                record_ids,   # $1
                input_remark, # $2
                threshold,    # $3
            )
        return {row["id"]: float(row["remark_sim_score"]) for row in rows}

    # ── JSONB 解析助手 ────────────────────────────────────────

    @staticmethod
    def parse_jsonb(value: Any) -> list[dict]:
        """将 asyncpg 返回的 JSONB 字段统一转为 list[dict]。"""
        if value is None:
            return []
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        if isinstance(value, list):
            return value
        return []