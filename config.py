# -*- coding: utf-8 -*-

import os

from dotenv import load_dotenv


load_dotenv()


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


TOKEN = get_required_env("BOT_TOKEN")
GOOGLE_SHEET_URL = get_required_env("GOOGLE_SHEET_URL")
GOOGLE_JSON_FILE = get_required_env("GOOGLE_JSON_FILE")
SURVEY_SPREADSHEET_URL = get_required_env("SURVEY_SPREADSHEET_URL")
INDIVIDUAL_SHEET_URL = get_required_env("INDIVIDUAL_SHEET_URL")
