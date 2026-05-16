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
    return [item.strip() for item in text.split(";") if item.strip()]


def value_matches(user_value, rule_value):
    user_value = normalize_text(user_value)
    rule_items = split_multi_value(rule_value)

    if not user_value:
        return False

    for item in rule_items:
        if item.lower() == user_value.lower():
            return True

    return False


def has_value(value):
    return normalize_text(value) != ""


def has_real_values(value):
    return len(split_multi_value(value)) > 0


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


def load_data():
    client = get_google_client()
    spreadsheet = client.open_by_url(GOOGLE_SHEET_URL)

    ws_rules = spreadsheet.worksheet("dynamic_margin_rules")
    ws_conditions = spreadsheet.worksheet("dynamic_margin_conditions")
    ws_priority = spreadsheet.worksheet("priority_order")

    rules = sheet_to_dicts(ws_rules)
    conditions = sheet_to_dicts(ws_conditions)
    priorities = sheet_to_dicts(ws_priority)

    return rules, conditions, priorities


def rule_type_allowed(rule_type, supplier, category, brand):
    has_supplier = has_value(supplier)
    has_category = has_value(category)
    has_brand = has_value(brand)

    if rule_type == "supplier+category+brand":
        return has_supplier and has_category and has_brand

    if rule_type == "supplier+category":
        return has_supplier and has_category and not has_brand

    if rule_type == "supplier+brand":
        return has_supplier and has_brand and not has_category

    if rule_type == "category+brand":
        return has_category and has_brand and not has_supplier

    if rule_type == "supplier":
        return has_supplier and not has_category and not has_brand

    if rule_type == "category":
        return has_category and not has_supplier and not has_brand

    if rule_type == "brand":
        return has_brand and not has_supplier and not has_category

    if rule_type == "global":
        return not has_supplier and not has_category and not has_brand

    return False


def rule_matches(rule_type, rule_row, supplier, category, brand):
    supplier_rule = rule_row.get("suppliers", "")
    category_rule = rule_row.get("categories", "")
    brand_rule = rule_row.get("brands", "")

    has_supplier_rule = has_real_values(supplier_rule)
    has_category_rule = has_real_values(category_rule)
    has_brand_rule = has_real_values(brand_rule)

    if rule_type == "supplier+category+brand":
        return (
            has_supplier_rule
            and has_category_rule
            and has_brand_rule
            and value_matches(supplier, supplier_rule)
            and value_matches(category, category_rule)
            and value_matches(brand, brand_rule)
        )

    if rule_type == "supplier+category":
        return (
            has_supplier_rule
            and has_category_rule
            and not has_brand_rule
            and value_matches(supplier, supplier_rule)
            and value_matches(category, category_rule)
        )

    if rule_type == "supplier+brand":
        return (
            has_supplier_rule
            and not has_category_rule
            and has_brand_rule
            and value_matches(supplier, supplier_rule)
            and value_matches(brand, brand_rule)
        )

    if rule_type == "category+brand":
        return (
            not has_supplier_rule
            and has_category_rule
            and has_brand_rule
            and value_matches(category, category_rule)
            and value_matches(brand, brand_rule)
        )

    if rule_type == "supplier":
        return (
            has_supplier_rule
            and not has_category_rule
            and not has_brand_rule
            and value_matches(supplier, supplier_rule)
        )

    if rule_type == "category":
        return (
            not has_supplier_rule
            and has_category_rule
            and not has_brand_rule
            and value_matches(category, category_rule)
        )

    if rule_type == "brand":
        return (
            not has_supplier_rule
            and not has_category_rule
            and has_brand_rule
            and value_matches(brand, brand_rule)
        )

    if rule_type == "global":
        return (
            not has_supplier_rule
            and not has_category_rule
            and not has_brand_rule
        )

    return False


def find_matching_margin(rules, priorities, supplier, category, brand):
    active_priorities = [
        row for row in priorities
        if normalize_text(row.get("is_active", "")).upper() == "TRUE"
    ]

    def priority_sort_key(row):
        value = normalize_text(row.get("priority_order", "9999"))
        try:
            return int(value)
        except Exception:
            return 9999

    active_priorities.sort(key=priority_sort_key)

    for priority_row in active_priorities:
        rule_type = normalize_text(priority_row.get("rule_type", "")).lower()

        if not rule_type_allowed(rule_type, supplier, category, brand):
            continue

        for rule_row in rules:
            if rule_matches(rule_type, rule_row, supplier, category, brand):
                return {
                    "margin_name": normalize_text(rule_row.get("margin_name", "")),
                    "rule_type": rule_type,
                    "rule_row": rule_row
                }

    return None


def to_float(value):
    if value is None:
        return None

    text = str(value).strip()

    if text == "":
        return None

    text = text.replace(" ", "")

    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")

    try:
        return float(text)
    except Exception:
        return None


def find_condition(conditions, margin_name, client_group, cost):
    matched = []

    for row in conditions:
        row_margin_name = normalize_text(row.get("margin_name", ""))
        row_client_group = normalize_text(row.get("client_group", ""))

        if row_margin_name.lower() != normalize_text(margin_name).lower():
            continue

        if row_client_group.lower() != normalize_text(client_group).lower():
            continue

        cost_from = to_float(row.get("cost_from", ""))
        cost_to = to_float(row.get("cost_to", ""))
        margin_percent = to_float(row.get("margin_percent", ""))

        if cost_from is None or cost_to is None or margin_percent is None:
            continue

        if cost_from <= cost <= cost_to:
            matched.append({
                "cost_from": cost_from,
                "cost_to": cost_to,
                "margin_percent": margin_percent,
                "row": row
            })

    if not matched:
        return None

    matched.sort(key=lambda x: x["cost_from"], reverse=True)
    return matched[0]


def calculate_sale_price(cost, margin_percent):
    return round(cost * (1 + margin_percent / 100), 2)


def calculate_margin_result(supplier, category, brand, client_group, cost):
    rules, conditions, priorities = load_data()

    matched_margin = find_matching_margin(
        rules=rules,
        priorities=priorities,
        supplier=supplier,
        category=category,
        brand=brand
    )

    if not matched_margin:
        matched_margin = find_matching_margin(
            rules=rules,
            priorities=priorities,
            supplier="",
            category="",
            brand=""
        )

        if not matched_margin:
            return {
                "success": False,
                "message": "Не знайдено відповідну dynamic margin rule"
            }

        matched_margin["rule_type"] = "GLOBAL fallback"

    margin_name = matched_margin["margin_name"]
    rule_type = matched_margin["rule_type"]

    matched_condition = find_condition(
        conditions=conditions,
        margin_name=margin_name,
        client_group=client_group,
        cost=cost
    )

    if not matched_condition:
        return {
            "success": False,
            "message": "Dynamic margin знайдена, але не знайдено condition по client_group/cost",
            "margin_name": margin_name,
            "rule_type": rule_type
        }

    margin_percent = matched_condition["margin_percent"]
    sale_price = calculate_sale_price(cost, margin_percent)

    return {
        "success": True,
        "margin_name": margin_name,
        "rule_type": rule_type,
        "client_group": client_group,
        "cost": cost,
        "margin_percent": margin_percent,
        "sale_price": sale_price
    }
