import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_json_file(path: str) -> Any:
    """Load JSON from a UTF-8 encoded file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_json(data: Any, pretty: bool = False) -> str:
    """Serialize JSON with UTF-8 friendly output."""
    if pretty:
        return json.dumps(data, ensure_ascii=False, indent=2)
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def ok(data: Any) -> Dict[str, Any]:
    """Build success response envelope."""
    return {"success": True, "data": data, "error": None}


def fail(code: str, message: str) -> Dict[str, Any]:
    """Build error response envelope."""
    return {"success": False, "data": None, "error": {"code": code, "message": message}}


def normalize_text(value: Any) -> str:
    """Normalize arbitrary value into stripped string."""
    if value is None:
        return ""
    return str(value).strip()


def safe_get(obj: Any, key: str, default: Any = None) -> Any:
    """Safe dict get."""
    if not isinstance(obj, dict):
        return default
    return obj.get(key, default)


def confidence_from_score(score: float) -> str:
    """Map numeric score to confidence label."""
    if score >= 0.8:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"


def flatten_json(value: Any, prefix: str = "") -> List[Tuple[str, Any]]:
    """
    Flatten nested JSON-like structures into (path, value) pairs.

    Lists use [index] notation. Dicts use dot notation.
    """
    items: List[Tuple[str, Any]] = []

    if isinstance(value, dict):
        for key, sub_value in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else key
            items.extend(flatten_json(sub_value, next_prefix))
        if not value and prefix:
            items.append((prefix, {}))
        return items

    if isinstance(value, list):
        if not value:
            items.append((prefix, []))
            return items
        for index, sub_value in enumerate(value):
            next_prefix = f"{prefix}[{index}]"
            items.extend(flatten_json(sub_value, next_prefix))
        return items

    items.append((prefix, value))
    return items


def summarize_value(value: Any, max_len: int = 180) -> Any:
    """Summarize long values to keep diff output compact."""
    if isinstance(value, str):
        text = value.strip()
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."
    return value


def env_bool(name: str, default: bool = False) -> bool:
    """Read boolean from environment variables."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}