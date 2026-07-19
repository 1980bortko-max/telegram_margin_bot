# -*- coding: utf-8 -*-

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import GOOGLE_JSON_FILE, GOOGLE_SHEET_URL


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip()


def split_multi_value(value):
    text = normalize_text(value)
    if not text:
        return []

    parts = text.split(";")
    result = []

    for item in parts:
        clean_item = item.strip()
        if clean_item:
            result.append(clean_item)

    return result


def get_google_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON_FILE, scope)
    return gspread.authorize(creds)


def sheet_to_dicts(ws):
    values = ws.get_all_values()
    if not values:
        return []

    headers = values[0]
    rows = values[1:]

    result = []
    for row in rows:
        row_extended = row + [""] * (len(headers) - len(row))
        result.append(dict(zip(headers, row_extended[:len(headers)])))

    return result


def load_rules_and_conditions():
    client = get_google_client()
    spreadsheet = client.open_by_url(GOOGLE_SHEET_URL)

    ws_rules = spreadsheet.worksheet("dynamic_margin_rules")
    ws_conditions = spreadsheet.worksheet("dynamic_margin_conditions")

    rules = sheet_to_dicts(ws_rules)
    conditions = sheet_to_dicts(ws_conditions)

    return rules, conditions


def unique_sorted(values):
    cleaned = []
    seen = set()

    for value in values:
        text = normalize_text(value)
        if not text:
            continue

        key = text.lower()
        if key in seen:
            continue

        seen.add(key)
        cleaned.append(text)

    cleaned.sort(key=lambda x: x.lower())
    return cleaned


def build_suppliers_catalog(rules):
    items = []

    for row in rules:
        for supplier in split_multi_value(row.get("suppliers", "")):
            items.append(supplier)

    return unique_sorted(items)


def build_categories_catalog(rules):
    items = []

    for row in rules:
        for category in split_multi_value(row.get("categories", "")):
            items.append(category)

    return unique_sorted(items)


def build_brands_catalog(rules):
    items = []

    for row in rules:
        for brand in split_multi_value(row.get("brands", "")):
            items.append(brand)

    return unique_sorted(items)


def build_client_groups_catalog(conditions):
    items = []

    for row in conditions:
        client_group = normalize_text(row.get("client_group", ""))
        if client_group:
            items.append(client_group)

    return unique_sorted(items)


def build_all_catalogs():
    rules, conditions = load_rules_and_conditions()

    catalogs = {
        "suppliers": build_suppliers_catalog(rules),
        "categories": build_categories_catalog(rules),
        "brands": build_brands_catalog(rules),
        "client_groups": build_client_groups_catalog(conditions)
    }

    return catalogs


if __name__ == "__main__":
    catalogs = build_all_catalogs()

    print("=== CATALOGS ===")
    print("Suppliers:", len(catalogs["suppliers"]))
    for item in catalogs["suppliers"]:
        print(" -", item)

    print("\nCategories:", len(catalogs["categories"]))
    for item in catalogs["categories"]:
        print(" -", item)

    print("\nBrands:", len(catalogs["brands"]))
    for item in catalogs["brands"]:
        print(" -", item)

    print("\nClient groups:", len(catalogs["client_groups"]))
    for item in catalogs["client_groups"]:
        print(" -", item)
