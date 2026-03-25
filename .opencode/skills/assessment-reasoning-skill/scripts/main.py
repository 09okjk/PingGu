import argparse
import io
import sys
from typing import Any, Dict, List

# Windows 编码兼容性修复
if sys.platform == "win32":
    # 确保标准输出使用 UTF-8 编码
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", line_buffering=True
        )

from db import ReferenceRepository
from manpower_engine import estimate_manpower
from risk_engine import match_risks
from utils import dump_json, fail, load_json_file, ok
from workhour_engine import estimate_workhours


def extract_learning_signals(
    learning_samples: List[Dict[str, Any]],
) -> tuple[List[str], List[str]]:
    signals: List[str] = []
    references: List[str] = []

    if not learning_samples:
        return signals, references

    risk_revisions = 0
    spare_part_revisions = 0
    workhour_revisions = 0

    for sample in learning_samples:
        summary = (sample.get("revision_summary") or "").lower()
        sample_id = sample.get("sample_id", "")

        if "风险" in summary and ("上调" in summary or "提高" in summary):
            risk_revisions += 1
            if sample_id:
                references.append(sample_id)
        if "备件" in summary or "等待" in summary:
            spare_part_revisions += 1
            if sample_id and sample_id not in references:
                references.append(sample_id)
        if "工时" in summary or (
            "时间" in summary and ("增加" in summary or "延长" in summary)
        ):
            workhour_revisions += 1
            if sample_id and sample_id not in references:
                references.append(sample_id)

    if risk_revisions > 0:
        signals.append("similar_revisions_often_raise_risk_level")
    if spare_part_revisions > 0:
        signals.append("similar_revisions_often_add_spare_part_notes")
    if workhour_revisions > 0:
        signals.append("similar_revisions_often_increase_hours")

    return signals, references


def build_reasoning_trace(
    requirement: Dict[str, Any],
    history_cases: List[Dict[str, Any]],
    risk_results: List[Dict[str, Any]],
    workhour_results: List[Dict[str, Any]],
    manpower_result: Dict[str, Any],
    learning_samples: List[Dict[str, Any]] | None = None,
) -> List[str]:
    trace: List[str] = []

    remark = requirement.get("remark", "") or ""
    hit_keywords = []
    for risk in risk_results:
        for item in risk.get("trigger_basis", []):
            if item.startswith("remark_keyword:"):
                hit_keywords.append(item.replace("remark_keyword:", ""))

    if hit_keywords:
        trace.append(f"命中 remark 关键词：{'、'.join(sorted(set(hit_keywords)))}")

    if history_cases:
        trace.append(
            f"参考历史案例 {history_cases[0].get('case_id', 'unknown')} 的风险与人员配置"
        )

    if workhour_results:
        trace.append("工时估算采用历史参考值并叠加风险修正")

    if manpower_result:
        trace.append("人数推理采用可串行则复用的简化规则")

    if learning_samples:
        signals, _ = extract_learning_signals(learning_samples)
        if signals:
            trace.append(f"学习资产提示：{','.join(signals)}")

    return trace


def summarize_confidence(
    risk_results: List[Dict[str, Any]],
    workhour_results: List[Dict[str, Any]],
    manpower_result: Dict[str, Any],
) -> Dict[str, str]:
    risk_conf = risk_results[0]["confidence"] if risk_results else "low"
    workhour_conf = workhour_results[0]["confidence"] if workhour_results else "low"
    manpower_conf = manpower_result.get("confidence", "low")

    return {
        "risk": risk_conf,
        "workhour": workhour_conf,
        "manpower": manpower_conf,
    }


def run_reason_assessment(payload: Dict[str, Any], refs_dir: str) -> Dict[str, Any]:
    requirement = payload.get("requirement", {})
    history_cases = payload.get("history_cases", [])
    learning_samples = payload.get("learning_samples", [])

    repo = ReferenceRepository(refs_dir)
    risk_rules = repo.get_risk_rules()
    workhour_rules = repo.get_workhour_rules()
    manpower_rules = repo.get_manpower_rules()

    risk_results = match_risks(requirement, history_cases, risk_rules)
    workhour_results = estimate_workhours(
        requirement, history_cases, workhour_rules, risk_results
    )
    manpower_result = estimate_manpower(history_cases, manpower_rules)

    confidence_summary = summarize_confidence(
        risk_results, workhour_results, manpower_result
    )
    reasoning_trace = build_reasoning_trace(
        requirement,
        history_cases,
        risk_results,
        workhour_results,
        manpower_result,
        learning_samples,
    )

    warnings = []
    if not history_cases:
        warnings.append("历史案例为空，当前结果主要基于规则与兜底逻辑。")
    if workhour_results and workhour_results[0]["confidence"] == "low":
        warnings.append("工时估算依据较弱，建议人工复核。")
    if manpower_result.get("confidence") == "low":
        warnings.append("人数推理依据较弱，建议人工复核。")

    learning_signals, learning_references = extract_learning_signals(learning_samples)

    if learning_signals:
        for signal in learning_signals:
            if "raise_risk" in signal:
                warnings.append(
                    "学习资产提示：类似场景中人工常上调风险等级，请重点确认。"
                )
            if "add_spare_part" in signal:
                warnings.append(
                    "学习资产提示：类似场景中人工常补充备件相关说明，请重点确认。"
                )
            if "increase_hours" in signal:
                warnings.append(
                    "学习资产提示：类似场景中人工常增加工时估算，请重点确认。"
                )

    return {
        "requirement_id": requirement.get("requirement_id", "unknown"),
        "status": "ok",
        "risk_results": risk_results,
        "workhour_results": workhour_results,
        "manpower_result": manpower_result,
        "confidence_summary": confidence_summary,
        "reasoning_trace": reasoning_trace,
        "warnings": warnings,
        "learning_signals": learning_signals,
        "learning_references": learning_references,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True)
    parser.add_argument("--json-input", required=True)
    parser.add_argument("--refs-dir", required=True)
    parser.add_argument("--pretty", action="store_true")

    args = parser.parse_args()

    try:
        payload = load_json_file(args.json_input)

        if args.action == "reason_assessment":
            result = run_reason_assessment(payload, args.refs_dir)
        elif args.action == "match_risks":
            repo = ReferenceRepository(args.refs_dir)
            result = match_risks(
                payload.get("requirement", {}),
                payload.get("history_cases", []),
                repo.get_risk_rules(),
            )
        elif args.action == "estimate_workhours":
            repo = ReferenceRepository(args.refs_dir)
            risks = match_risks(
                payload.get("requirement", {}),
                payload.get("history_cases", []),
                repo.get_risk_rules(),
            )
            result = estimate_workhours(
                payload.get("requirement", {}),
                payload.get("history_cases", []),
                repo.get_workhour_rules(),
                risks,
            )
        elif args.action == "estimate_manpower":
            repo = ReferenceRepository(args.refs_dir)
            result = estimate_manpower(
                payload.get("history_cases", []),
                repo.get_manpower_rules(),
            )
        else:
            print(
                dump_json(
                    fail("INVALID_ACTION", f"Unsupported action: {args.action}"),
                    args.pretty,
                )
            )
            return

        # 使用 UTF-8 输出，避免 Windows 控制台编码问题
        output = dump_json(ok(result), args.pretty)
        print(output.encode("utf-8").decode("utf-8"))
    except FileNotFoundError as e:
        print(dump_json(fail("FILE_NOT_FOUND", str(e)), args.pretty))
    except Exception as e:
        print(dump_json(fail("UNEXPECTED_ERROR", str(e)), args.pretty))


if __name__ == "__main__":
    main()
