import json
from pathlib import Path
from typing import Any, Dict, List


def load_json_file(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(data: Any, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(data, ensure_ascii=False, indent=2)
    return json.dumps(data, ensure_ascii=False)


def ok(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"success": True, "data": data, "error": None}


def fail(code: str, message: str) -> Dict[str, Any]:
    return {"success": False, "data": None, "error": {"code": code, "message": message}}


def contains_any_keyword(text: str, keywords: List[str]) -> List[str]:
    if not text:
        return []
    hits = []
    for keyword in keywords:
        if keyword and keyword in text:
            hits.append(keyword)
    return hits


def avg(numbers: List[float]) -> float:
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)


def safe_get(d: Dict[str, Any], *keys: str, default=None):
    current = d
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def refs_path(refs_dir: str, filename: str) -> str:
    return str(Path(refs_dir) / filename)