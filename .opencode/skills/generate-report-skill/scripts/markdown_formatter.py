from typing import Any, Dict, List, Optional


def format_report_markdown(report: Dict[str, Any]) -> str:
    """
    将 S6 报告数据转换为 Markdown 格式，供工务人员直接阅读。
    """
    lines = []

    lines.append("# 评估报告草稿")
    lines.append("")

    lines.extend(_build_summary_section(report.get("summary", {})))
    lines.extend(
        _build_risk_section(report.get("report_table", {}).get("risk_rows", []))
    )
    lines.extend(
        _build_task_section(report.get("report_table", {}).get("task_rows", []))
    )
    lines.extend(
        _build_totals_section(report.get("report_table", {}).get("totals", {}))
    )
    lines.extend(
        _build_tools_section(
            report.get("report_table", {}).get("tool_rows", []),
            report.get("report_table", {}).get("material_rows", []),
            report.get("report_table", {}).get("special_tool_rows", []),
        )
    )
    lines.extend(
        _build_spare_parts_section(
            report.get("report_table", {}).get("spare_parts_or_equipment", {})
        )
    )
    lines.extend(_build_confidence_section(report.get("confidence_summary", {})))
    lines.extend(
        _build_review_focus_section(
            report.get("review_focus", []), report.get("warnings", [])
        )
    )
    lines.extend(_build_learning_section(report.get("learning_summary", {})))

    return "\n".join(lines)


def _build_summary_section(summary: Dict[str, Any]) -> List[str]:
    lines = []
    lines.append("## 一、服务需求概要")
    lines.append("")

    if not summary:
        lines.append("*暂无概要信息*")
        lines.append("")
        return lines

    lines.append(f"- **业务归口**: {summary.get('business_type', {}).get('name', '-')}")
    lines.append(f"- **服务描述**: {summary.get('service_desc', {}).get('name', '-')}")
    lines.append(f"- **服务类型**: {summary.get('service_type', {}).get('name', '-')}")
    lines.append(
        f"- **服务地点**: {summary.get('service_location_type', {}).get('name', '-')}"
    )

    equipment = summary.get("equipment_name", {}).get("name", "-")
    model = summary.get("equipment_model", {}).get("name", "-")
    qty = summary.get("equipment_quantity", "-")
    unit = summary.get("equipment_unit", {}).get("name", "-")
    lines.append(f"- **设备信息**: {equipment} / {model} / {qty} {unit}")

    remark = summary.get("remark_summary", "")
    if remark:
        lines.append(f"- **备注说明**: {remark}")

    lines.append("")
    return lines


def _build_risk_section(risk_rows: List[Dict[str, Any]]) -> List[str]:
    lines = []
    lines.append("## 二、风险评估")
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
    lines = []
    lines.append("## 三、施工任务")
    lines.append("")

    if not task_rows:
        lines.append("*暂无任务项*")
        lines.append("")
        return lines

    for idx, task in enumerate(task_rows, 1):
        task_name = task.get("task_name", f"任务{idx}")
        task_desc = task.get("task_description", "")

        lines.append(f"### 任务 {idx}: {task_name}")
        lines.append("")
        if task_desc:
            lines.append(f"{task_desc}")
            lines.append("")

        work_items = task.get("work_items", [])
        if work_items:
            lines.append("| 工种 | 职级 | 人数 | 工时 | 置信度 |")
            lines.append("|------|------|------|------|--------|")

            for item in work_items:
                work_type = item.get("work_type", {}).get("name", "-")
                job_level = item.get("job_level", {}).get("name", "-")
                persons = item.get("persons", "-")
                hours = item.get("hours", "-")
                conf = _format_confidence(item.get("confidence", ""))

                lines.append(
                    f"| {work_type} | {job_level} | {persons} | {hours} | {conf} |"
                )

            lines.append("")

        suggested_hours = task.get("suggested_hours", {})
        if suggested_hours:
            hours_val = suggested_hours.get("value", "-")
            hours_conf = _format_confidence(suggested_hours.get("confidence", ""))
            lines.append(f"**建议工时**: {hours_val} 小时（{hours_conf}）")
            lines.append("")

    return lines


