import re
from typing import Any, Dict, List, Optional, Tuple

from models import ManpowerResult


def extract_level_code(level_name: str) -> str:
    """
    从职级名称中提取职级代码
    支持格式：
    - ET1, ET2, ..., ET6 (电气工程师)
    - MT1, MT2, ..., MT6 (轮机工程师)
    - EP1, EP2, ..., EP6 (电工)
    - FP1, FP2, ..., FP6 (轮机钳工)
    - WP1, WP2, ..., WP6 (焊工)
    - PP1, PP2, ..., PP6 (管工)
    - HT1, HT2, ..., HT6 (液压工程师)
    - HP1, HP2, ..., HP6 (液压钳工)
    - D1, D2, ..., D20 (设计师类)
    - T1-T6 (传统工程师职级)
    - P1-P6 (传统工职级)
    - 初级，中级，高级，资深 (软件/IT 类)
    """
    if not level_name:
        return ""
    
    # 直接就是职级代码的情况 (如 "ET1", "D5")
    match = re.match(r"^([A-Z]{1,2}\d{1,2})$", level_name.strip())
    if match:
        return match.group(1)
    
    # 括号中的职级代码 (如 "工程师 (T5)")
    match = re.search(r"\(([A-Z]{1,2}\d{1,2})\)", level_name)
    if match:
        return match.group(1)
    
    # 中文职级 (初级，中级，高级，资深)
    if "资深" in level_name:
        return "ZS"
    if "高级" in level_name:
        return "GJ"
    if "中级" in level_name:
        return "ZJ"
    if "初级" in level_name:
        return "CJ"
    
    return ""


def get_level_order(level_code: str) -> int:
    """
    获取职级代码的级别顺序（数字越小级别越低）
    从数据库 job_levels 表中读取，这里提供兜底逻辑
    """
    if not level_code:
        return 0
    
    # 字母 + 数字格式 (如 ET1, D5)
    match = re.match(r"([A-Z]+)(\d+)", level_code)
    if match:
        prefix = match.group(1)
        num = int(match.group(2))
        return num
    
    # 中文职级
    order_map = {
        "CJ": 1,  # 初级
        "ZJ": 2,  # 中级
        "GJ": 3,  # 高级
        "ZS": 4,  # 资深
    }
    return order_map.get(level_code, 0)


def can_higher_cover_lower(higher_code: str, lower_code: str, level_cover_rules: List[Dict[str, Any]]) -> bool:
    """
    判断高职级是否可以覆盖低职级
    优先使用数据库规则，其次使用级别顺序比较
    """
    if not higher_code or not lower_code:
        return False
    
    # 相同职级可以直接覆盖
    if higher_code == lower_code:
        return True
    
    # 检查覆盖规则
    for rule in level_cover_rules:
        if (rule.get("higher_level_code") == higher_code and 
            rule.get("lower_level_code") == lower_code and
            rule.get("is_active", True)):
            return True
    
    # 如果没有明确规则，使用级别顺序判断
    higher_order = get_level_order(higher_code)
    lower_order = get_level_order(lower_code)
    
    # 数字越大级别越高
    return higher_order > lower_order


def estimate_manpower(
    history_cases: List[Dict[str, Any]],
    manpower_rules: Dict[str, Any],
) -> Dict[str, Any]:
    global_rules = manpower_rules.get("global_rules", {})
    allow_serial_reuse = bool(global_rules.get("allow_serial_reuse", True))
    higher_level_can_cover = bool(global_rules.get("higher_level_can_cover_lower_level", True))
    level_cover_rules = manpower_rules.get("level_cover_rules", [])

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

        # 使用职级覆盖规则判断是否可以复用
        # 如果所有职级之间可以相互覆盖（高职级覆盖低职级），则取最大人数
        # 否则需要分别计算
        level_codes = [lc for lc, _ in items]
        can_all_cover = True
        
        if len(level_codes) > 1:
            # 检查是否所有高职级都可以覆盖低职级
            for i in range(len(level_codes)):
                for j in range(i + 1, len(level_codes)):
                    if not can_higher_cover_lower(level_codes[i], level_codes[j], level_cover_rules) and \
                       not can_higher_cover_lower(level_codes[j], level_codes[i], level_cover_rules):
                        can_all_cover = False
                        break
                if not can_all_cover:
                    break
        
        if can_all_cover:
            max_qty = max(qty for _, qty in items)
            total_persons += max_qty
        else:
            # 如果不能相互覆盖，需要累加
            total_persons += sum(qty for _, qty in items)

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