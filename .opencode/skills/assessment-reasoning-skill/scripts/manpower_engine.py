import re
from typing import Any, Dict, List, Tuple

from models import ManpowerResult


LEVEL_ORDER = {
    "T6": 6, "T5": 5, "T4": 4, "T3": 3, "T2": 2, "T1": 1,
    "P6": 6, "P5": 5, "P4": 4, "P3": 3, "P2": 2, "P1": 1
}


def extract_level_code(level_name: str) -> str:
    if not level_name:
        return ""
    match = re.search(r"\((T\d|P\d)\)", level_name)
    if match:
        return match.group(1)
    return ""


def estimate_manpower(
    history_cases: List[Dict[str, Any]],
    manpower_rules: Dict[str, Any],
) -> Dict[str, Any]:
    global_rules = manpower_rules.get("global_rules", {})
    allow_serial_reuse = bool(global_rules.get("allow_serial_reuse", True))
    higher_level_can_cover = bool(global_rules.get("higher_level_can_cover_lower_level", True))

    personnel = []
    for case in history_cases:
        personnel.extend(case.get("personnel", []))

    if not personnel:
        return ManpowerResult(
            total_persons=1,
            confidence="low",
            basis=["fallback:no_personnel_history"],
            explanation="缺少历史人员明细，当前返回兜底人数 1，需人工确认。"
        ).to_dict()

    grouped: Dict[str, List[Tuple[str, int]]] = {}
    for item in personnel:
        work_type = item.get("work_type_name", "未知工种")
        level_name = item.get("job_level_name", "")
        qty = int(item.get("quantity", 1) or 1)
        level_code = extract_level_code(level_name)

        grouped.setdefault(work_type, []).append((level_code, qty))

    total_persons = 0
    for work_type, items in grouped.items():
        if not allow_serial_reuse:
            total_persons += sum(qty for _, qty in items)
            continue

        if not higher_level_can_cover:
            total_persons += max(qty for _, qty in items)
            continue

        max_qty = max(qty for _, qty in items)
        total_persons += max_qty

    confidence = "medium" if personnel else "low"

    return ManpowerResult(
        total_persons=total_persons,
        confidence=confidence,
        basis=[
            f"serial_reuse:{str(allow_serial_reuse).lower()}",
            f"job_level_cover:{str(higher_level_can_cover).lower()}",
        ],
        explanation=f"根据当前历史任务参考与简化串行复用规则，理论最小总人数为 {total_persons}。"
    ).to_dict()