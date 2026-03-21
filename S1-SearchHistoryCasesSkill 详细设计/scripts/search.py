#!/usr/bin/env python3
"""
Search History Cases Skill — 主入口
支持命令行直接运行和作为模块导入两种方式。

命令行示例：
    python3 search.py \\
        --business-type "轮机" \\
        --service-desc-code "RS0000000001" \\
        --service-type-code "CS0017" \\
        --equipment-model-code "ET000000000826" \\
        --task-description "主机坞修保养" \\
        --top-k 5

模块导入示例：
    import asyncio
    from search import SearchHistoryCasesSkill
    from models import RequirementInput

    async def main():
        async with SearchHistoryCasesSkill.context() as skill:
            result = await skill.execute(RequirementInput(
                business_type="轮机",
                service_desc_code="RS0000000001",
                top_k=5,
            ))
            print(result.model_dump_json(indent=2, ensure_ascii=False))

    asyncio.run(main())
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Optional

# 将 scripts/ 目录加入路径，支持直接运行
sys.path.insert(0, str(Path(__file__).parent))

from config import SkillConfig
from db import DatabaseClient
from models import (
    EquipmentInfo,
    HistoryCaseResult,
    MaterialItem,
    PersonnelItem,
    RequirementInput,
    SearchOutput,
    SpecialToolItem,
    ToolItem,
    WORK_SCHEDULE_MAP,
)

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("search-history-cases")

# ── Skill 元数据 ──────────────────────────────────────────────
SKILL_NAME = "search_history_cases"
SKILL_VERSION = "1.0.0"
SKILL_DESCRIPTION = (
    "根据服务需求单，从历史评估数据库中渐进式检索最相似的 Top-K 历史案例。"
    "四步策略：精确粗筛 → 条件放宽 → 取 Top-K 并拉取人员明细 → 备注相似度补充。"
)


class SearchHistoryCasesSkill:
    """
    S1 — SearchHistoryCasesSkill

    渐进式历史案例检索 Skill，封装四步 Agentic 检索逻辑。
    """

    def __init__(self, db: DatabaseClient, config: SkillConfig) -> None:
        self._db = db
        self._config = config

    # ── 生命周期 ──────────────────────────────────────────────

    @classmethod
    async def create(
        cls, config: Optional[SkillConfig] = None
    ) -> "SearchHistoryCasesSkill":
        """创建 Skill 实例，初始化连接池。config 为 None 时从环境变量读取。"""
        cfg = config or SkillConfig.from_env()
        db = await DatabaseClient.create(cfg)
        return cls(db, cfg)

    async def close(self) -> None:
        await self._db.close()

    @classmethod
    @asynccontextmanager
    async def context(
        cls, config: Optional[SkillConfig] = None
    ) -> AsyncIterator["SearchHistoryCasesSkill"]:
        """异步上下文管理器，自动管理连接池生命周期。"""
        skill = await cls.create(config)
        try:
            yield skill
        finally:
            await skill.close()

    # ── 对外标准接口 ──────────────────────────────────────────

    async def execute(self, requirement: RequirementInput) -> SearchOutput:
        """
        Skill 主入口：接受 RequirementInput，返回 SearchOutput。

        Args:
            requirement: 服务需求单输入对象

        Returns:
            SearchOutput，包含 Top-K 案例列表及检索元数据
        """
        logger.info(
            "[S1] 开始检索 | %s / %s / %s | top_k=%d",
            requirement.business_type,
            requirement.service_desc_code,
            requirement.service_type_code,
            requirement.top_k,
        )

        # ── Step 1：精确粗筛 ──────────────────────────────────
        candidates = await self._db.search_records(
            business_type        = requirement.business_type,
            service_desc_code    = requirement.service_desc_code,
            service_type_code    = requirement.service_type_code,
            equipment_model_code = requirement.equipment_model_code,
            input_task_desc      = requirement.task_description,
            with_service_type    = True,
            limit                = self._config.candidate_limit,
        )
        total_found = len(candidates)
        logger.debug("[S1] Step1 候选集：%d 条", total_found)

        # ── Step 2B：候选不足时自动放宽 ──────────────────────
        relaxed = False
        if total_found < self._config.candidate_threshold:
            logger.info(
                "[S1] 候选集不足（%d < %d），触发条件放宽",
                total_found,
                self._config.candidate_threshold,
            )
            candidates = await self._db.search_records(
                business_type        = requirement.business_type,
                service_desc_code    = requirement.service_desc_code,
                service_type_code    = None,
                equipment_model_code = requirement.equipment_model_code,
                input_task_desc      = requirement.task_description,
                with_service_type    = False,
                limit                = self._config.candidate_limit,
            )
            relaxed = True
            logger.debug("[S1] Step2B 放宽后候选集：%d 条", len(candidates))

        # ── Step 2A：取 Top-K，批量拉取人员明细 ──────────────
        top_cases = candidates[: requirement.top_k]
        record_ids = [c["id"] for c in top_cases]

        personnel_map = await self._db.fetch_personnel(record_ids)
        logger.debug("[S1] 拉取人员明细，record_ids=%s", record_ids)

        # ── Step 3：备注相似度补充（可选）────────────────────
        remark_scores: dict[int, float] = {}
        if requirement.remark and record_ids:
            remark_scores = await self._db.fetch_remark_similarity(
                record_ids   = record_ids,
                input_remark = requirement.remark,
                threshold    = self._config.remark_sim_threshold,
            )
            logger.debug("[S1] 备注相似度：%s", remark_scores)

        # ── Step 4：构建返回结果 ──────────────────────────────
        results = [
            self._build_result(
                row, requirement, relaxed, personnel_map, remark_scores
            )
            for row in top_cases
        ]

        logger.info("[S1] 完成，返回 %d 条 | relaxed=%s", len(results), relaxed)
        return SearchOutput(
            cases       = results,
            total_found = total_found,
            relaxed     = relaxed,
            input_echo  = requirement,
        )

    # ── 内部辅助方法 ──────────────────────────────────────────

    def _build_result(
        self,
        row: dict,
        req: RequirementInput,
        relaxed: bool,
        personnel_map: dict[int, list[dict]],
        remark_scores: dict[int, float],
    ) -> HistoryCaseResult:
        record_id  = row["id"]
        task_sim   = float(row.get("task_sim_score") or 0.0)
        remark_sim = remark_scores.get(record_id)
        ws         = row.get("work_schedule")

        return HistoryCaseResult(
            case_id            = row["service_order_no"],
            match_reason       = self._build_match_reason(row, req, task_sim, relaxed),
            task_sim_score     = task_sim,
            remark_sim_score   = remark_sim,
            evaluated_at       = row.get("evaluated_at"),
            equipment_info     = EquipmentInfo(
                model_code = row.get("equipment_model_code"),
                model_name = row.get("equipment_model_name"),
                qty        = row.get("equipment_qty"),
                unit       = row.get("equipment_unit"),
            ),
            risk_description   = row.get("risk_description"),
            task_description   = row.get("task_description"),
            total_persons      = row.get("total_persons"),
            total_days         = (
                float(row["total_days"]) if row.get("total_days") is not None else None
            ),
            work_schedule      = ws,
            work_schedule_label= WORK_SCHEDULE_MAP.get(ws) if ws else None,
            construction_hours = (
                float(row["construction_hours"])
                if row.get("construction_hours") is not None else None
            ),
            inspection_hours   = (
                float(row["inspection_hours"])
                if row.get("inspection_hours") is not None else None
            ),
            personnel     = self._parse_personnel(personnel_map.get(record_id, [])),
            tools         = self._parse_tools(row.get("tools_content")),
            materials     = self._parse_materials(row.get("materials_content")),
            special_tools = self._parse_special_tools(row.get("special_tools_content")),
        )

    @staticmethod
    def _build_match_reason(
        row: dict,
        req: RequirementInput,
        task_sim: float,
        relaxed: bool,
    ) -> str:
        parts = [f"业务归口({req.business_type})"]
        if row.get("service_desc_name"):
            parts.append(f"服务描述({row['service_desc_name']})")
        if not relaxed and row.get("service_type_name"):
            parts.append(f"服务类型({row['service_type_name']})")
        if (
            req.equipment_model_code
            and row.get("equipment_model_code") == req.equipment_model_code
        ):
            label = row.get("equipment_model_name") or req.equipment_model_code
            parts.append(f"设备型号({label})")

        reason = "命中：" + " + ".join(parts)
        if task_sim > 0:
            reason += f" | 任务相似度: {task_sim:.2f}"
        if relaxed:
            reason += " | ⚠️ 服务类型条件已放宽"
        return reason

    @staticmethod
    def _parse_personnel(rows: list[dict]) -> list[PersonnelItem]:
        result = []
        for r in rows:
            ch = r.get("construction_hour")
            result.append(PersonnelItem(
                work_type_code    = r.get("work_type_code"),
                work_type_name    = r.get("work_type_name"),
                job_level_code    = r.get("job_level_code"),
                job_level_name    = r.get("job_level_name"),
                quantity          = r.get("quantity"),
                construction_hour = float(ch) if ch is not None else None,
                task_desc         = r.get("detailed_job_responsibilities"),
            ))
        return result

    def _parse_tools(self, raw: Any) -> list[ToolItem]:
        result = []
        for item in self._db.parse_jsonb(raw):
            um = item.get("unitMeasurement") or {}
            result.append(ToolItem(
                tool_name   = item.get("toolName", ""),
                tool_type_no= item.get("toolTypeNo"),
                quantity    = item.get("quantity", 0),
                unit_code   = um.get("no"),
                unit_name   = um.get("zhName"),
            ))
        return result

    def _parse_materials(self, raw: Any) -> list[MaterialItem]:
        result = []
        for item in self._db.parse_jsonb(raw):
            um = item.get("unitMeasurement") or {}
            result.append(MaterialItem(
                tool_name = item.get("toolName", ""),
                model     = item.get("model"),
                quantity  = item.get("quantity", 0),
                unit_code = um.get("no"),
                unit_name = um.get("zhName"),
            ))
        return result

    def _parse_special_tools(self, raw: Any) -> list[SpecialToolItem]:
        result = []
        for item in self._db.parse_jsonb(raw):
            um = item.get("unitMeasurement") or {}
            result.append(SpecialToolItem(
                tool_name = item.get("toolName", ""),
                model     = item.get("model"),
                quantity  = item.get("quantity", 0),
                unit_code = um.get("no"),
                unit_name = um.get("zhName"),
            ))
        return result


# ── 命令行入口 ────────────────────────────────────────────────

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="search.py",
        description="S1 SearchHistoryCasesSkill — 历史评估案例渐进式检索",
    )
    p.add_argument("--business-type",        required=True,  help="业务归口：电气 / 轮机")
    p.add_argument("--service-desc-code",    required=True,  help="服务描述编码")
    p.add_argument("--service-type-code",    default=None,   help="服务类型编码（可选）")
    p.add_argument("--equipment-model-code", default=None,   help="设备型号编码（可选）")
    p.add_argument("--task-description",     default=None,   help="施工任务描述（可选）")
    p.add_argument("--remark",               default=None,   help="备注文本（可选）")
    p.add_argument("--top-k",  type=int, default=5,          help="返回案例数（默认 5，最大 20）")
    p.add_argument(
        "--output", default="stdout",
        help="输出目标：stdout（默认）或文件路径",
    )
    p.add_argument(
        "--format", choices=["json", "pretty"], default="json",
        help="输出格式：json（单行，默认）/ pretty（带缩进）",
    )
    p.add_argument("--verbose", "-v", action="store_true", help="输出调试日志")
    return p


async def _async_main(args: argparse.Namespace) -> None:
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    req = RequirementInput(
        business_type        = args.business_type,
        service_desc_code    = args.service_desc_code,
        service_type_code    = args.service_type_code,
        equipment_model_code = args.equipment_model_code,
        task_description     = args.task_description,
        remark               = args.remark,
        top_k                = min(max(1, args.top_k), 20),
    )

    async with SearchHistoryCasesSkill.context() as skill:
        output = await skill.execute(req)

    # 序列化
    indent = 2 if args.format == "pretty" else None
    json_str = output.model_dump_json(indent=indent, ensure_ascii=False)

    if args.output == "stdout":
        print(json_str)
    else:
        Path(args.output).write_text(json_str, encoding="utf-8")
        print(f"✅ 结果已写入：{args.output}", file=sys.stderr)


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()
    asyncio.run(_async_main(args))


if __name__ == "__main__":
    main()