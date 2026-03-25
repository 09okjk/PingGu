import argparse
import io
import json
import sys
from typing import Any, Dict

# Windows 编码兼容性修复
if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", line_buffering=True
        )

from diff_extractor import extract_revision_diff
from feedback_classifier import classify_feedback
from preference_miner import mine_report_preferences
from rule_miner import mine_rule_candidates
from sample_scorer import score_learning_sample
from storage import maybe_store_result_in_db, maybe_store_result_locally
from utils import dump_json, fail, load_json_file, ok


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="S3 LearningFlywheelSkill")
    parser.add_argument("--action", required=True, choices=["learn_from_revision"])
    parser.add_argument("--json-input-file", help="Path to input JSON file")
    parser.add_argument("--json-input", help="Inline input JSON string")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def load_payload(args: argparse.Namespace) -> Dict[str, Any]:
    """Load payload from file or inline JSON."""
    if args.json_input_file:
        return load_json_file(args.json_input_file)
    if args.json_input:
        return json.loads(args.json_input)
    raise ValueError("json-input-file or json-input is required")


def normalize_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize context object."""
    context = payload.get("context") or {}
    if not isinstance(context, dict):
        raise ValueError("context must be an object")
    return context


def normalize_artifacts(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize artifacts object."""
    artifacts = payload.get("artifacts") or {}
    if not isinstance(artifacts, dict):
        raise ValueError("artifacts must be an object")
    if "initial_report_json" not in artifacts or "final_report_json" not in artifacts:
        raise ValueError("artifacts.initial_report_json and artifacts.final_report_json are required")
    return artifacts


def normalize_versions(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize versions object."""
    versions = payload.get("versions") or {}
    if not isinstance(versions, dict):
        raise ValueError("versions must be an object")
    return versions


def build_next_step_actions(
    learning_sample: Dict[str, Any],
    rule_candidates: Any,
    report_preference_candidates: Any,
    local_storage_meta: Dict[str, Any],
    db_storage_meta: Dict[str, Any],
) -> Any:
    """Build next step actions list."""
    actions = ["store_revision"]

    if learning_sample.get("store"):
        actions.append("store_learning_sample")

    if rule_candidates:
        actions.append("submit_rule_candidates_for_review")

    if report_preference_candidates:
        actions.append("submit_preference_candidates_for_review")

    if local_storage_meta.get("stored"):
        actions.append("local_storage_completed")

    if db_storage_meta.get("stored"):
        actions.append("db_storage_completed")

    return actions


def learn_from_revision(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Main S3 pipeline."""
    context = normalize_context(payload)
    artifacts = normalize_artifacts(payload)
    versions = normalize_versions(payload)
    options = payload.get("options") or {}

    revision_diff = extract_revision_diff(
        artifacts.get("initial_report_json"),
        artifacts.get("final_report_json"),
        artifacts.get("edit_actions", []),
    )

    feedback_tags = classify_feedback(revision_diff, artifacts)

    learning_sample = score_learning_sample(
        context=context,
        artifacts=artifacts,
        revision_diff=revision_diff,
        feedback_tags=feedback_tags,
    )

    rule_candidates = []
    if options.get("generate_rule_candidates", True):
        rule_candidates = mine_rule_candidates(
            context=context,
            artifacts=artifacts,
            revision_diff=revision_diff,
            feedback_tags=feedback_tags,
        )

    report_preference_candidates = []
    if options.get("generate_preference_candidates", True):
        report_preference_candidates = mine_report_preferences(
            context=context,
            artifacts=artifacts,
            revision_diff=revision_diff,
            feedback_tags=feedback_tags,
        )

    data = {
        "skill": "LearningFlywheelSkill",
        "version": "1.1.0",
        "context": context,
        "versions": versions,
        "revision_diff": revision_diff,
        "feedback_tags": feedback_tags,
        "learning_sample": learning_sample,
        "rule_candidates": rule_candidates,
        "report_preference_candidates": report_preference_candidates,
        "confidence": learning_sample.get("confidence", "medium"),

        # 为 storage 层保留完整工件快照
        "artifacts_snapshot": {
            "requirement_json": artifacts.get("requirement_json", {}),
            "history_cases_json": artifacts.get("history_cases_json", []),
            "assessment_reasoning_json": artifacts.get("assessment_reasoning_json", {}),
            "initial_report_json": artifacts.get("initial_report_json", {}),
            "final_report_json": artifacts.get("final_report_json", {}),
            "conversation_messages": artifacts.get("conversation_messages", []),
            "edit_actions": artifacts.get("edit_actions", []),
        }
    }

    local_storage_meta = maybe_store_result_locally(data)
    db_storage_meta = maybe_store_result_in_db(data)

    data["storage"] = {
        "local": local_storage_meta,
        "database": db_storage_meta,
    }

    data["next_step_actions"] = build_next_step_actions(
        learning_sample=learning_sample,
        rule_candidates=rule_candidates,
        report_preference_candidates=report_preference_candidates,
        local_storage_meta=local_storage_meta,
        db_storage_meta=db_storage_meta,
    )

    return data


def main() -> None:
    """CLI entrypoint."""
    try:
        args = parse_args()
        payload = load_payload(args)

        if args.action == "learn_from_revision":
            result = learn_from_revision(payload)
            print(dump_json(ok(result), pretty=args.pretty))
            return

        print(dump_json(fail("INVALID_ACTION", f"Unsupported action: {args.action}"), pretty=args.pretty))
    except FileNotFoundError as e:
        print(dump_json(fail("FILE_NOT_FOUND", str(e)), pretty=True))
    except json.JSONDecodeError as e:
        print(dump_json(fail("INVALID_JSON", str(e)), pretty=True))
    except ValueError as e:
        print(dump_json(fail("INVALID_INPUT", str(e)), pretty=True))
    except Exception as e:
        print(dump_json(fail("UNEXPECTED_ERROR", str(e)), pretty=True))


if __name__ == "__main__":
    main()