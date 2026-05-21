# -*- coding: utf-8 -*-

import json
import sys
from pathlib import Path
from typing import Any, Dict

from config import CATALOG_SEARCH_HEADLESS

# On Windows always default to headless — no display server available on Windows Server
_WINDOWS_DEFAULT_HEADLESS = sys.platform == "win32"


SETTINGS_FILE = "catalog_search_settings.json"


def get_settings_path() -> Path:
    return Path.cwd() / SETTINGS_FILE


def load_catalog_search_settings() -> Dict[str, Any]:
    path = get_settings_path()
    data: Dict[str, Any] = {}

    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    default_headless = _WINDOWS_DEFAULT_HEADLESS or CATALOG_SEARCH_HEADLESS
    return {
        "headless": bool(data.get("headless", default_headless)),
    }


def is_catalog_search_headless() -> bool:
    return bool(load_catalog_search_settings().get("headless"))


def set_catalog_search_headless(enabled: bool) -> None:
    path = get_settings_path()
    settings = load_catalog_search_settings()
    settings["headless"] = bool(enabled)
    path.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
