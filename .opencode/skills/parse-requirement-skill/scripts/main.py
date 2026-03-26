#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import re
import sys
import uuid
from typing import Any, Dict, List, Optional, Tuple


def ok(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"success": True, "data": data, "error": None}


def fail(code: str, message: str) -> Dict[str, Any]:
    return {"success": False, "data": None, "error": {"code": code, "message": message}}


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dump(result: Dict[str, Any], pretty: bool) -> None:
    if pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))


def gen_session_id() -> str:
    return f"sess-{uuid.uuid4().hex[:12]}"


def detect_language(text: str, forced_lang: Optional[str] = None) -> str:
    if forced_lang:
        return forced_lang

    has_cjk = bool(re.search(r"[\u4e00-\u9fff]", text))
    has_kana = bool(re.search(r"[\u3040-\u30ff]", text))
    has_hangul = bool(re.search(r"[\uac00-\ud7af]", text))

    if has_hangul:
        return "ko"
    if has_kana:
        return "ja"
    if has_cjk:
        return "zh"
    return "en"


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[\.\!\?\n。！？；;])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def find_best_enum_match(
    text: str, items: List[Dict[str, Any]]
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    lower_text = text.lower()
    scored = []

    for item in items:
        score = 0
        aliases = item.get("aliases", [])
        for alias in aliases:
            alias_lower = alias.lower()
            if alias_lower in lower_text:
                score = max(score, len(alias_lower))
        if item.get("name", "").lower() in lower_text:
            score = max(score, len(item["name"]))
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        return None, []

    return scored[0][1], [x[1] for x in scored[:3]]


def infer_business_type(
    service_desc: Optional[Dict[str, Any]],
    equipment_name: Optional[Dict[str, Any]],
    refs: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    mapping = refs.get("business_type_inference", {})
    bt_enum = refs.get("business_type_enum", [])

    candidate_code = None
    if service_desc and service_desc.get("code") in mapping:
        candidate_code = mapping[service_desc["code"]]
    elif equipment_name and equipment_name.get("code") in mapping:
        candidate_code = mapping[equipment_name["code"]]

    if not candidate_code:
        return None

    for item in bt_enum:
        if item.get("code") == candidate_code:
            return {"code": item["code"], "name": item["name"], "confidence": "medium"}
    return None


def extract_model(text: str, refs: Dict[str, Any]) -> Optional[str]:
    patterns = refs.get("model_patterns", [])
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return None


def extract_manufacturer(text: str) -> Optional[str]:
    known = ["MAN B&W", "Wartsila", "WinGD", "Hyundai", "Mitsubishi"]
    lower_text = text.lower()
    for item in known:
        if item.lower() in lower_text:
            return item
    return None


def extract_quantity_and_unit(
    text: str, refs: Dict[str, Any]
) -> Tuple[Optional[float], Optional[Dict[str, Any]]]:
    patterns = [
        r"(\d+(?:\.\d+)?)\s*(units?|sets?|pcs?|pieces?)\b",
        r"(\d+(?:\.\d+)?)\s*(台|套|个)\b",
    ]

    matched_qty = None
    matched_unit_raw = None
    for p in patterns:
        m = re.search(p, text, flags=re.IGNORECASE)
        if m:
            matched_qty = float(m.group(1))
            matched_unit_raw = m.group(2)
            break

    if matched_qty is None:
        return None, None

    unit_enum = refs.get("unit_enum", [])
    for item in unit_enum:
        aliases = [a.lower() for a in item.get("aliases", [])]
        if matched_unit_raw and matched_unit_raw.lower() in aliases:
            return matched_qty, {
                "code": item["code"],
                "name": item["name"],
                "confidence": "medium",
            }

    return matched_qty, None


def summarize_segment(segment: str) -> str:
    s = segment.strip()
    return s if len(s) <= 60 else s[:57] + "..."


def build_enum_value(
    item: Optional[Dict[str, Any]], confidence: str = "high"
) -> Optional[Dict[str, Any]]:
    if not item:
        return None
    return {
        "code": item.get("code"),
        "name": item.get("name"),
        "confidence": confidence,
    }


def detect_service_type_ambiguity(
    matched_candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if len(matched_candidates) < 2:
        return []
    return [
        {
            "field": "service_type",
            "reason": "文本中可能同时包含多个服务动作关键词，无法完全确定单一服务类型",
            "candidates": [
                {"code": c["code"], "name": c["name"]} for c in matched_candidates[:3]
            ],
        }
    ]


def split_into_requirement_segments(text: str, refs: Dict[str, Any]) -> List[str]:
    sentences = split_sentences(text)
    if not sentences:
        return [text]

    service_desc_enum = refs.get("service_desc_enum", [])
    split_keywords = [k.lower() for k in refs.get("split_keywords", [])]

    segments: List[List[str]] = []
    current: List[str] = []

    for sent in sentences:
        sent_lower = sent.lower()
        desc_match, _ = find_best_enum_match(sent, service_desc_enum)

        should_start_new = False
        if current and desc_match:
            current_text = " ".join(current)
            current_desc_match, _ = find_best_enum_match(
                current_text, service_desc_enum
            )
            if current_desc_match and current_desc_match.get("code") != desc_match.get(
                "code"
            ):
                should_start_new = True

        if current and any(k in sent_lower for k in split_keywords):
            if desc_match:
                should_start_new = True

        if should_start_new:
            segments.append(current)
            current = [sent]
        else:
            current.append(sent)

    if current:
        segments.append(current)

    merged = [" ".join(seg).strip() for seg in segments if " ".join(seg).strip()]
    return merged if merged else [text]


def parse_requirement_segment(
    segment: str, refs: Dict[str, Any], idx: int, strict: bool = False
) -> Dict[str, Any]:
    service_desc_match, service_desc_candidates = find_best_enum_match(
        segment, refs.get("service_desc_enum", [])
    )
    service_type_match, service_type_candidates = find_best_enum_match(
        segment, refs.get("service_type_enum", [])
    )
    equipment_name_match, _ = find_best_enum_match(
        segment, refs.get("equipment_name_enum", [])
    )

    business_type = infer_business_type(service_desc_match, equipment_name_match, refs)
    model = extract_model(segment, refs)
    qty, unit = extract_quantity_and_unit(segment, refs)

    ambiguities = detect_service_type_ambiguity(service_type_candidates)

    confidence = "high"
    if service_desc_match is None or service_type_match is None:
        confidence = "medium"
    if strict and (service_desc_match is None or business_type is None):
        confidence = "low"

    needs_confirmation = confidence != "high" or len(ambiguities) > 0

    if equipment_name_match is None and service_desc_match is not None:
        equipment_name_match = {"code": None, "name": service_desc_match["name"]}

    summary_parts = []
    if service_desc_match:
        summary_parts.append(service_desc_match["name"])
    if service_type_match:
        summary_parts.append(service_type_match["name"])
    if not summary_parts:
        summary_parts.append(summarize_segment(segment))

    return {
        "requirement_id": f"REQ-{idx:03d}",
        "summary": " / ".join(summary_parts),
        "business_type": business_type,
        "service_desc": build_enum_value(
            service_desc_match, "high" if service_desc_match else "low"
        ),
        "service_type": build_enum_value(
            service_type_match, "medium" if service_type_match else "low"
        ),
        "equipment_name": build_enum_value(
            equipment_name_match, "medium" if equipment_name_match else "low"
        ),
        "equipment_model": {"code": None, "name": model, "confidence": "medium"}
        if model
        else None,
        "equipment_manufacturer": extract_manufacturer(segment),
        "equipment_quantity": qty,
        "equipment_unit": unit,
        "service_device_models": [model] if model else [],
        "remark": segment.strip(),
        "requirement_detail": None,
        "original_evidence": [segment],
        "ambiguities": ambiguities,
        "confidence": confidence,
        "needs_user_confirmation": needs_confirmation,
    }


def build_next_questions(requirements: List[Dict[str, Any]]) -> List[str]:
    questions = []

    if len(requirements) > 1:
        questions.append(
            f"我识别出 {len(requirements)} 个服务项，是否正确？是否需要新增、删除、合并或拆分？"
        )

    for req in requirements:
        rid = req.get("requirement_id")
        if req.get("service_desc") is None:
            questions.append(
                f"{rid} 的服务描述尚未识别，请确认该服务项对应的设备/服务对象。"
            )
        if req.get("service_type") is None:
            questions.append(
                f"{rid} 的服务类型尚未识别，请确认是检测、维修、更换、安装还是保养。"
            )
        if req.get("needs_user_confirmation"):
            questions.append(f"请确认 {rid} 的内容是否准确：{req.get('summary', '')}")

    if not questions:
        questions.append("当前需求单已基本解析完成，是否确认无需继续修改？")

    return questions[:5]


def parse_action(
    payload: Dict[str, Any],
    refs: Dict[str, Any],
    forced_lang: Optional[str],
    strict: bool,
) -> Dict[str, Any]:
    email_text = normalize_text((payload.get("email_text") or "").strip())
    if not email_text:
        raise ValueError("email_text is empty.")

    session_id = payload.get("session_id") or gen_session_id()
    metadata = payload.get("metadata", {})
    attachments = payload.get("attachments", [])
    language = detect_language(email_text, forced_lang or payload.get("language_hint"))

    segments = split_into_requirement_segments(email_text, refs)
    requirements = [
        parse_requirement_segment(seg, refs, idx=i + 1, strict=strict)
        for i, seg in enumerate(segments)
    ]

    next_questions = build_next_questions(requirements)
    status = "needs_confirmation"
    if (
        all(not r.get("needs_user_confirmation", False) for r in requirements)
        and len(next_questions) == 1
    ):
        status = "draft"

    parsing_notes = []
    if len(requirements) > 1:
        parsing_notes.append("检测到多个服务项，已按设备对象/服务意图拆分。")
    if attachments:
        parsing_notes.append("检测到附件元信息，但当前版本未解析附件内容。")

    return {
        "session_id": session_id,
        "status": status,
        "action": "parse",
        "input_type": "email_text",
        "language": language,
        "requirements": requirements,
        "next_questions": next_questions,
        "revision_history": [],
        "parsing_notes": parsing_notes,
        "metadata": metadata,
    }


def apply_feedback_to_requirements(
    requirements: List[Dict[str, Any]], feedback: str, refs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    feedback_lower = feedback.lower()

    target_index = None

    m_req = re.search(r"req[-\s]?0*([1-9]\d*)", feedback_lower)
    if m_req:
        target_index = int(m_req.group(1)) - 1

    m_cn = re.search(r"第\s*([1-9]\d*)\s*项", feedback)
    if m_cn:
        target_index = int(m_cn.group(1)) - 1

    def detect_target_service_type(text: str) -> Optional[Dict[str, Any]]:
        st_enum = refs.get("service_type_enum", [])
        best, _ = find_best_enum_match(text, st_enum)
        return best

    service_type_target = detect_target_service_type(feedback)

    updated = json.loads(json.dumps(requirements, ensure_ascii=False))

    if service_type_target:
        if target_index is not None and 0 <= target_index < len(updated):
            req = updated[target_index]
            req["service_type"] = {
                "code": service_type_target["code"],
                "name": service_type_target["name"],
                "confidence": "high",
            }
            req["summary"] = rebuild_summary(req)
            req["confidence"] = "high"
            req["needs_user_confirmation"] = False
            req["ambiguities"] = []
        else:
            for req in reversed(updated):
                if req.get("needs_user_confirmation", False):
                    req["service_type"] = {
                        "code": service_type_target["code"],
                        "name": service_type_target["name"],
                        "confidence": "high",
                    }
                    req["summary"] = rebuild_summary(req)
                    req["confidence"] = "high"
                    req["needs_user_confirmation"] = False
                    req["ambiguities"] = []
                    break

    detail_keywords = [
        "需求详情",
        "补充信息",
        "另外",
        "经确认",
        "客户反馈",
        "detail",
        "补充",
    ]
    if any(kw in feedback_lower for kw in detail_keywords):
        detail_text = feedback
        for kw in [
            "需求详情:",
            "需求详情：",
            "补充信息:",
            "补充信息：",
            "detail:",
            "detail:",
        ]:
            if kw in feedback:
                detail_text = feedback.split(kw, 1)[1].strip()
                break
        if target_index is not None and 0 <= target_index < len(updated):
            updated[target_index]["requirement_detail"] = detail_text
        else:
            for req in reversed(updated):
                if req.get("needs_user_confirmation", False) or req == updated[-1]:
                    req["requirement_detail"] = detail_text
                    break

    return updated


def rebuild_summary(req: Dict[str, Any]) -> str:
    parts = []
    if req.get("service_desc") and req["service_desc"].get("name"):
        parts.append(req["service_desc"]["name"])
    if req.get("service_type") and req["service_type"].get("name"):
        parts.append(req["service_type"]["name"])
    return " / ".join(parts) if parts else req.get("summary", "")


def revise_action(payload: Dict[str, Any], refs: Dict[str, Any]) -> Dict[str, Any]:
    session_id = payload.get("session_id")
    if not session_id:
        raise ValueError("session_id is required for revise.")

    current_requirements = payload.get("current_requirements", [])
    user_feedback = (payload.get("user_feedback") or "").strip()
    revision_history = payload.get("revision_history", [])
    metadata = payload.get("metadata", {})

    if not current_requirements:
        raise ValueError("current_requirements is required for revise.")
    if not user_feedback:
        raise ValueError("user_feedback is required for revise.")

    updated_requirements = apply_feedback_to_requirements(
        current_requirements, user_feedback, refs
    )

    revision_history = revision_history + [
        {"turn": len(revision_history) + 1, "user_feedback": user_feedback}
    ]

    next_questions = build_next_questions(updated_requirements)
    status = "needs_confirmation"
    if (
        "确认" in user_feedback
        or "可以了" in user_feedback
        or "无需修改" in user_feedback
    ):
        status = "confirmed"
        next_questions = []
    elif all(not r.get("needs_user_confirmation", False) for r in updated_requirements):
        next_questions = ["当前需求单已更新，是否确认无需再修改？"]

    return {
        "session_id": session_id,
        "status": status,
        "action": "revise",
        "requirements": updated_requirements,
        "next_questions": next_questions,
        "revision_history": revision_history,
        "metadata": metadata,
    }


def confirm_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    session_id = payload.get("session_id")
    current_requirements = payload.get("current_requirements", [])
    user_feedback = (payload.get("user_feedback") or "").strip()
    revision_history = payload.get("revision_history", [])
    metadata = payload.get("metadata", {})

    if not session_id:
        raise ValueError("session_id is required for confirm.")
    if not current_requirements:
        raise ValueError("current_requirements is required for confirm.")

    if user_feedback:
        revision_history = revision_history + [
            {"turn": len(revision_history) + 1, "user_feedback": user_feedback}
        ]

    return {
        "session_id": session_id,
        "status": "confirmed",
        "action": "confirm",
        "requirements": current_requirements,
        "next_questions": [],
        "revision_history": revision_history,
        "metadata": metadata,
    }


def read_payload(args: argparse.Namespace) -> Dict[str, Any]:
    if args.json_input:
        return json.loads(args.json_input)

    if args.json_input_file:
        return load_json(args.json_input_file)

    if args.input:
        return {
            "email_text": args.input,
            "attachments": [],
            "language_hint": args.lang,
            "strict": args.strict,
            "metadata": {},
        }

    if args.input_file:
        with open(args.input_file, "r", encoding="utf-8") as f:
            return {
                "email_text": f.read(),
                "attachments": [],
                "language_hint": args.lang,
                "strict": args.strict,
                "metadata": {},
            }

    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        if not raw:
            raise ValueError("STDIN is empty.")
        try:
            maybe_json = json.loads(raw)
            if isinstance(maybe_json, dict):
                return maybe_json
        except Exception:
            pass
        return {
            "email_text": raw,
            "attachments": [],
            "language_hint": args.lang,
            "strict": args.strict,
            "metadata": {},
        }

    raise ValueError("No input provided.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ParseRequirementSkill v2")
    parser.add_argument(
        "--action", required=True, choices=["parse", "revise", "confirm"]
    )
    parser.add_argument("--input", help="Raw email text")
    parser.add_argument("--input-file", help="Path to raw input text file")
    parser.add_argument("--json-input", help="Full JSON input payload")
    parser.add_argument("--json-input-file", help="Path to JSON input payload file")
    parser.add_argument("--refs", required=True, help="Path to R2 reference JSON")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--strict", action="store_true", help="Strict mode")
    parser.add_argument("--lang", help="Forced language code")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        refs = load_json(args.refs)
        payload = read_payload(args)

        if args.action == "parse":
            result = parse_action(payload, refs, args.lang, args.strict)
        elif args.action == "revise":
            result = revise_action(payload, refs)
        elif args.action == "confirm":
            result = confirm_action(payload)
        else:
            raise ValueError(f"Unsupported action: {args.action}")

        dump(ok(result), args.pretty)

    except FileNotFoundError as e:
        dump(fail("FILE_NOT_FOUND", str(e)), args.pretty)
    except json.JSONDecodeError as e:
        dump(fail("INVALID_JSON", f"Failed to parse JSON: {e}"), args.pretty)
    except Exception as e:
        dump(fail("PARSE_ERROR", str(e)), args.pretty)


if __name__ == "__main__":
    main()
