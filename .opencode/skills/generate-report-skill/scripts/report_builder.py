from datetime import datetime
from typing import Any, Dict, List

from confidence import build_confidence_summary
from materials_section import (
    build_material_rows,
    build_special_tool_rows,
    build_tool_rows,
)
from risk_section import build_risk_rows
from sources import build_source_summary
from spare_parts_section import build_spare_parts_or_equipment
from summary_builder import build_summary
from task_section import build_task_rows
from totals_section import build_totals


def generate_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    requirement = payload.get("requirement", {}) or {}
    history_cases = payload.get("history_cases", []) or []
    assessment_result = payload.get("assessment_result", {}) or {}
    options = payload.get("options", {}) or {}

    warnings: List[Dict[str, Any]] = []

    _validate_inputs(requirement, assessment_result, warnings)

    summary = build_summary(requirement)
    risk_rows = build_risk_rows(assessment_result)
    task_rows = build_task_rows(requirement, history_cases, assessment_result, warnings)
    totals = build_totals(requirement, assessment_result, task_rows, warnings)
    tool_rows = build_tool_rows(history_cases, warnings)
    material_rows = build_material_rows(history_cases, warnings)
    special_tool_rows = build_special_tool_rows(history_cases, warnings)
    spare_parts_or_equipment = build_spare_parts_or_equipment(
        requirement, history_cases, warnings
    )

    confidence_summary = build_confidence_summary(
        risk_rows,
        task_rows,
        totals,
        tool_rows,
        material_rows,
        special_tool_rows,
        spare_parts_or_equipment,
    )
    source_summary = build_source_summary(history_cases, assessment_result)
    review_focus = build_review_focus(
        risk_rows,
        task_rows,
        totals,
        spare_parts_or_equipment,
        warnings,
        include_review_focus=options.get("include_review_focus", True),
    )

    return {
        "requirement_id": requirement.get("requirement_id", ""),
        "status": "ok",
        "report_version": "1.1.0",
        "report_language": options.get("output_language", "zh-CN"),
        "report_type": "service_assessment_draft",
        "report_for": [
            "engineering_review",
            "quotation_preparation",
        ],
        "summary": summary,
        "report_table": {
            "risk_rows": risk_rows,
            "task_rows": task_rows,
            "totals": totals,
            "tool_rows": tool_rows,
            "material_rows": material_rows,
            "special_tool_rows": special_tool_rows,
            "spare_parts_or_equipment": spare_parts_or_equipment,
        },
        "confidence_summary": confidence_summary,
        "source_summary": source_summary,
        "warnings": warnings,
        "review_focus": review_focus,
        "metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "generator_version": "1.1.0",
        },
    }


def build_review_focus(
    risk_rows: List[Dict[str, Any]],
    task_rows: List[Dict[str, Any]],
    totals: Dict[str, Any],
    spare_parts_or_equipment: Dict[str, List[Dict[str, Any]]],
    warnings: List[Dict[str, Any]],
    include_review_focus: bool = True,
) -> List[str]:
    if not include_review_focus:
        return []

    focus: List[str] = []

    if any(row.get("risk_level") == "high" for row in risk_rows):
        focus.append("请重点确认高风险项是否需要影响工期、资源投入或现场作业安排。")

    if any(row.get("confidence") == "low" for row in task_rows):
        focus.append("请确认施工任务拆分是否完整，低置信任务建议工务人员人工调整。")

    if (totals.get("is_voyage_repair") or {}).get("confidence") == "low":
        focus.append("请确认服务地点类型，以确保是否航修判断准确。")

    if spare_parts_or_equipment.get("to_be_confirmed"):
        focus.append("请重点确认设备/备件由客户提供、我方提供，还是仍待确认。")

    if any(w["severity"] == "high" for w in warnings):
        focus.append("当前存在高优先级 warning，请工务人员优先处理。")

    if warnings:
        focus.append("请结合 warnings 列表优先复核数据稳定性不足的字段。")

    return list(dict.fromkeys(focus))


def _validate_inputs(
    requirement: Dict[str, Any],
    assessment_result: Dict[str, Any],
    warnings: List[Dict[str, Any]],
) -> None:
    if not requirement.get("requirement_id"):
        warnings.append(
            {
                "code": "REQUIREMENT_ID_MISSING",
                "message": "requirement_id 缺失，建议补充唯一需求项标识。",
                "severity": "medium",
            }
        )

    if not assessment_result:
        warnings.append(
            {
                "code": "ASSESSMENT_RESULT_MISSING",
                "message": "assessment_result 缺失，报告将严重依赖历史案例或占位输出。",
                "severity": "high",
            }
        )