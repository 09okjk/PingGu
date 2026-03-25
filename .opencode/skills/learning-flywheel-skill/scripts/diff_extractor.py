from typing import Any, Dict, List, Optional

from utils import flatten_json, summarize_value


def _build_flat_map(data: Any) -> Dict[str, Any]:
    """Build flat path->value map from nested JSON."""
    return {path: value for path, value in flatten_json(data) if path}


def _normalize_edit_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize external edit action shape."""
    return {
        "field_path": action.get("field_path") or action.get("path") or "",
        "action": action.get("action") or "update",
        "before": summarize_value(action.get("before")),
        "after": summarize_value(action.get("after")),
        "source": action.get("source") or "edit_action",
    }


def extract_revision_diff(
    initial_report_json: Any,
    final_report_json: Any,
    edit_actions: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Extract structured revision diff between initial and final report.

    Priority:
    1. Use JSON-level diff as canonical baseline.
    2. Merge explicit edit_actions as supplemental evidence.
    """
    initial_map = _build_flat_map(initial_report_json)
    final_map = _build_flat_map(final_report_json)

    all_paths = sorted(set(initial_map.keys()) | set(final_map.keys()))
    results: List[Dict[str, Any]] = []

    for path in all_paths:
        before = initial_map.get(path, None)
        after = final_map.get(path, None)

        if path not in initial_map:
            results.append(
                {
                    "field_path": path,
                    "action": "add",
                    "before": None,
                    "after": summarize_value(after),
                    "source": "json_diff",
                }
            )
            continue

        if path not in final_map:
            results.append(
                {
                    "field_path": path,
                    "action": "remove",
                    "before": summarize_value(before),
                    "after": None,
                    "source": "json_diff",
                }
            )
            continue

        if before != after:
            results.append(
                {
                    "field_path": path,
                    "action": "update",
                    "before": summarize_value(before),
                    "after": summarize_value(after),
                    "source": "json_diff",
                }
            )

    seen = {(item["field_path"], item["action"], str(item["before"]), str(item["after"])) for item in results}

    for action in edit_actions or []:
        normalized = _normalize_edit_action(action)
        key = (
            normalized["field_path"],
            normalized["action"],
            str(normalized["before"]),
            str(normalized["after"]),
        )
        if normalized["field_path"] and key not in seen:
            results.append(normalized)
            seen.add(key)

    return results