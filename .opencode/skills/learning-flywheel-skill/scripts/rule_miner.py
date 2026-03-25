from typing import Any, Dict, List

from utils import confidence_from_score, normalize_text, safe_get


def _extract_remark_keywords(requirement: Dict[str, Any]) -> List[str]:
    """Extract lightweight remark keywords."""
    remark = normalize_text(requirement.get("remark"))
    if not remark:
        return []
    candidates = ["交叉作业", "备件", "停航", "异常振动", "进出坞", "时效", "风险"]
    return [keyword for keyword in candidates if keyword in remark]


def mine_rule_candidates(
    context: Dict[str, Any],
    artifacts: Dict[str, Any],
    revision_diff: List[Dict[str, Any]],
    feedback_tags: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Mine candidate rules from a single revision case."""
    requirement = safe_get(artifacts, "requirement_json", {})
    results: List[Dict[str, Any]] = []

    tag_codes = {normalize_text(item.get("tag_code")) for item in feedback_tags}

    if "RISK_UNDER_ESTIMATED" in tag_codes:
        confidence = 0.78
        results.append(
            {
                "candidate_rule_id": "CR-RISK-001",
                "trigger": {
                    "business_type": safe_get(context, "business_type"),
                    "service_desc_code": safe_get(safe_get(requirement, "service_desc", {}), "code"),
                    "service_type_code": safe_get(safe_get(requirement, "service_type", {}), "code"),
                    "remark_keywords": _extract_remark_keywords(requirement),
                },
                "suggestion": {
                    "rule_type": "risk_floor",
                    "risk_level_floor": "medium",
                    "must_review_fields": ["risk_rows", "warnings", "review_focus"],
                },
                "confidence_score": confidence,
                "confidence": confidence_from_score(confidence),
                "status": "pending_review",
            }
        )

    if "MISSING_DIMENSION" in tag_codes:
        confidence = 0.72
        results.append(
            {
                "candidate_rule_id": "CR-REPORT-001",
                "trigger": {
                    "business_type": safe_get(context, "business_type"),
                    "ship_type": safe_get(context, "ship_type"),
                },
                "suggestion": {
                    "rule_type": "required_dimension",
                    "must_include_sections": [
                        "风险提示",
                        "设备/备件需求",
                        "审核关注点"
                    ],
                },
                "confidence_score": confidence,
                "confidence": confidence_from_score(confidence),
                "status": "pending_review",
            }
        )

    if "MISSING_RECOMMENDATION" in tag_codes:
        confidence = 0.70
        results.append(
            {
                "candidate_rule_id": "CR-RECOMMEND-001",
                "trigger": {
                    "business_type": safe_get(context, "business_type"),
                    "remark_keywords": _extract_remark_keywords(requirement),
                },
                "suggestion": {
                    "rule_type": "recommendation_enrichment",
                    "must_include_fields": ["suggested_action", "review_focus"],
                },
                "confidence_score": confidence,
                "confidence": confidence_from_score(confidence),
                "status": "pending_review",
            }
        )

    return results