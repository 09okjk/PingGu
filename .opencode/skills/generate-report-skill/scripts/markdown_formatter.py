from typing import Any, Dict, List, Optional


def format_report_markdown(report: Dict[str, Any]) -> str:
    """
    将 S6 报告数据转换为 Markdown 格式，供工务人员直接阅读。
    报告结构：
    - 板块一：项目信息
    - 板块二：服务评估
    """
    lines = []

    lines.append("# 智能评估报告")
    lines.append("")

    # 板块一：项目信息
    lines.append("## 项目信息")
    lines.append("")
    lines.extend(_build_project_info_section(report.get("summary", {})))

    # 板块二：服务评估
    lines.append("## 服务评估")
    lines.append("")
    lines.extend(
        _build_risk_section(report.get("report_table", {}).get("risk_rows", []))
    )
    lines.extend(
        _build_task_section(report.get("report_table", {}).get("task_rows", []))
    )
    lines.extend(
        _build_workforce_section(report.get("report_table", {}).get("task_rows", []))
    )
    lines.extend(
        _build_summary_totals_section(report.get("report_table", {}).get("totals", {}))
    )
    lines.extend(
        _build_resources_section(
            report.get("report_table", {}).get("tool_rows", []),
            report.get("report_table", {}).get("material_rows", []),
            report.get("report_table", {}).get("special_tool_rows", []),
            report.get("report_table", {}).get("spare_parts_or_equipment", {}),
        )
    )
    lines.extend(
        _build_review_focus_section(
            report.get("review_focus", []), report.get("warnings", [])
        )
    )

    return "\n".join(lines)


def _build_project_info_section(summary: Dict[str, Any]) -> List[str]:
    """板块一：项目信息"""
    lines = []

    if not summary:
        lines.append("*暂无项目信息*")
        lines.append("")
        return lines

    def get_value(field: str, default: str = "-") -> str:
        val = summary.get(field)
        if val is None:
            return default
        if isinstance(val, dict):
            return val.get("name", default) or default
        return str(val) if val != "" else default

    lines.append("| 字段 | 内容 |")
    lines.append("|------|------|")
    lines.append(f"| 业务归口 | {get_value('business_type')} |")
    lines.append(f"| 服务描述 | {get_value('service_desc')} |")
    lines.append(f"| 服务类型 | {get_value('service_type')} |")
    lines.append(f"| 服务地点 | {get_value('service_location_type')} |")
    lines.append(f"| 所属设备名称 | {get_value('equipment_name')} |")
    lines.append(f"| 所属设备型号 | {get_value('equipment_model')} |")
    lines.append(f"| 所属设备厂家 | {summary.get('equipment_manufacturer') or '-'} |")
    lines.append(
        f"| 服务设备数量 | {summary.get('equipment_quantity') if summary.get('equipment_quantity') is not None else '-'} |"
    )
    lines.append(f"| 服务设备计量单位 | {get_value('equipment_unit')} |")

    remark = summary.get("remark")
    lines.append(f"| 备注 | {remark if remark else '-'} |")

    requirement_detail = summary.get("requirement_detail")
    lines.append(f"| 需求详情 | {requirement_detail if requirement_detail else '无'} |")

    lines.append("")
    return lines


def _build_risk_section(risk_rows: List[Dict[str, Any]]) -> List[str]:
    """4.1 风险提示"""
    lines = []
    lines.append("### 风险提示")
    lines.append("")

    if not risk_rows:
        lines.append("*暂无风险项*")
        lines.append("")
        return lines

    lines.append("| 风险等级 | 风险名称 | 说明 | 建议措施 | 置信度 |")
    lines.append("|----------|----------|------|----------|--------|")

    for risk in risk_rows:
        level = _format_risk_level(risk.get("risk_level", ""))
        name = risk.get("risk_name", "-")
        desc = risk.get("description", "-")
        action = risk.get("suggested_action", "-")
        conf = _format_confidence(risk.get("confidence", ""))

        lines.append(f"| {level} | {name} | {desc} | {action} | {conf} |")

    lines.append("")
    return lines


def _build_task_section(task_rows: List[Dict[str, Any]]) -> List[str]:
    """4.2 施工任务"""
    lines = []
    lines.append("### 施工任务")
    lines.append("")

    if not task_rows:
        lines.append("*暂无任务项*")
        lines.append("")
        return lines

    for idx, task in enumerate(task_rows, 1):
        task_name = task.get("task_name", f"任务{idx}")
        task_desc = task.get("task_description", "")

        lines.append(f"**任务 {idx}**: {task_name}")
        lines.append("")
        if task_desc:
            lines.append(f"{task_desc}")
            lines.append("")

    return lines


