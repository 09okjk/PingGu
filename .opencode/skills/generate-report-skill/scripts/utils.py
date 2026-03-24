import json
from pathlib import Path
from typing import Any, Dict


def load_json_file(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_json(data: Any, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(data, ensure_ascii=False, indent=2)
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def ok(data: Any) -> Dict[str, Any]:
    return {"success": True, "data": data, "error": None}


def fail(code: str, message: str) -> Dict[str, Any]:
    return {"success": False, "data": None, "error": {"code": code, "message": message}}


def safe_get_name(obj: Dict[str, Any], default: str = "") -> str:
    if not isinstance(obj, dict):
        return default
    return str(obj.get("name") or default)


def safe_get_code(obj: Dict[str, Any], default: str = "") -> str:
    if not isinstance(obj, dict):
        return default
    return str(obj.get("code") or default)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()