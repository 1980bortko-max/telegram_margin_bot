# -*- coding: utf-8 -*-

import os

from dotenv import load_dotenv


load_dotenv()


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


def get_optional_env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "так", "y")


def get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


TOKEN = get_required_env("BOT_TOKEN")
GOOGLE_SHEET_URL = get_required_env("GOOGLE_SHEET_URL")
GOOGLE_JSON_FILE = get_required_env("GOOGLE_JSON_FILE")
SURVEY_SPREADSHEET_URL = get_required_env("SURVEY_SPREADSHEET_URL")
INDIVIDUAL_SHEET_URL = get_required_env("INDIVIDUAL_SHEET_URL")

AUTOFUN_BASE_URL = get_optional_env("AUTOFUN_BASE_URL", "https://cs.autofun.at")
AF_IDS_USERNAME = get_optional_env("AF_IDS_USERNAME") or get_optional_env("AF_IDS_USER", "Oleksandr.Bortko")
AF_IDS_PASSWORD = get_optional_env("AF_IDS_PASSWORD") or get_optional_env("AF_IDS_PASS")
CHROME_BIN = get_optional_env(
    "CHROME_BIN",
    "/Users/aleksandrbortko/Downloads/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
)
CHROMEDRIVER_PATH = get_optional_env(
    "CHROMEDRIVER_PATH",
    "/Users/aleksandrbortko/Downloads/chromedriver-mac-arm64/chromedriver",
)
CATALOG_CHROME_PROFILE_DIR = get_optional_env("CATALOG_CHROME_PROFILE_DIR", ".crm_chrome_profile")
CATALOG_DEBUG_DIR = get_optional_env("CATALOG_DEBUG_DIR", "catalog_search_debug")
CATALOG_SEARCH_HEADLESS = get_bool_env("CATALOG_SEARCH_HEADLESS", False)
CATALOG_SEARCH_LIMIT = get_int_env("CATALOG_SEARCH_LIMIT", 20)