def _build_workforce_section(task_rows: List[Dict[str, Any]]) -> List[str]:
    """4.3 施工人数及工时（详细）"""
    lines = []
    lines.append("### 施工人数及工时")
    lines.append("")

    if not task_rows:
        lines.append("*暂无施工人数及工时信息*")
        lines.append("")
        return lines

    for idx, task in enumerate(task_rows, 1):
        work_items = task.get("work_items", [])
        if not work_items:
            continue

        lines.append(f"**任务 {idx}**: {task.get('task_name', f'任务{idx}')}")
        lines.append("")
        lines.append(
            "| 详细工作内容 | 单位 | 数量 | 工种 | 职级 | 人数 | 单人工时 | 置信度 |"
        )
        lines.append(
            "|--------------|------|------|------|------|------|----------|--------|"
        )

        for item in work_items:
            desc = item.get("description", "-")
            unit = item.get("unit", {}).get("name", "-") if item.get("unit") else "-"
            quantity = item.get("quantity", "-")
            work_type = (
                item.get("work_type", {}).get("name", "-")
                if item.get("work_type")
                else "-"
            )
            job_level = (
                item.get("job_level", {}).get("name", "-")
                if item.get("job_level")
                else "-"
            )
            persons = item.get("persons", "-")
            hours = item.get("hours", "-")
            conf = _format_confidence(item.get("confidence", ""))

            lines.append(
                f"| {desc} | {unit} | {quantity} | {work_type} | {job_level} | {persons} | {hours} | {conf} |"
            )

        lines.append("")

    return lines


def _build_summary_totals_section(totals: Dict[str, Any]) -> List[str]:
    """4.4 综述"""
    lines = []
    lines.append("### 综述")
    lines.append("")

    if not totals:
        lines.append("*暂无综述信息*")
        lines.append("")
        return lines

    is_voyage = totals.get("is_voyage_repair", {})
    voyage_val = "是" if is_voyage.get("value", False) else "否"
    voyage_conf = _format_confidence(is_voyage.get("confidence", ""))

    total_hours = totals.get("total_hours", {})
    hours_val = total_hours.get("value", "-")
    hours_conf = _format_confidence(total_hours.get("confidence", ""))

    total_persons = totals.get("total_persons", {})
    persons_val = total_persons.get("value", "-")
    persons_conf = _format_confidence(total_persons.get("confidence", ""))

    lines.append("| 项目 | 数值 | 置信度 |")
    lines.append("|------|------|--------|")
    lines.append(f"| 是否航修 | {voyage_val} | {voyage_conf} |")
    lines.append(f"| 总小时数 | {hours_val} 小时 | {hours_conf} |")
    lines.append(f"| 总人数 | {persons_val} 人 | {persons_conf} |")

    explanation = totals.get("explanation", "")
    if explanation:
        lines.append("")
        lines.append(f"> {explanation}")

    lines.append("")
    return lines


