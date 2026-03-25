from typing import Any, Dict, List

from utils import confidence_from_score, normalize_text, safe_get


def mine_report_preferences(
    context: Dict[str, Any],
    artifacts: Dict[str, Any],
    revision_diff: List[Dict[str, Any]],
    feedback_tags: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Mine report preference candidates from revision patterns."""
    tag_codes = {normalize_text(item.get("tag_code")) for item in feedback_tags}
    results: List[Dict[str, Any]] = []

    if "FORMAT_NOT_PRACTICAL" in tag_codes or "ORG_SPECIFIC_PREFERENCE" in tag_codes:
        confidence = 0.80
        results.append(
            {
                "preference_id": "PF-REPORT-001",
                "scenario": {
                    "business_type": safe_get(context, "business_type"),
                    "ship_type": safe_get(context, "ship_type"),
                },
                "required_sections": [
                    "风险提示",
                    "施工任务",
                    "总计",
                    "设备/备件需求",
                    "审核关注点"
                ],
                "expression_preference": "先结论后依据",
                "confidence_score": confidence,
                "confidence": confidence_from_score(confidence),
                "status": "pending_review",
            }
        )

    if "WRONG_TERMINOLOGY" in tag_codes or "UNCLEAR_EXPRESSION" in tag_codes:
        confidence = 0.68
        results.append(
            {
                "preference_id": "PF-WORDING-001",
                "scenario": {
                    "business_type": safe_get(context, "business_type"),
                },
                "required_sections": [],
                "expression_preference": "使用更业务化、更审核友好的表述",
                "confidence_score": confidence,
                "confidence": confidence_from_score(confidence),
                "status": "pending_review",
            }
        )

    if not results and len(revision_diff) >= 4:
        confidence = 0.55
        results.append(
            {
                "preference_id": "PF-GENERIC-001",
                "scenario": {
                    "business_type": safe_get(context, "business_type"),
                },
                "required_sections": ["审核关注点"],
                "expression_preference": "保留更多结构化审核提示",
                "confidence_score": confidence,
                "confidence": confidence_from_score(confidence),
                "status": "pending_review",
            }
        )

    return results