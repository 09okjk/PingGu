from typing import Any, Dict, List

from utils import confidence_from_score, normalize_text, safe_get


def score_learning_sample(
    context: Dict[str, Any],
    artifacts: Dict[str, Any],
    revision_diff: List[Dict[str, Any]],
    feedback_tags: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Score whether a revision case should be stored as a learning sample."""
    score = 0.0
    reasons: List[str] = []

    final_report = safe_get(artifacts, "final_report_json", {})
    initial_report = safe_get(artifacts, "initial_report_json", {})
    task_id = normalize_text(safe_get(context, "task_id", ""))

    if task_id:
        score += 0.10
        reasons.append("task_id 可追溯")

    if isinstance(initial_report, dict) and isinstance(final_report, dict):
        score += 0.15
        reasons.append("初稿与终稿结构完整")

    diff_count = len(revision_diff)
    if diff_count >= 1:
        score += 0.20
        reasons.append("存在明确修订差异")
    if diff_count >= 3:
        score += 0.10
        reasons.append("修订差异较充分")

    if feedback_tags:
        score += 0.15
        reasons.append("可识别归因标签")

    status = normalize_text(final_report.get("status")).lower()
    if status in {"ok", "confirmed", "final"}:
        score += 0.15
        reasons.append("终稿状态明确")

    conversation_messages = safe_get(artifacts, "conversation_messages", [])
    if isinstance(conversation_messages, list) and conversation_messages:
        score += 0.05
        reasons.append("包含对话上下文")

    edit_actions = safe_get(artifacts, "edit_actions", [])
    if isinstance(edit_actions, list) and edit_actions:
        score += 0.05
        reasons.append("包含字段编辑动作")

    if score > 1.0:
        score = 1.0

    quality_score = round(score, 2)
    store = quality_score >= 0.55

    scenario = {
        "business_type": safe_get(context, "business_type"),
        "ship_type": safe_get(context, "ship_type"),
    }

    return {
        "store": store,
        "sample_type": "revision_case",
        "quality_score": quality_score,
        "confidence": confidence_from_score(quality_score),
        "status": "candidate" if store else "discarded",
        "source_task_id": task_id,
        "scenario": scenario,
        "reason_summary": reasons,
    }