def _build_resources_section(
    tool_rows: List[Dict[str, Any]],
    material_rows: List[Dict[str, Any]],
    special_tool_rows: List[Dict[str, Any]],
    spare_parts: Dict[str, List[Dict[str, Any]]],
) -> List[str]:
    """4.5-4.8 资源需求：工具、耗材、专用工具、设备/备件"""
    lines = []
    lines.append("### 资源需求")
    lines.append("")

    # 4.5 需要工具
    lines.append("#### 需要工具")
    lines.append("")
    if tool_rows:
        lines.append("| 工具名称 | 工具类型 | 计量单位 | 需要数量 |")
        lines.append("|----------|----------|----------|----------|")
        for tool in tool_rows:
            name = tool.get("item_name", "-")
            tool_type = _format_tool_type(tool.get("item_type_code"))
            unit = tool.get("unit", {}).get("name", "-") if tool.get("unit") else "-"
            qty = tool.get("quantity", "-")
            lines.append(f"| {name} | {tool_type} | {unit} | {qty} |")
        lines.append("")
    else:
        lines.append("*无需要工具*")
        lines.append("")

    # 4.6 耗材
    lines.append("#### 耗材")
    lines.append("")
    if material_rows:
        lines.append("| 耗材名称 | 耗材型号 | 计量单位 | 数量 |")
        lines.append("|----------|----------|----------|------|")
        for mat in material_rows:
            name = mat.get("item_name", "-")
            model = mat.get("item_model", "-") or "-"
            unit = mat.get("unit", {}).get("name", "-") if mat.get("unit") else "-"
            qty = mat.get("quantity", "-")
            lines.append(f"| {name} | {model} | {unit} | {qty} |")
        lines.append("")
    else:
        lines.append("*无耗材需求*")
        lines.append("")

    # 4.7 专用工具
    lines.append("#### 专用工具")
    lines.append("")
    if special_tool_rows:
        lines.append("| 专用工具名称 | 专用工具型号 | 计量单位 | 数量 |")
        lines.append("|--------------|--------------|----------|------|")
        for tool in special_tool_rows:
            name = tool.get("item_name", "-")
            model = tool.get("item_model", "-") or "-"
            unit = tool.get("unit", {}).get("name", "-") if tool.get("unit") else "-"
            qty = tool.get("quantity", "-")
            lines.append(f"| {name} | {model} | {unit} | {qty} |")
        lines.append("")
    else:
        lines.append("*无专用工具需求*")
        lines.append("")

    # 4.8 设备/备件需求
    lines.append("#### 设备/备件需求")
    lines.append("")
    if not spare_parts:
        lines.append("*暂无设备/备件需求信息*")
        lines.append("")
        return lines

    customer_provided = spare_parts.get("customer_provided", [])
    provider_provided = spare_parts.get("provider_provided", [])
    to_be_confirmed = spare_parts.get("to_be_confirmed", [])

    if customer_provided:
        lines.append("**客户提供**")
        for item in customer_provided:
            lines.append(f"- {item.get('item_name', '-')}")
        lines.append("")

    if provider_provided:
        lines.append("**我方提供**")
        for item in provider_provided:
            lines.append(f"- {item.get('item_name', '-')}")
        lines.append("")

    if to_be_confirmed:
        lines.append("**待确认**")
        for item in to_be_confirmed:
            lines.append(f"- {item.get('item_name', '-')}")
        lines.append("")

    if not (customer_provided or provider_provided or to_be_confirmed):
        lines.append("*暂无设备/备件需求*")
        lines.append("")

    return lines


def _format_tool_type(tool_type_no: Any) -> str:
    """转换工具类型编号为中文"""
    mapping = {
        1: "手动工具",
        2: "电动工具",
        3: "气动工具",
        4: "液压工具",
        5: "测量工具",
        6: "起重工具",
        7: "焊接工具",
        8: "其他",
    }
    if isinstance(tool_type_no, int) and tool_type_no in mapping:
        return mapping[tool_type_no]
    return str(tool_type_no) if tool_type_no else "-"

    customer_provided = spare_parts.get("customer_provided", [])
    provider_provided = spare_parts.get("provider_provided", [])
    to_be_confirmed = spare_parts.get("to_be_confirmed", [])

    if customer_provided:
        lines.append("**客户提供**")
        for item in customer_provided:
            lines.append(f"- {item.get('item_name', '-')}")
        lines.append("")

    if provider_provided:
        lines.append("**我方提供**")
        for item in provider_provided:
            lines.append(f"- {item.get('item_name', '-')}")
        lines.append("")

    if to_be_confirmed:
        lines.append("**待确认**")
        for item in to_be_confirmed:
            lines.append(f"- {item.get('item_name', '-')}")
        lines.append("")

    if not (customer_provided or provider_provided or to_be_confirmed):
        lines.append("*暂无设备/备件需求*")
        lines.append("")

    return lines


def _build_review_focus_section(
    review_focus: List[str], warnings: List[Dict[str, Any]]
) -> List[str]:
    lines = []
    lines.append("### 审核重点")
    lines.append("")

    if warnings:
        lines.append("#### ⚠️ 警告提示")
        lines.append("")
        for w in warnings:
            severity = w.get("severity", "medium")
            message = w.get("message", "")
            icon = "🔴" if severity == "high" else "⚠️"
            lines.append(f"- {icon} {message}")
        lines.append("")

    if review_focus:
        lines.append("#### 重点关注")
        lines.append("")
        for focus in review_focus:
            lines.append(f"- {focus}")
        lines.append("")

    if not (warnings or review_focus):
        lines.append("*暂无审核重点*")
        lines.append("")

    return lines


def _format_risk_level(level: str) -> str:
    mapping = {"high": "🔴 高", "medium": "🟡 中", "low": "🟢 低"}
    return mapping.get(level, level)


def _format_confidence(confidence: str) -> str:
    mapping = {"high": "✓ 高", "medium": "⚠ 中", "low": "⚡ 低"}
    return mapping.get(confidence, confidence)
