from typing import Any, Dict, List


def build_source_summary(
    history_cases: List[Dict[str, Any]],
    assessment_result: Dict[str, Any],
) -> Dict[str, Any]:
    history_case_ids = [case.get("case_id") for case in history_cases if case.get("case_id")]

    risk_rule_ids = [
        item.get("risk_id")
        for item in assessment_result.get("risk_results", []) or []
        if item.get("risk_id")
    ]

    workhour_rule_ids = []
    for item in assessment_result.get("workhour_results", []) or []:
        for basis in item.get("basis", []) or []:
            if isinstance(basis, str) and basis.startswith("r5_rule:"):
                workhour_rule_ids.append(basis.replace("r5_rule:", ""))

    used_reference_types = ["requirement", "assessment_reasoning"]
    if history_case_ids:
        used_reference_types.insert(1, "history_cases")

    return {
        "history_case_ids": list(dict.fromkeys(history_case_ids)),
        "risk_rule_ids": list(dict.fromkeys(risk_rule_ids)),
        "workhour_rule_ids": list(dict.fromkeys(workhour_rule_ids)),
        "used_reference_types": used_reference_types,
    }