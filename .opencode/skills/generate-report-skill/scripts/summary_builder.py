from typing import Any, Dict

from utils import normalize_text


def build_summary(requirement: Dict[str, Any]) -> Dict[str, Any]:
    remark = normalize_text(requirement.get("remark", ""))
    remark_summary = remark[:200] if remark else ""

    service_desc = requirement.get("service_desc") or {}
    service_type = requirement.get("service_type") or {}
    equipment_name = requirement.get("equipment_name") or {}
    equipment_model = requirement.get("equipment_model") or {}
    business_type = requirement.get("business_type") or {}
    service_location_type = requirement.get("service_location_type") or {}
    equipment_unit = requirement.get("equipment_unit") or {}

    summary_parts = [
        business_type.get("name", ""),
        service_desc.get("name", ""),
        service_type.get("name", ""),
        equipment_name.get("name", ""),
        equipment_model.get("name", ""),
    ]
    requirement_summary = " / ".join([p for p in summary_parts if p])

    return {
        "requirement_summary": requirement_summary,
        "business_type": business_type,
        "service_desc": service_desc,
        "service_type": service_type,
        "service_location_type": service_location_type,
        "equipment_name": equipment_name,
        "equipment_model": equipment_model,
        "equipment_manufacturer": requirement.get("equipment_manufacturer"),
        "equipment_quantity": requirement.get("equipment_quantity"),
        "equipment_unit": equipment_unit,
        "remark": remark,
        "requirement_detail": requirement.get("requirement_detail"),
        "remark_summary": remark_summary,
    }
