from typing import Any, Dict, List

from models import WorkhourResult
from utils import avg, safe_get


def estimate_workhours(
    requirement: Dict[str, Any],
    history_cases: List[Dict[str, Any]],
    workhour_rules: List[Dict[str, Any]],
    risk_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    service_type_code = safe_get(requirement, "service_type", "code", default="")
    equipment_name_code = safe_get(requirement, "equipment_name", "code", default="")
    equipment_quantity = requirement.get("equipment_quantity", 1) or 1

    history_task_hours: List[float] = []
    history_task_tag = "通用任务"

    for case in history_cases:
        if case.get("task_description"):
            history_task_tag = case["task_description"]

        for person in case.get("personnel", []):
            hour = person.get("construction_hour")
            if isinstance(hour, (int, float)):
                history_task_hours.append(float(hour))

    matched_rule = None
    for rule in workhour_rules:
        if not rule.get("is_active", True):
            continue
        if (
            rule.get("service_type_code") == service_type_code
            and rule.get("equipment_name_code") == equipment_name_code
        ):
            matched_rule = rule
            break

    basis: List[str] = []
    base_hours = 0.0

    if history_task_hours:
        base_hours = avg(history_task_hours)
        basis.append("history_case_avg")

    if matched_rule:
        if base_hours <= 0:
            base_hours = float(matched_rule.get("baseline_hours", 0))
        else:
            base_hours = (base_hours + float(matched_rule.get("baseline_hours", 0))) / 2
        basis.append(f"r5_rule:{matched_rule['rule_id']}")

    if base_hours <= 0:
        base_hours = 8.0

    quantity_factor = 1.0
    if matched_rule and equipment_quantity > 1:
        increment = float(matched_rule.get("quantity_factor", 0))
        quantity_factor += increment * (equipment_quantity - 1)

    risk_multiplier = 1.0
    if matched_rule:
        adjustments = matched_rule.get("risk_adjustments", [])
        for result in risk_results:
            triggers = result.get("trigger_basis", [])
            for adj in adjustments:
                trigger = adj.get("trigger")
                if any(trigger in item for item in triggers):
                    risk_multiplier *= float(adj.get("multiplier", 1.0))
                    basis.append(f"risk_adjustment:{trigger}")

    suggested = int(round(base_hours * quantity_factor * risk_multiplier))

    confidence = "low"
    if "history_case_avg" in basis and matched_rule:
        confidence = "medium"
        if matched_rule.get("sample_size", 0) >= 10:
            confidence = "high"
    elif "history_case_avg" in basis or matched_rule:
        confidence = "medium"

    result = WorkhourResult(
        task_tag=history_task_tag,
        suggested_hours=suggested,
        confidence=confidence,
        basis=basis,
        note="当前为单值估算结果，后续可升级为区间估算。",
    )

    return [result.to_dict()]