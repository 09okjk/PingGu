from typing import Any, Dict, List


def build_confidence_summary(
    risk_rows: List[Dict[str, Any]],
    task_rows: List[Dict[str, Any]],
    totals: Dict[str, Any],
    tool_rows: List[Dict[str, Any]],
    material_rows: List[Dict[str, Any]],
    special_tool_rows: List[Dict[str, Any]],
    spare_parts_or_equipment: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, str]:
    return {
        "risks": _section_confidence(risk_rows),
        "tasks": _section_confidence(task_rows),
        "totals": _totals_confidence(totals),
        "tools": _section_confidence(tool_rows),
        "materials": _section_confidence(material_rows),
        "special_tools": _section_confidence(special_tool_rows),
        "spare_parts_or_equipment": _spare_parts_confidence(spare_parts_or_equipment),
    }


def _section_confidence(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "low"

    order = {"high": 3, "medium": 2, "low": 1}
    scores = [order.get(row.get("confidence", "low"), 1) for row in rows]
    avg = sum(scores) / len(scores)

    if avg >= 2.6:
        return "high"
    if avg >= 1.8:
        return "medium"
    return "low"


def _totals_confidence(totals: Dict[str, Any]) -> str:
    values = [
        (totals.get("is_voyage_repair") or {}).get("confidence", "low"),
        (totals.get("total_hours") or {}).get("confidence", "low"),
        (totals.get("total_persons") or {}).get("confidence", "low"),
    ]
    return _confidence_from_values(values)


def _spare_parts_confidence(sp: Dict[str, List[Dict[str, Any]]]) -> str:
    values = []
    for key in ["customer_provided", "provider_provided", "to_be_confirmed"]:
        for item in sp.get(key, []):
            values.append(item.get("confidence", "low"))
    return _confidence_from_values(values)


def _confidence_from_values(values: List[str]) -> str:
    if not values:
        return "low"
    order = {"high": 3, "medium": 2, "low": 1}
    avg = sum(order.get(v, 1) for v in values) / len(values)
    if avg >= 2.6:
        return "high"
    if avg >= 1.8:
        return "medium"
    return "low"