def _build_totals_section(totals: Dict[str, Any]) -> List[str]:
    lines = []
    lines.append("## 四、总计")
    lines.append("")

    if not totals:
        lines.append("*暂无总计信息*")
        lines.append("")
        return lines

    is_voyage = totals.get("is_voyage_repair", {})
    voyage_val = "是" if is_voyage.get("value", False) else "否"
    voyage_conf = _format_confidence(is_voyage.get("confidence", ""))
    lines.append(f"- **是否航修**: {voyage_val}（{voyage_conf}）")

    total_hours = totals.get("total_hours", {})
    hours_val = total_hours.get("value", "-")
    hours_conf = _format_confidence(total_hours.get("confidence", ""))
    lines.append(f"- **总工时**: {hours_val} 小时（{hours_conf}）")

    total_persons = totals.get("total_persons", {})
    persons_val = total_persons.get("value", "-")
    persons_conf = _format_confidence(total_persons.get("confidence", ""))
    lines.append(f"- **总人数**: {persons_val} 人（{persons_conf}）")

    explanation = totals.get("explanation", "")
    if explanation:
        lines.append("")
        lines.append(f"> {explanation}")

    lines.append("")
    return lines


def _build_tools_section(
    tool_rows: List[Dict[str, Any]],
    material_rows: List[Dict[str, Any]],
    special_tool_rows: List[Dict[str, Any]],
) -> List[str]:
    lines = []
    lines.append("## 五、工具与耗材")
    lines.append("")

    if tool_rows:
        lines.append("### 工具")
        lines.append("")
        lines.append("| 工具名称 | 型号 | 数量 | 单位 |")
        lines.append("|----------|------|------|------|")
        for tool in tool_rows:
            name = tool.get("toolName", "-")
            model = tool.get("model", "-")
            qty = tool.get("quantity", "-")
            unit = tool.get("unitMeasurement", {}).get("zhName", "-")
            lines.append(f"| {name} | {model} | {qty} | {unit} |")
        lines.append("")

    if material_rows:
        lines.append("### 耗材")
        lines.append("")
        lines.append("| 耗材名称 | 型号 | 数量 | 单位 |")
        lines.append("|----------|------|------|------|")
        for mat in material_rows:
            name = mat.get("toolName", "-")
            model = mat.get("model", "-")
            qty = mat.get("quantity", "-")
            unit = mat.get("unitMeasurement", {}).get("zhName", "-")
            lines.append(f"| {name} | {model} | {qty} | {unit} |")
        lines.append("")

    if special_tool_rows:
        lines.append("### 专用工具")
        lines.append("")
        lines.append("| 工具名称 | 型号 | 数量 | 单位 |")
        lines.append("|----------|------|------|------|")
        for tool in special_tool_rows:
            name = tool.get("toolName", "-")
            model = tool.get("model", "-")
            qty = tool.get("quantity", "-")
            unit = tool.get("unitMeasurement", {}).get("zhName", "-")
            lines.append(f"| {name} | {model} | {qty} | {unit} |")
        lines.append("")

    if not (tool_rows or material_rows or special_tool_rows):
        lines.append("*暂无工具与耗材信息*")
        lines.append("")

    return lines


