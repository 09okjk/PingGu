from typing import Any, Dict, List


def build_totals(
    requirement: Dict[str, Any],
    assessment_result: Dict[str, Any],
    task_rows: List[Dict[str, Any]],
    warnings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    location_type = (requirement.get("service_location_type") or {}).get("name", "")
    is_voyage_repair = location_type == "港口"

    if not location_type:
        warnings.append(
            {
                "code": "SERVICE_LOCATION_TYPE_MISSING",
                "message": "服务地点类型缺失，是否航修结果稳定性不足。",
                "severity": "high",
            }
        )

    manpower_result = assessment_result.get("manpower_result", {}) or {}
    workhour_results = assessment_result.get("workhour_results", []) or []

    total_hours = None
    total_hours_conf = "low"
    total_hours_source = []

    if workhour_results:
        sorted_hours = sorted(
            [x for x in workhour_results if isinstance(x.get("suggested_hours"), (int, float))],
            key=lambda x: x.get("suggested_hours", 0),
            reverse=True,
        )
        if sorted_hours:
            selected = sorted_hours[0]
            total_hours = selected.get("suggested_hours")
            total_hours_conf = selected.get("confidence", "low")
            total_hours_source = [f"s2_workhour:{selected.get('task_tag', 'unknown')}"]
        else:
            warnings.append(
                {
                    "code": "TOTAL_HOURS_MISSING",
                    "message": "S2 工时结果存在，但未提取到有效总小时数。",
                    "severity": "medium",
                }
            )
    else:
        warnings.append(
            {
                "code": "NO_WORKHOUR_RESULTS",
                "message": "缺少 S2 工时推理结果，总小时数字段稳定性不足。",
                "severity": "high",
            }
        )

    total_persons_value = manpower_result.get("total_persons")
    if total_persons_value is None:
        warnings.append(
            {
                "code": "NO_MANPOWER_RESULT",
                "message": "缺少 S2 人数推理结果，总人数稳定性不足。",
                "severity": "high",
            }
        )

    return {
        "is_voyage_repair": {
            "value": is_voyage_repair,
            "confidence": "high" if location_type else "low",
            "source": ["s5_service_location_type"],
        },
        "total_hours": {
            "value": total_hours,
            "confidence": total_hours_conf,
            "source": total_hours_source,
        },
        "total_persons": {
            "value": total_persons_value,
            "confidence": manpower_result.get("confidence", "low"),
            "source": ["s2_manpower"],
        },
        "explanation": "总小时数表示整体施工总时长；总人数表示理论最小所需人数，并非各任务人数直接相加。",
    }