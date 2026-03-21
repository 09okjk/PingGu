"""
Search History Cases Skill — 配置项
全部配置由环境变量驱动，无任何硬编码。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    """
    简易 .env 加载器，避免引入 python-dotenv 依赖。
    优先读取脚本所在目录的父级（skill 根目录）中的 .env 文件。
    """
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


# 启动时自动加载 .env
_load_dotenv()


@dataclass(frozen=True)
class SkillConfig:
    # ── 数据库连接 ────────────────────────────────────────────
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    db_pool_min: int
    db_pool_max: int
    db_connect_timeout: int

    # ── 检索行为 ──────────────────────────────────────────────
    default_top_k: int
    candidate_limit: int
    candidate_threshold: int
    remark_sim_threshold: float

    # ── 时间衰减区间（年）────────────────────────────────────
    recency_tier1_years: int
    recency_tier2_years: int

    @classmethod
    def from_env(cls) -> "SkillConfig":
        return cls(
            db_host              = os.environ.get("PINGGU_DB_HOST", "localhost"),
            db_port              = int(os.environ.get("PINGGU_DB_PORT", "5432")),
            db_name              = os.environ.get("PINGGU_DB_NAME", "pinggu"),
            db_user              = os.environ.get("PINGGU_DB_USER", "pinggu_user"),
            db_password          = os.environ.get("PINGGU_DB_PASSWORD", ""),
            db_pool_min          = int(os.environ.get("PINGGU_DB_POOL_MIN", "1")),
            db_pool_max          = int(os.environ.get("PINGGU_DB_POOL_MAX", "5")),
            db_connect_timeout   = int(os.environ.get("PINGGU_DB_CONNECT_TIMEOUT", "10")),
            default_top_k        = int(os.environ.get("S1_DEFAULT_TOP_K", "5")),
            candidate_limit      = int(os.environ.get("S1_CANDIDATE_LIMIT", "20")),
            candidate_threshold  = int(os.environ.get("S1_CANDIDATE_THRESHOLD", "5")),
            remark_sim_threshold = float(os.environ.get("S1_REMARK_SIM_THRESHOLD", "0.1")),
            recency_tier1_years  = int(os.environ.get("S1_RECENCY_TIER1_YEARS", "2")),
            recency_tier2_years  = int(os.environ.get("S1_RECENCY_TIER2_YEARS", "3")),
        )

    @property
    def dsn(self) -> str:
        return (
            f"host={self.db_host} port={self.db_port} "
            f"dbname={self.db_name} user={self.db_user} "
            f"password={self.db_password} "
            f"connect_timeout={self.db_connect_timeout}"
        )