from typing import Any, Dict, List

from models import RiskResult
from utils import contains_any_keyword, safe_get


def match_risks(requirement: Dict[str, Any], history_cases: List[Dict[str, Any]], risk_rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    service_type_code = safe_get(requirement, "service_type", "code", default="")
    equipment_name_code = safe_get(requirement, "equipment_name", "code", default="")
    equipment_model_code = safe_get(requirement, "equipment_model", "code", default="")
    remark = requirement.get("remark", "") or ""

    history_text = "\n".join(
        [str(case.get("risk_description", "")) for case in history_cases]
    )

    results: List[RiskResult] = []

    for rule in risk_rules:
        if not rule.get("is_active", True):
            continue

        basis: List[str] = []
        score = 0

        if service_type_code and service_type_code in rule.get("service_type_codes", []):
            basis.append(f"service_type:{service_type_code}")
            score += 1

        if equipment_name_code and equipment_name_code in rule.get("equipment_name_codes", []):
            basis.append(f"equipment_name:{equipment_name_code}")
            score += 1

        model_codes = rule.get("equipment_model_codes", [])
        if equipment_model_code and model_codes and equipment_model_code in model_codes:
            basis.append(f"equipment_model:{equipment_model_code}")
            score += 1

        keyword_hits = contains_any_keyword(remark, rule.get("keyword_triggers", []))
        for hit in keyword_hits:
            basis.append(f"remark_keyword:{hit}")
        if keyword_hits:
            score += 2

        history_hits = contains_any_keyword(history_text, rule.get("keyword_triggers", []))
        if history_hits:
            basis.append(f"history_case:{history_cases[0].get('case_id', 'unknown')}")
            score += 1

        if score <= 0:
            continue

        if score >= 4:
            confidence = "high"
        elif score >= 2:
            confidence = "medium"
        else:
            confidence = "low"

        results.append(
            RiskResult(
                risk_id=rule["risk_id"],
                risk_name=rule["risk_name"],
                risk_level=rule["risk_level"],
                confidence=confidence,
                trigger_basis=basis,
                description=rule["description"],
                suggested_action=rule["suggested_action"],
            )
        )

    results.sort(
        key=lambda x: (
            {"high": 0, "medium": 1, "low": 2}.get(x.confidence, 9),
            {"high": 0, "medium": 1, "low": 2}.get(x.risk_level, 9),
            x.risk_name,
        )
    )

    return [r.to_dict() for r in results]