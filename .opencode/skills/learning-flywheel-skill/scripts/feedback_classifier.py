from typing import Any, Dict, List

from utils import confidence_from_score, normalize_text, safe_get


def _contains_any(text: str, keywords: List[str]) -> bool:
    """Case-insensitive keyword match."""
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _classify_by_field_path(field_path: str, before: Any, after: Any) -> List[Dict[str, Any]]:
    """Infer tags from changed field path and values."""
    tags: List[Dict[str, Any]] = []
    path_lower = field_path.lower()
    before_text = normalize_text(before).lower()
    after_text = normalize_text(after).lower()

    if "risk" in path_lower:
        if before_text in {"low", "medium"} and after_text in {"medium", "high"}:
            tags.append({"tag_code": "RISK_UNDER_ESTIMATED", "tag_confidence": 0.88})
        elif before_text in {"high", "medium"} and after_text in {"medium", "low"}:
            tags.append({"tag_code": "RISK_OVER_ESTIMATED", "tag_confidence": 0.88})

    if "hour" in path_lower or "workhour" in path_lower:
        try:
            before_num = float(before)
            after_num = float(after)
            if after_num > before_num:
                tags.append({"tag_code": "WORKHOUR_UNDER_ESTIMATED", "tag_confidence": 0.82})
            elif after_num < before_num:
                tags.append({"tag_code": "WORKHOUR_OVER_ESTIMATED", "tag_confidence": 0.82})
        except (TypeError, ValueError):
            pass

    if "person" in path_lower or "manpower" in path_lower:
        try:
            before_num = float(before)
            after_num = float(after)
            if after_num > before_num:
                tags.append({"tag_code": "MANPOWER_UNDER_ESTIMATED", "tag_confidence": 0.82})
            elif after_num < before_num:
                tags.append({"tag_code": "MANPOWER_OVER_ESTIMATED", "tag_confidence": 0.82})
        except (TypeError, ValueError):
            pass

    if any(key in path_lower for key in ["recommend", "suggested_action", "review_focus", "warning"]):
        if before in (None, "", []) and after not in (None, "", []):
            tags.append({"tag_code": "MISSING_RECOMMENDATION", "tag_confidence": 0.76})

    if any(key in path_lower for key in ["spare_parts", "equipment", "to_be_confirmed", "remark_summary"]):
        if before in (None, "", []) and after not in (None, "", []):
            tags.append({"tag_code": "MISSING_DIMENSION", "tag_confidence": 0.72})

    if _contains_any(path_lower, ["summary", "description", "expression", "wording"]):
        tags.append({"tag_code": "UNCLEAR_EXPRESSION", "tag_confidence": 0.60})

    return tags


def _classify_by_context(
    revision_diff: List[Dict[str, Any]],
    artifacts: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Infer tags using broader context."""
    tags: List[Dict[str, Any]] = []

    requirement = safe_get(artifacts, "requirement_json", {})
    history_cases = safe_get(artifacts, "history_cases_json", [])
    conversation_messages = safe_get(artifacts, "conversation_messages", [])

    if not safe_get(requirement, "service_type") or not safe_get(requirement, "equipment_model"):
        tags.append({"tag_code": "PARSE_INCOMPLETE", "tag_confidence": 0.58})

    if isinstance(history_cases, list) and len(history_cases) <= 1:
        tags.append({"tag_code": "RETRIEVAL_MISS", "tag_confidence": 0.55})

    conversation_text = " ".join(
        normalize_text(item.get("content"))
        for item in conversation_messages
        if isinstance(item, dict)
    ).lower()

    if _contains_any(conversation_text, ["术语", "表达", "不专业", "措辞"]):
        tags.append({"tag_code": "WRONG_TERMINOLOGY", "tag_confidence": 0.75})

    if _contains_any(conversation_text, ["格式", "不好用", "不方便", "表格", "顺序"]):
        tags.append({"tag_code": "FORMAT_NOT_PRACTICAL", "tag_confidence": 0.75})

    if _contains_any(conversation_text, ["部门要求", "公司要求", "习惯", "偏好", "必须体现"]):
        tags.append({"tag_code": "ORG_SPECIFIC_PREFERENCE", "tag_confidence": 0.80})

    if revision_diff and len(revision_diff) >= 5:
        tags.append({"tag_code": "MISSING_DIMENSION", "tag_confidence": 0.52})

    return tags


def classify_feedback(
    revision_diff: List[Dict[str, Any]],
    artifacts: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Classify feedback tags from diff and contextual artifacts."""
    tags: List[Dict[str, Any]] = []

    for item in revision_diff:
        tags.extend(
            _classify_by_field_path(
                field_path=normalize_text(item.get("field_path")),
                before=item.get("before"),
                after=item.get("after"),
            )
        )

    tags.extend(_classify_by_context(revision_diff, artifacts))

    merged: Dict[str, float] = {}
    for tag in tags:
        code = normalize_text(tag.get("tag_code"))
        confidence = float(tag.get("tag_confidence") or 0.5)
        if not code:
            continue
        merged[code] = max(merged.get(code, 0.0), confidence)

    result = []
    for code, score in sorted(merged.items(), key=lambda item: item[1], reverse=True):
        result.append(
            {
                "tag_code": code,
                "tag_confidence": round(score, 2),
                "confidence": confidence_from_score(score),
            }
        )
    return result