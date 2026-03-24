import os
from pathlib import Path


def load_env_file() -> None:
    """
    简单读取同级 skill 根目录下的 .env 文件。
    不依赖 python-dotenv，避免增加安装成本。
    """
    current = Path(__file__).resolve()
    skill_root = current.parent.parent
    env_path = skill_root / ".env"

    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default)