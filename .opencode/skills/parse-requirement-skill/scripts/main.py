#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import re
import sys
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
    parts = re.split(r'(?<=[\.\!\?\n。！？；;])\s+', text)
    return [p.strip() for p in parts if p.strip()]


def find_best_enum_match(text: str, items: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
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

    best = scored[0][1]
    candidates = [x[1] for x in scored[:3]]
    return best, candidates


def infer_business_type(
    service_desc: Optional[Dict[str, Any]],
    equipment_name: Optional[Dict[str, Any]],
    refs: Dict[str, Any]
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
            return {
                "code": item["code"],
                "name": item["name"],
                "confidence": "medium"
            }
    return None


def extract_model(text: str, refs: Dict[str, Any]) -> Optional[str]:
    patterns = refs.get("model_patterns", [])
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return None


def extract_manufacturer(text: str) -> Optional[str]:
    known = [
        "MAN B&W",
        "Wartsila",
        "WinGD",
        "Hyundai",
        "Mitsubishi"
    ]
    lower_text = text.lower()
    for item in known:
        if item.lower() in lower_text:
            return item
    return None


def extract_quantity_and_unit(text: str, refs: Dict[str, Any]) -> Tuple[Optional[float], Optional[Dict[str, Any]]]:
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(units?|sets?|pcs?|pieces?)\b',
        r'(\d+(?:\.\d+)?)\s*(台|套|个)\b'
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
        if matched_unit_raw.lower() in aliases:
            return matched_qty, {
                "code": item["code"],
                "name": item["name"],
                "confidence": "medium"
            }

    return matched_qty, None


def summarize_segment(segment: str) -> str:
    s = segment.strip()
    if len(s) <= 60:
        return s
    return s[:57] + "..."


def build_enum_value(item: Optional[Dict[str, Any]], confidence: str = "high") -> Optional[Dict[str, Any]]:
    if not item:
        return None
    return {
        "code": item.get("code"),
        "name": item.get("name"),
        "confidence": confidence
    }


def detect_service_type_ambiguity(text: str, matched_candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ambiguities = []
    if len(matched_candidates) >= 2:
        ambiguities.append({
            "field": "service_type",
            "reason": "文本中可能同时包含多个服务动作关键词，无法完全确定单一服务类型",
            "candidates": [{"code": c["code"], "name": c["name"]} for c in matched_candidates[:3]]
        })
    return ambiguities


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
            current_desc_match, _ = find_best_enum_match(current_text, service_desc_enum)
            if current_desc_match and current_desc_match.get("code") != desc_match.get("code"):
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


def parse_requirement_segment(segment: str, refs: Dict[str, Any], idx: int, strict: bool = False) -> Dict[str, Any]:
    service_desc_match, service_desc_candidates = find_best_enum_match(segment, refs.get("service_desc_enum", []))
    service_type_match, service_type_candidates = find_best_enum_match(segment, refs.get("service_type_enum", []))
    equipment_name_match, _ = find_best_enum_match(segment, refs.get("equipment_name_enum", []))

    business_type = infer_business_type(service_desc_match, equipment_name_match, refs)
    model = extract_model(segment, refs)
    qty, unit = extract_quantity_and_unit(segment, refs)

    ambiguities: List[Dict[str, Any]] = []
    ambiguities.extend(detect_service_type_ambiguity(segment, service_type_candidates))

    if service_desc_match is None and service_desc_candidates:
        ambiguities.append({
            "field": "service_desc",
            "reason": "识别到多个可能的服务描述候选",
            "candidates": [{"code": c["code"], "name": c["name"]} for c in service_desc_candidates[:3]]
        })

    confidence = "high"
    if service_desc_match is None or service_type_match is None:
        confidence = "medium"
    if strict and (service_desc_match is None or business_type is None):
        confidence = "low"

    needs_confirmation = False
    if confidence != "high" or len(ambiguities) > 0 or (model is not None and service_desc_match is None):
        needs_confirmation = True

    if equipment_name_match is None and service_desc_match is not None:
        equipment_name_match = {
            "code": None,
            "name": service_desc_match["name"]
        }

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
        "service_desc": build_enum_value(service_desc_match, "high" if service_desc_match else "low"),
        "service_type": build_enum_value(service_type_match, "medium" if service_type_match else "low"),
        "equipment_name": build_enum_value(equipment_name_match, "medium" if equipment_name_match else "low"),
        "equipment_model": {
            "code": None,
            "name": model,
            "confidence": "medium"
        } if model else None,
        "equipment_manufacturer": extract_manufacturer(segment),
        "equipment_quantity": qty,
        "equipment_unit": unit,
        "service_device_models": [model] if model else [],
        "remark": segment.strip(),
        "original_evidence": [segment],
        "ambiguities": ambiguities,
        "confidence": confidence,
        "needs_user_confirmation": needs_confirmation
    }


def parse_email_to_requirements(
    email_text: str,
    refs: Dict[str, Any],
    strict: bool = False,
    forced_lang: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    cleaned = normalize_text(email_text)
    language = detect_language(cleaned, forced_lang)

    segments = split_into_requirement_segments(cleaned, refs)
    requirements = [
        parse_requirement_segment(seg, refs, idx=i + 1, strict=strict)
        for i, seg in enumerate(segments)
    ]

    parsing_notes = []
    if len(requirements) > 1:
        parsing_notes.append("检测到多个服务项，已按设备对象/服务意图拆分。")
    if any(r["needs_user_confirmation"] for r in requirements):
        parsing_notes.append("部分字段存在歧义或缺失，建议人工确认。")

    return {
        "input_type": "email_text",
        "language": language,
        "requirement_count": len(requirements),
        "requirements": requirements,
        "global_ambiguities": [],
        "parsing_notes": parsing_notes,
        "metadata": metadata or {}
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
            "metadata": {}
        }

    if args.input_file:
        with open(args.input_file, "r", encoding="utf-8") as f:
            return {
                "email_text": f.read(),
                "attachments": [],
                "language_hint": args.lang,
                "strict": args.strict,
                "metadata": {}
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
            "metadata": {}
        }

    raise ValueError("No input provided. Use --input / --input-file / --json-input / --json-input-file / stdin.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ParseRequirementSkill")
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

        email_text = (payload.get("email_text") or "").strip()
        attachments = payload.get("attachments", [])
        language_hint = payload.get("language_hint") or args.lang
        strict = bool(payload.get("strict", args.strict))
        metadata = payload.get("metadata", {})

        if not email_text:
            dump(fail("EMPTY_INPUT", "Input text is empty."), args.pretty)
            return

        result = parse_email_to_requirements(
            email_text=email_text,
            refs=refs,
            strict=strict,
            forced_lang=language_hint,
            metadata=metadata
        )

        if attachments:
            result["parsing_notes"].append("检测到附件元信息，但当前版本未解析附件内容。")

        dump(ok(result), args.pretty)

    except FileNotFoundError as e:
        dump(fail("FILE_NOT_FOUND", str(e)), args.pretty)
    except json.JSONDecodeError as e:
        dump(fail("INVALID_JSON", f"Failed to parse JSON: {e}"), args.pretty)
    except Exception as e:
        dump(fail("PARSE_ERROR", str(e)), args.pretty)


if __name__ == "__main__":
    main()