def _build_spare_parts_section(
    spare_parts: Dict[str, List[Dict[str, Any]]],
) -> List[str]:
    lines = []
    lines.append("## 六、设备/备件需求")
    lines.append("")

    if not spare_parts:
        lines.append("*暂无设备/备件需求信息*")
        lines.append("")
        return lines

    customer_provided = spare_parts.get("customer_provided", [])
    provider_provided = spare_parts.get("provider_provided", [])
    to_be_confirmed = spare_parts.get("to_be_confirmed", [])

    if customer_provided:
        lines.append("### 客户提供")
        lines.append("")
        for item in customer_provided:
            lines.append(f"- {item.get('item_name', '-')}")
        lines.append("")

    if provider_provided:
        lines.append("### 我方提供")
        lines.append("")
        for item in provider_provided:
            lines.append(f"- {item.get('item_name', '-')}")
        lines.append("")

    if to_be_confirmed:
        lines.append("### 待确认")
        lines.append("")
        for item in to_be_confirmed:
            lines.append(f"- {item.get('item_name', '-')}")
        lines.append("")

    if not (customer_provided or provider_provided or to_be_confirmed):
        lines.append("*暂无设备/备件需求信息*")
        lines.append("")

    return lines


def _build_confidence_section(confidence_summary: Dict[str, Any]) -> List[str]:
    lines = []
    lines.append("## 七、置信度汇总")
    lines.append("")

    if not confidence_summary:
        lines.append("*暂无置信度信息*")
        lines.append("")
        return lines

    risk_conf = _format_confidence(confidence_summary.get("risk", ""))
    workhour_conf = _format_confidence(confidence_summary.get("workhour", ""))
    manpower_conf = _format_confidence(confidence_summary.get("manpower", ""))

    lines.append(f"- **风险**: {risk_conf}")
    lines.append(f"- **工时**: {workhour_conf}")
    lines.append(f"- **人数**: {manpower_conf}")
    lines.append("")

    return lines


def _build_review_focus_section(
    review_focus: List[str], warnings: List[Dict[str, Any]]
) -> List[str]:
    lines = []
    lines.append("## 八、审核重点")
    lines.append("")

    if warnings:
        lines.append("### ⚠️ 警告提示")
        lines.append("")
        for w in warnings:
            severity = w.get("severity", "medium")
            message = w.get("message", "")
            icon = "🔴" if severity == "high" else "⚠️"
            lines.append(f"- {icon} {message}")
        lines.append("")

    if review_focus:
        lines.append("### 重点关注")
        lines.append("")
        for focus in review_focus:
            lines.append(f"- {focus}")
        lines.append("")

    if not (warnings or review_focus):
        lines.append("*暂无审核重点*")
        lines.append("")

    return lines


def _build_learning_section(learning_summary: Dict[str, Any]) -> List[str]:
    lines = []
    lines.append("## 九、学习资产参考")
    lines.append("")

    if not learning_summary:
        lines.append("*本次无学习资产参考*")
        lines.append("")
        return lines

    sample_ids = learning_summary.get("used_learning_sample_ids", [])
    hints = learning_summary.get("applied_learning_hints", [])

    if sample_ids:
        lines.append(f"- **参考学习样本**: {len(sample_ids)} 个")
    else:
        lines.append("- **参考学习样本**: 无")

    if hints:
        hint_texts = []
        for h in hints:
            if "raise_risk" in h:
                hint_texts.append("类似场景常上调风险等级")
            elif "spare_part" in h:
                hint_texts.append("类似场景常补充备件说明")
            elif "increase_hours" in h:
                hint_texts.append("类似场景常增加工时")
            else:
                hint_texts.append(h)
        lines.append(f"- **学习提示**: {', '.join(hint_texts)}")
    else:
        lines.append("- **学习提示**: 无")

    lines.append("")
    lines.append("> 💡 系统已从历史修订经验中学习，以上提示供参考。")
    lines.append("")

    return lines


def _format_risk_level(level: str) -> str:
    mapping = {"high": "🔴 高", "medium": "🟡 中", "low": "🟢 低"}
    return mapping.get(level, level)


def _format_confidence(confidence: str) -> str:
    mapping = {"high": "✓ 高", "medium": "⚠ 中", "low": "⚡ 低"}
    return mapping.get(confidence, confidence)
