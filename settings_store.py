from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SETTINGS_PATH = Path(__file__).with_name("tittytatter.settings.json")


def load_settings() -> dict[str, Any]:
    if not SETTINGS_PATH.exists():
        return {}
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_settings(data: dict[str, Any]) -> None:
    temp = SETTINGS_PATH.with_suffix(".json.tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(SETTINGS_PATH)


def delete_settings() -> bool:
    try:
        SETTINGS_PATH.unlink(missing_ok=True)
        return True
    except Exception:
        return False
