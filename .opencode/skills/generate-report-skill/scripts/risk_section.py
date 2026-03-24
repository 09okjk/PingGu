from typing import Any, Dict, List


def build_risk_rows(assessment_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    risk_results = assessment_result.get("risk_results", []) or []

    level_order = {"high": 0, "medium": 1, "low": 2}
    dedup = {}

    for item in risk_results:
        key = item.get("risk_id") or item.get("risk_name")
        if not key:
            continue
        if key not in dedup:
            dedup[key] = {
                "risk_id": item.get("risk_id"),
                "risk_name": item.get("risk_name"),
                "risk_level": item.get("risk_level", "low"),
                "description": item.get("description", ""),
                "suggested_action": item.get("suggested_action", ""),
                "confidence": item.get("confidence", "low"),
                "source": _to_sources(item),
            }

    rows = list(dedup.values())
    rows.sort(key=lambda x: (level_order.get(x["risk_level"], 9), x["risk_name"] or ""))
    return rows


def _to_sources(item: Dict[str, Any]) -> List[str]:
    sources = []
    for basis in item.get("trigger_basis", []) or []:
        if basis.startswith("history_case:"):
            case_id = basis.replace("history_case:", "")
            sources.append(f"s1_history_case:{case_id}")
        else:
            sources.append(f"s2_risk_trigger:{basis}")

    risk_id = item.get("risk_id")
    if risk_id:
        sources.insert(0, f"s2_risk:{risk_id}")
    return list(dict.fromkeys(sources))