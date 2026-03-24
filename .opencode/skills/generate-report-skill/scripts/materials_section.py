from collections import defaultdict
from typing import Any, Dict, List, Tuple


def build_tool_rows(history_cases: List[Dict[str, Any]], warnings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return _aggregate_items(history_cases, "tools", "tools", warnings)


def build_material_rows(history_cases: List[Dict[str, Any]], warnings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return _aggregate_items(history_cases, "materials", "materials", warnings)


def build_special_tool_rows(history_cases: List[Dict[str, Any]], warnings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return _aggregate_items(history_cases, "special_tools", "special_tools", warnings)


def _aggregate_items(
    history_cases: List[Dict[str, Any]],
    field_name: str,
    warning_name: str,
    warnings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    total_cases = len(history_cases)
    grouped: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}

    for case in history_cases:
        case_id = case.get("case_id", "unknown")
        items = case.get(field_name, []) or []

        seen_keys_in_case = set()

        for item in items:
            item_name = item.get("toolName", "") or ""
            item_model = item.get("model", "") or ""
            unit = item.get("unitMeasurement", {}) or {}
            unit_code = unit.get("no", "") or ""
            unit_name = unit.get("zhName", "") or ""
            type_code = str(item.get("toolTypeNo", "") or "")

            key = (item_name, item_model, unit_code, type_code)
            if key not in grouped:
                grouped[key] = {
                    "item_name": item_name,
                    "item_model": item_model or None,
                    "item_type_code": item.get("toolTypeNo"),
                    "unit": {
                        "code": unit_code,
                        "name": unit_name,
                    },
                    "quantities": [],
                    "case_count": 0,
                    "source": [],
                }

            grouped[key]["quantities"].append(item.get("quantity"))
            grouped[key]["source"].append(f"s1_history_case:{case_id}")

            if key not in seen_keys_in_case:
                grouped[key]["case_count"] += 1
                seen_keys_in_case.add(key)

    rows = []
    for _, value in grouped.items():
        quantity = _pick_quantity(value["quantities"])
        confidence = _confidence_from_frequency(value["case_count"], total_cases)

        row = {
            "item_name": value["item_name"],
            "item_model": value["item_model"],
            "item_type_code": value["item_type_code"],
            "unit": value["unit"],
            "quantity": quantity,
            "confidence": confidence,
            "source": list(dict.fromkeys(value["source"])),
            "notes": [],
        }

        if value["case_count"] == 1 and total_cases >= 3:
            row["notes"].append("该项仅在少量历史案例中出现，建议人工确认。")

        rows.append(row)

    rows.sort(key=lambda x: (x["item_name"] or "", x["item_model"] or ""))

    if total_cases > 0 and not rows:
        warnings.append(
            {
                "code": f"{warning_name.upper()}_EMPTY",
                "message": f"历���案例中未形成稳定的 {warning_name} 推荐结果。",
                "severity": "low",
            }
        )

    if total_cases >= 3 and rows:
        low_conf_ratio = len([r for r in rows if r["confidence"] == "low"]) / max(len(rows), 1)
        if low_conf_ratio >= 0.5:
            warnings.append(
                {
                    "code": f"{warning_name.upper()}_DIVERGENT",
                    "message": f"{warning_name} 推荐项分歧较大，建议人工确认清单完整性。",
                    "severity": "medium",
                }
            )

    return rows


def _pick_quantity(values: List[Any]) -> Any:
    clean = [v for v in values if isinstance(v, (int, float))]
    if not clean:
        return None
    clean.sort()
    return clean[len(clean) // 2]


def _confidence_from_frequency(case_count: int, total_cases: int) -> str:
    if total_cases <= 0:
        return "low"
    ratio = case_count / total_cases
    if ratio >= 0.6:
        return "high"
    if ratio >= 0.3:
        return "medium"
    return "low"