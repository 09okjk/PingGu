from typing import Any, Dict, List


CUSTOMER_HINTS = [
    "客户提供",
    "客户自备",
    "客户已有",
    "自备",
    "已有备件",
    "无需我方提供",
    "客户有备件",
]

PROVIDER_HINTS = [
    "我方提供",
    "需我方提供",
    "由我方提供",
    "需要我方设备",
    "需要我方备件",
]

SPARE_PART_KEYWORDS = [
    "备件",
    "阀件",
    "专用备件包",
    "检测设备",
    "专用设备",
    "更换件",
]


def build_spare_parts_or_equipment(
    requirement: Dict[str, Any],
    history_cases: List[Dict[str, Any]],
    warnings: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    remark = str(requirement.get("remark", "") or "")

    result = {
        "customer_provided": [],
        "provider_provided": [],
        "to_be_confirmed": [],
    }

    # Step 1: 当前需求优先
    if _contains_any(remark, CUSTOMER_HINTS):
        result["customer_provided"].append(
            {
                "item_name": _extract_candidate_name(remark),
                "confidence": "medium",
                "source": ["s5_requirement"],
                "notes": ["根据当前需求备注识别为客户提供。"],
            }
        )
        return result

    if _contains_any(remark, PROVIDER_HINTS):
        result["provider_provided"].append(
            {
                "item_name": _extract_candidate_name(remark),
                "confidence": "medium",
                "source": ["s5_requirement"],
                "notes": ["根据当前需求备注识别为我方提供。"],
            }
        )
        return result

    # Step 2: 历史案例弱参考
    history_hits = _history_candidate_items(history_cases)

    if history_hits:
        for item in history_hits[:3]:
            result["to_be_confirmed"].append(
                {
                    "item_name": item["item_name"],
                    "confidence": "low",
                    "source": item["source"],
                    "notes": ["历史案例存在相关项，但当前需求未明确归属。"],
                }
            )
    else:
        result["to_be_confirmed"].append(
            {
                "item_name": "设备/备件需求",
                "confidence": "low",
                "source": ["manual_placeholder"],
                "notes": ["当前无充分依据判断设备/备件归属，建议人工确认。"],
            }
        )

    warnings.append(
        {
            "code": "SPARE_PARTS_NEED_UNCLEAR",
            "message": "设备/备件归属缺乏明确依据，建议人���确认。",
            "severity": "high",
        }
    )

    return result


def _contains_any(text: str, hints: List[str]) -> bool:
    return any(hint in text for hint in hints)


def _extract_candidate_name(text: str) -> str:
    for keyword in SPARE_PART_KEYWORDS:
        if keyword in text:
            return keyword
    return "设备/备件（具体项待补充）"


def _history_candidate_items(history_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    for case in history_cases:
        case_id = case.get("case_id", "unknown")

        for collection_name in ["materials", "special_tools", "tools"]:
            items = case.get(collection_name, []) or []
            for item in items:
                item_name = item.get("toolName", "")
                if any(keyword in str(item_name) for keyword in SPARE_PART_KEYWORDS):
                    results.append(
                        {
                            "item_name": item_name,
                            "source": [f"s1_history_case:{case_id}"],
                        }
                    )

    unique = []
    seen = set()
    for item in results:
        key = item["item_name"]
        if key not in seen:
            unique.append(item)
            seen.add(key)

    return unique