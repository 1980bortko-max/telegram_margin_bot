# -*- coding: utf-8 -*-

import json
from typing import Any, Dict, List

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import GOOGLE_JSON_FILE, GOOGLE_SHEET_URL

CATALOGS_FILE = "catalogs.json"


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def unique_sorted(values: List[Any]) -> List[str]:
    result = []
    seen = set()

    for value in values:
        text = normalize_text(value)
        if not text:
            continue

        key = text.lower()
        if key in seen:
            continue

        seen.add(key)
        result.append(text)

    result.sort(key=lambda x: x.lower())
    return result


def sheet_to_dicts(ws) -> List[Dict[str, Any]]:
    values = ws.get_all_values()

    if not values:
        return []

    headers = values[0]
    rows = []

    for row in values[1:]:
        row_extended = row + [""] * (len(headers) - len(row))
        rows.append(dict(zip(headers, row_extended[:len(headers)])))

    return rows


def get_google_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON_FILE, scope)
    return gspread.authorize(creds)


def get_spreadsheet():
    client = get_google_client()
    return client.open_by_url(GOOGLE_SHEET_URL)


def get_sheet_column_values(sheet_name: str, column_name: str) -> List[str]:
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet(sheet_name)
    rows = sheet_to_dicts(ws)

    values = [row.get(column_name, "") for row in rows]
    return unique_sorted(values)


def get_managers() -> List[str]:
    return get_sheet_column_values("manager", "manager")


def get_client_types() -> List[str]:
    return get_sheet_column_values("client_types", "client_types")


def get_survey_client_groups() -> List[str]:
    return get_sheet_column_values("client_groups", "client_groups")


def get_revenue_ranges() -> List[str]:
    return get_sheet_column_values("revenue_ranges", "revenue_ranges")


def get_orders_ranges() -> List[str]:
    return get_sheet_column_values("orders_ranges", "orders_ranges")


def get_debounce_percent_ranges() -> List[str]:
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet("debounce_percent")
    values = ws.get_all_values()

    if not values:
        return []

    result = []

    for row in values[1:]:
        if not row:
            continue

        value = row[0].strip() if len(row) > 0 else ""
        if value:
            result.append(value)

    return unique_sorted(result)


def get_debounce_days_ranges() -> List[str]:
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet("debounce_days")
    values = ws.get_all_values()

    if not values:
        return []

    result = []

    for row in values[1:]:
        if not row:
            continue

        value = row[0].strip() if len(row) > 0 else ""
        if value:
            result.append(value)

    return unique_sorted(result)


def get_returns_percent_ranges() -> List[str]:
    return get_sheet_column_values("returns_percent", "returns_percent")


def get_focus_values() -> List[str]:
    return get_sheet_column_values("focus_values", "focus_values")


def get_logistics_zones() -> List[str]:
    return get_sheet_column_values("logistics_zones", "logistics_zones")


def get_oms_price_groups() -> List[str]:
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet("цінова група OMS")
    values = ws.get_all_values()

    if not values:
        return []

    result = []

    for row in values[1:]:
        if not row:
            continue

        value = row[0].strip() if len(row) > 0 else ""
        if value:
            result.append(value)

    return unique_sorted(result)


def get_nextis_price_groups() -> List[str]:
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet("цінова група Nextis")
    values = ws.get_all_values()

    if not values:
        return []

    result = []

    for row in values[1:]:
        if not row:
            continue

        value = row[0].strip() if len(row) > 0 else ""
        if value:
            result.append(value)

    return unique_sorted(result)


def get_calc_client_groups() -> List[str]:
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet("dynamic_margin_conditions")
    rows = sheet_to_dicts(ws)

    values = [row.get("client_group", "") for row in rows]
    return unique_sorted(values)


def get_suppliers_from_rules() -> List[str]:
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet("dynamic_margin_rules")
    rows = sheet_to_dicts(ws)

    values = []
    for row in rows:
        raw = normalize_text(row.get("suppliers", ""))
        if not raw:
            continue
        parts = [x.strip() for x in raw.split(";") if x.strip()]
        values.extend(parts)

    return unique_sorted(values)


def get_brands_from_rules() -> List[str]:
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet("dynamic_margin_rules")
    rows = sheet_to_dicts(ws)

    values = []
    for row in rows:
        raw = normalize_text(row.get("brands", ""))
        if not raw:
            continue
        parts = [x.strip() for x in raw.split(";") if x.strip()]
        values.extend(parts)

    return unique_sorted(values)


def get_categories_from_rules() -> List[str]:
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet("dynamic_margin_rules")
    rows = sheet_to_dicts(ws)

    values = []
    for row in rows:
        raw = normalize_text(row.get("categories", ""))
        if not raw:
            continue
        parts = [x.strip() for x in raw.split(";") if x.strip()]
        values.extend(parts)

    return unique_sorted(values)


def build_catalogs() -> Dict[str, List[str]]:
    return {
        # калькулятор
        "calc_client_groups": get_calc_client_groups(),
        "suppliers": get_suppliers_from_rules(),
        "categories": get_categories_from_rules(),
        "brands": get_brands_from_rules(),

        # опитувальник
        "survey_client_groups": get_survey_client_groups(),
        "client_types": get_client_types(),
        "managers": get_managers(),
        "revenue_ranges": get_revenue_ranges(),
        "orders_ranges": get_orders_ranges(),
        "debounce_percent_ranges": get_debounce_percent_ranges(),
        "debounce_days_ranges": get_debounce_days_ranges(),
        "returns_percent_ranges": get_returns_percent_ranges(),
        "focus_values": get_focus_values(),
        "logistics_zones": get_logistics_zones(),

        # окремі довідники для OMS / Nextis
        "oms_price_groups": get_oms_price_groups(),
        "nextis_price_groups": get_nextis_price_groups(),
    }


def save_catalogs() -> Dict[str, List[str]]:
    catalogs = build_catalogs()

    with open(CATALOGS_FILE, "w", encoding="utf-8") as f:
        json.dump(catalogs, f, ensure_ascii=False, indent=2)

    return catalogs
def validate_catalogs(catalogs: Dict[str, List[str]]) -> List[str]:
    errors = []

    required_catalogs = {
        "client_types": "Типи клієнтів",
        "survey_client_groups": "Клієнтські групи (опитувальник)",
        "managers": "Менеджери",
        "revenue_ranges": "Виручка",
        "orders_ranges": "Кількість замовлень",
        "debounce_percent_ranges": "% дебіторки",
        "debounce_days_ranges": "Дні дебіторки",
        "returns_percent_ranges": "% повернень",
        "focus_values": "Фокус",
        "logistics_zones": "Логістичні зони",
        "oms_price_groups": "OMS групи",
        "nextis_price_groups": "Nextis групи",
    }

    for key, name in required_catalogs.items():
        values = catalogs.get(key)

        if not values:
            errors.append(f"{name} — порожній")

    return errors

def load_catalogs() -> Dict[str, List[str]]:
    try:
        with open(CATALOGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
