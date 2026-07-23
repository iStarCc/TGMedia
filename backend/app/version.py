import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _version_file_candidates() -> list[Path]:
    base = Path(__file__).resolve().parent.parent
    return [
        base / "version.json",
        base.parent / "version.json",
    ]


def find_version_file() -> Path:
    for path in _version_file_candidates():
        if path.is_file():
            return path
    raise FileNotFoundError("version.json not found")


@lru_cache
def load_version_data() -> dict[str, Any]:
    data = json.loads(find_version_file().read_text(encoding="utf-8"))
    if not data.get("version"):
        raise ValueError("version.json missing version field")
    return data


def get_app_version() -> str:
    return load_version_data()["version"]


APP_VERSION: str = get_app_version()
