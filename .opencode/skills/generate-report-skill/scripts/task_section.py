from collections import Counter
from typing import Any, Dict, List, Tuple


def build_task_rows(
    requirement: Dict[str, Any],
    history_cases: List[Dict[str, Any]],
    assessment_result: Dict[str, Any],
    warnings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    workhour_results = assessment_result.get("workhour_results", []) or []
    total_cases = len(history_cases)

    if total_cases == 0:
        warnings.append(
            {
                "code": "NO_HISTORY_CASES",
                "message": "未提供历史案例，任务结构将退化为低置信粗粒度输出。",
                "severity": "high",
            }
        )

    # Step 1: 聚合历史案例中的任务骨架
    task_occurrence: Counter[str] = Counter()
    task_personnel_map: Dict[str, List[Dict[str, Any]]] = {}
    task_case_sources: Dict[str, List[str]] = {}
    raw_task_names: List[str] = []

    for case in history_cases:
        case_id = case.get("case_id", "unknown")
        case_task_desc = case.get("task_description") or ""

        personnel = case.get("personnel", []) or []
        case_seen_tasks = set()

        for person in personnel:
            task_name = (
                person.get("task_desc")
                or case_task_desc
                or "施工任务"
            )
            task_name = str(task_name).strip() or "施工任务"
            raw_task_names.append(task_name)

            if task_name not in case_seen_tasks:
                task_occurrence[task_name] += 1
                case_seen_tasks.add(task_name)

            if task_name not in task_personnel_map:
                task_personnel_map[task_name] = []
            task_personnel_map[task_name].append(
                {
                    "case_id": case_id,
                    "work_type_code": person.get("work_type_code", ""),
                    "work_type_name": person.get("work_type_name", ""),
                    "job_level_code": person.get("job_level_code", ""),
                    "job_level_name": person.get("job_level_name", ""),
                    "quantity": person.get("quantity"),
                    "construction_hour": person.get("construction_hour"),
                }
            )
            task_case_sources.setdefault(task_name, []).append(f"s1_history_case:{case_id}")

        if not personnel and case_task_desc:
            task_name = str(case_task_desc).strip() or "施工任务"
            raw_task_names.append(task_name)
            task_occurrence[task_name] += 1
            task_personnel_map.setdefault(task_name, [])
            task_case_sources.setdefault(task_name, []).append(f"s1_history_case:{case_id}")

    # Step 2: 若历史任务完全缺失，则回退到 S2 / requirement
    if not task_occurrence:
        fallback_name = (
            (workhour_results[0].get("task_tag") if workhour_results else None)
            or requirement.get("service_desc", {}).get("name")
            or "施工任务"
        )
        warnings.append(
            {
                "code": "TASK_STRUCTURE_FALLBACK",
                "message": "历史任务结构不足，已退化为粗粒度任务输出。",
                "severity": "medium",
            }
        )
        return [
            {
                "task_id": "task-001",
                "task_name": fallback_name,
                "task_description": "当前历史任务结构不足，已退化为粗粒度任务。",
                "quantity": requirement.get("equipment_quantity"),
                "unit": requirement.get("equipment_unit", {}),
                "work_items": [],
                "suggested_hours": _fallback_workhour(workhour_results),
                "confidence": "low",
                "source": ["s2_reasoning"] if workhour_results else ["manual_placeholder"],
                "notes": ["建议工务人员人工确认任务拆分。"],
            }
        ]

    # Step 3: 根据任务出现频次排序
    sorted_task_names = sorted(
        task_occurrence.keys(),
        key=lambda name: (-task_occurrence[name], name),
    )

    # Step 4: 任务分歧提示
    if len(sorted_task_names) >= 3 and total_cases > 0:
        top_count = task_occurrence[sorted_task_names[0]]
        if top_count / total_cases < 0.5:
            warnings.append(
                {
                    "code": "TASK_STRUCTURE_DIVERGENT",
                    "message": "历史案例中的任务骨架差异较大，任务组织结果稳定性一般。",
                    "severity": "medium",
                }
            )

    rows: List[Dict[str, Any]] = []

    # Step 5: 构建 task rows
    for idx, task_name in enumerate(sorted_task_names, start=1):
        occurrence = task_occurrence[task_name]
        source_list = list(dict.fromkeys(task_case_sources.get(task_name, [])))
        work_items = _merge_work_items(task_personnel_map.get(task_name, []))
        task_confidence = _task_confidence(occurrence, total_cases)

        matched_workhour = _match_workhour(task_name, workhour_results)

        row = {
            "task_id": f"task-{idx:03d}",
            "task_name": task_name,
            "task_description": "依据历史相似案例整理的施工任务。",
            "quantity": requirement.get("equipment_quantity"),
            "unit": requirement.get("equipment_unit", {}),
            "work_items": work_items,
            "suggested_hours": matched_workhour,
            "confidence": task_confidence,
            "source": source_list + matched_workhour.get("source", []),
            "notes": [],
        }

        if not work_items:
            row["notes"].append("当前任务缺少稳定的人力结构参考。")

        rows.append(row)

    # Step 6: 若有工时结果未匹配到任务，补充 warning
    unmatched_workhours = []
    for wh in workhour_results:
        task_tag = (wh.get("task_tag") or "").strip()
        if not task_tag:
            continue
        if not any(_task_match(task_tag, row["task_name"]) for row in rows):
            unmatched_workhours.append(task_tag)

    if unmatched_workhours:
        warnings.append(
            {
                "code": "WORKHOUR_TASK_UNMATCHED",
                "message": f"S2 工时结果中有任务未与 S6 任务骨架精确对齐：{', '.join(unmatched_workhours)}",
                "severity": "low",
            }
        )

    return rows


def _merge_work_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for item in items:
        key = (
            item.get("work_type_code", ""),
            item.get("job_level_code", ""),
        )
        if key not in grouped:
            grouped[key] = {
                "work_type": {
                    "code": item.get("work_type_code", ""),
                    "name": item.get("work_type_name", ""),
                },
                "job_level": {
                    "code": item.get("job_level_code", ""),
                    "name": item.get("job_level_name", ""),
                },
                "persons_values": [],
                "hours_values": [],
                "source": [],
            }

        grouped[key]["persons_values"].append(item.get("quantity"))
        grouped[key]["hours_values"].append(item.get("construction_hour"))
        grouped[key]["source"].append(f"s1_history_case:{item.get('case_id', 'unknown')}")

    rows = []
    for _, value in grouped.items():
        rows.append(
            {
                "work_type": value["work_type"],
                "job_level": value["job_level"],
                "persons": _pick_median_number(value["persons_values"]),
                "hours": _pick_median_number(value["hours_values"]),
                "confidence": _work_item_confidence(len(value["source"])),
                "source": list(dict.fromkeys(value["source"])),
            }
        )

    rows.sort(key=lambda x: (x["work_type"]["name"], x["job_level"]["name"]))
    return rows


def _task_confidence(occurrence: int, total_cases: int) -> str:
    if total_cases <= 0:
        return "low"
    ratio = occurrence / total_cases
    if ratio >= 0.6:
        return "high"
    if ratio >= 0.3:
        return "medium"
    return "low"


def _work_item_confidence(source_count: int) -> str:
    if source_count >= 3:
        return "high"
    if source_count >= 2:
        return "medium"
    return "low"


def _match_workhour(task_name: str, workhour_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    for item in workhour_results:
        task_tag = (item.get("task_tag") or "").strip()
        if _task_match(task_name, task_tag):
            return {
                "value": item.get("suggested_hours"),
                "confidence": item.get("confidence", "low"),
                "source": _workhour_sources(item),
            }

    if workhour_results:
        first = workhour_results[0]
        return {
            "value": first.get("suggested_hours"),
            "confidence": "low",
            "source": _workhour_sources(first),
        }

    return {
        "value": None,
        "confidence": "low",
        "source": [],
    }


def _fallback_workhour(workhour_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not workhour_results:
        return {"value": None, "confidence": "low", "source": []}
    first = workhour_results[0]
    return {
        "value": first.get("suggested_hours"),
        "confidence": first.get("confidence", "low"),
        "source": _workhour_sources(first),
    }


def _workhour_sources(item: Dict[str, Any]) -> List[str]:
    task_tag = item.get("task_tag", "unknown")
    sources = [f"s2_workhour:{task_tag}"]
    for basis in item.get("basis", []) or []:
        sources.append(f"s2_workhour_basis:{basis}")
    return list(dict.fromkeys(sources))


def _task_match(a: str, b: str) -> bool:
    a = (a or "").strip()
    b = (b or "").strip()
    if not a or not b:
        return False
    return a == b or a in b or b in a


def _pick_median_number(values: List[Any]) -> Any:
    clean = [v for v in values if isinstance(v, (int, float))]
    if not clean:
        return None
    clean.sort()
    return clean[len(clean) // 2]