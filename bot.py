# -*- coding: utf-8 -*-

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from config import TOKEN, GOOGLE_SHEET_URL, INDIVIDUAL_SHEET_URL
from catalogs_storage import (
    save_catalogs,
    load_catalogs,
    validate_catalogs,
    get_google_client,
    sheet_to_dicts,
)
from catalogs import (
    load_rules_and_conditions,
    split_multi_value,
)
from margin_logic import calculate_margin_result
from survey_logic import start_survey, handle_survey_message, is_survey_active


bot = Bot(token=TOKEN)
dp = Dispatcher()

PAGE_SIZE = 10
PAGE_SIZE_ACCESS = 6
VAT_RATE = 0.20

user_state: Dict[int, Dict[str, Any]] = {}
authorized_users_cache: Dict[int, Dict[str, Any]] = {}

INDIVIDUAL_SHEET_NAME = "Лист1"
PROMO_SHEET_NAME = "PROMO"
DEPARTMENTS_SHEET_NAME = "departments"

INDIVIDUAL_ACCESS_COLUMN = "Кнопка - індивідуальна націнка - ТАК"
PROMO_ACCESS_COLUMN = "Кнопка - промокод"

DEFAULT_DEPARTMENTS = [
    "Filial",
    "Callcenter",
    "Watsapp",
    "Partselection",
    "Manager",
]

INDIVIDUAL_FIELDS = [
    "client_name",
    "client_phone",
    "client_uuid",
    "brand",
    "reason",
    "markup",
    "competitor",
    "client_group",
]

INDIVIDUAL_TITLES = {
    "client_name": "Найменування клієнта",
    "client_phone": "Телефон клієнта",
    "client_uuid": "UID клієнта",
    "brand": "Бренд для зміни",
    "reason": "Причина зміни",
    "markup": "Зміна націнки (%)",
    "competitor": "Конкурент",
    "client_group": "Клієнтська поточна цінова група",
}

PROMO_BASE_FIELDS = [
    "client_name",
    "client_phone",
    "client_uuid",
    "manager_first_name",
    "manager_last_name",
    "department",
    "description",
    "dissatisfaction_level",
    "discount_amount",
]

PROMO_TITLES = {
    "client_name": "Найменування клієнта",
    "client_phone": "Телефон клієнта",
    "client_uuid": "UID клієнта",
    "manager_first_name": "Ім’я менеджера",
    "manager_last_name": "Прізвище менеджера",
    "department": "Оберіть департамент",
    "description": "Коротко опишіть проблему, з якою стикнувся клієнт",
    "dissatisfaction_level": "На скільки клієнт залишився незадоволений? Введіть 1, 2 або 3",
    "discount_amount": "Оберіть бажаний розмір знижки по промокоду. Наприклад: 5%, 10%, 15%",
}


after_result_keyboard_user = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔄 Новий розрахунок")],
        [KeyboardButton(text="🔙 Головне меню")],
    ],
    resize_keyboard=True
)

after_result_keyboard_admin = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔄 Новий розрахунок")],
        [KeyboardButton(text="👤 Нові заявки")],
        [KeyboardButton(text="🔙 Головне меню")],
    ],
    resize_keyboard=True
)

cost_keyboard_user = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔄 Новий розрахунок")],
        [KeyboardButton(text="🔙 Головне меню")],
    ],
    resize_keyboard=True
)

cost_keyboard_admin = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔄 Новий розрахунок")],
        [KeyboardButton(text="👤 Нові заявки")],
        [KeyboardButton(text="🔙 Головне меню")],
    ],
    resize_keyboard=True
)

phone_request_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📱 Поділитися номером", request_contact=True)]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

admin_requests_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Додати менеджера")],
        [KeyboardButton(text="⏭ Наступна заявка")],
        [KeyboardButton(text="🔙 Головне меню")],
    ],
    resize_keyboard=True
)

access_action_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Увімкнути доступ")],
        [KeyboardButton(text="❌ Вимкнути доступ")],
        [KeyboardButton(text="🔙 До списку менеджерів")],
        [KeyboardButton(text="🔙 Головне меню")],
    ],
    resize_keyboard=True
)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def norm_cmd(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    while "  " in text:
        text = text.replace("  ", " ")
    return text


def normalize_header(value: Any) -> str:
    text = norm_cmd(value)
    text = text.replace('"', "")
    text = text.replace("'", "")
    return text


def normalize_phone(phone: Any) -> str:
    value = normalize_text(phone)

    if value == "":
        return ""

    value = value.replace(" ", "")
    value = value.replace("-", "")
    value = value.replace("(", "")
    value = value.replace(")", "")

    if value.startswith("+"):
        digits = "+" + "".join(ch for ch in value[1:] if ch.isdigit())
    else:
        digits = "".join(ch for ch in value if ch.isdigit())

    if digits.startswith("380") and not digits.startswith("+380"):
        digits = "+" + digits

    if digits.startswith("0") and len(digits) == 10:
        digits = "+38" + digits

    return digits


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


def parse_cost(text: str) -> float:
    value = normalize_text(text)

    if value == "":
        raise ValueError("Порожнє значення")

    value = value.replace(" ", "")

    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")

    cost = float(value)

    if cost < 0:
        raise ValueError("Від’ємне значення")

    return cost


def is_active_flag(value: Any) -> bool:
    return normalize_text(value).upper() in ("TRUE", "ТАК", "YES", "1")


def col_to_letter(col_num: int) -> str:
    result = ""
    while col_num > 0:
        col_num, rem = divmod(col_num - 1, 26)
        result = chr(65 + rem) + result
    return result


def find_header_index(headers: List[str], aliases: List[str]) -> Optional[int]:
    normalized_headers = [normalize_header(h) for h in headers]

    for alias in aliases:
        alias_norm = normalize_header(alias)

        for idx, header in enumerate(normalized_headers):
            if header == alias_norm:
                return idx

        for idx, header in enumerate(normalized_headers):
            if alias_norm and alias_norm in header:
                return idx

    return None


def find_header_col_number(headers: List[str], aliases: List[str]) -> Optional[int]:
    idx = find_header_index(headers, aliases)
    if idx is None:
        return None
    return idx + 1


def get_next_empty_row(ws) -> int:
    values = ws.get_all_values()
    return len(values) + 1


def get_spreadsheet():
    client = get_google_client()
    return client.open_by_url(GOOGLE_SHEET_URL)


def get_individual_spreadsheet():
    client = get_google_client()
    return client.open_by_url(INDIVIDUAL_SHEET_URL)


def load_allowed_users():
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet("allowed_users")
    rows = sheet_to_dicts(ws)
    return rows, ws


def load_allowed_users_with_row_numbers():
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet("allowed_users")
    values = ws.get_all_values()

    if not values:
        return [], ws, []

    headers = values[0]
    rows = []

    for idx, row in enumerate(values[1:], start=2):
        row_extended = row + [""] * (len(headers) - len(row))
        row_dict = dict(zip(headers, row_extended[:len(headers)]))
        row_dict["_row_number"] = idx
        rows.append(row_dict)

    return rows, ws, headers


def load_registration_requests():
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet("registration_requests")
    rows = sheet_to_dicts(ws)
    return rows, ws


def load_registration_requests_with_row_numbers():
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet("registration_requests")
    values = ws.get_all_values()

    if not values:
        return [], ws, []

    headers = values[0]
    rows = []

    for idx, row in enumerate(values[1:], start=2):
        row_extended = row + [""] * (len(headers) - len(row))
        row_dict = dict(zip(headers, row_extended[:len(headers)]))
        row_dict["_row_number"] = idx
        rows.append(row_dict)

    return rows, ws, headers


def get_allowed_user_by_telegram_id(user_id: int) -> Optional[Dict[str, Any]]:
    rows, _ws, _headers = load_allowed_users_with_row_numbers()

    for row in rows:
        row_tg = normalize_text(row.get("telegram_id", ""))
        if row_tg == str(user_id) and is_active_flag(row.get("is_active", "")):
            return row

    return None


def get_allowed_user_profile(user_id: int) -> Dict[str, str]:
    row = get_allowed_user_by_telegram_id(user_id)
    if not row:
        return {
            "full_name": "",
            "first_name": "",
            "last_name": "",
            "department": "",
        }

    return {
        "full_name": normalize_text(row.get("full_name", "")),
        "first_name": normalize_text(row.get("first_name", "")),
        "last_name": normalize_text(row.get("last_name", "")),
        "department": normalize_text(row.get("department", "")),
    }


def authorize_user_session(
    telegram_user_id: int,
    phone: str,
    full_name: str,
    role: str,
    individual_markup_access: bool = False,
    promo_access: bool = False,
):
    authorized_users_cache[telegram_user_id] = {
        "phone": normalize_phone(phone),
        "full_name": normalize_text(full_name),
        "role": normalize_text(role).lower(),
        "is_authorized": True,
        "individual_markup_access": bool(individual_markup_access),
        "promo_access": bool(promo_access),
    }


def get_user_role_from_cache(user_id: int) -> str:
    data = authorized_users_cache.get(user_id)
    if not data:
        return ""
    return normalize_text(data.get("role", "")).lower()


def is_user_authorized(user_id: int) -> bool:
    data = authorized_users_cache.get(user_id)
    if not data:
        return False
    return bool(data.get("is_authorized", False))


def is_admin(user_id: int) -> bool:
    return get_user_role_from_cache(user_id) == "admin"


def has_individual_markup_access(user_id: int) -> bool:
    data = authorized_users_cache.get(user_id, {})
    return bool(data.get("individual_markup_access", False))


def has_promo_access(user_id: int) -> bool:
    data = authorized_users_cache.get(user_id, {})
    return bool(data.get("promo_access", False))


def refresh_user_role_from_google(user_id: int):
    rows, _ws = load_allowed_users()

    for row in rows:
        row_tg = normalize_text(row.get("telegram_id", ""))

        if row_tg == str(user_id) and is_active_flag(row.get("is_active", "")):
            individual_flag = normalize_text(row.get(INDIVIDUAL_ACCESS_COLUMN, "")).upper()
            promo_flag = normalize_text(row.get(PROMO_ACCESS_COLUMN, "")).upper()

            authorize_user_session(
                telegram_user_id=user_id,
                phone=row.get("phone", ""),
                full_name=row.get("full_name", ""),
                role=row.get("role", ""),
                individual_markup_access=individual_flag in ("TRUE", "ТАК"),
                promo_access=promo_flag in ("TRUE", "ТАК"),
            )
            return True

    return False


def find_allowed_user_by_phone(phone: str):
    normalized_phone = normalize_phone(phone)
    rows, _ws = load_allowed_users()

    for row in rows:
        row_phone = normalize_phone(row.get("phone", ""))
        row_is_active = row.get("is_active", "")

        if row_phone == normalized_phone and is_active_flag(row_is_active):
            individual_flag = normalize_text(row.get(INDIVIDUAL_ACCESS_COLUMN, "")).upper()
            promo_flag = normalize_text(row.get(PROMO_ACCESS_COLUMN, "")).upper()

            return {
                "phone": row_phone,
                "full_name": normalize_text(row.get("full_name", "")),
                "role": normalize_text(row.get("role", "")),
                "telegram_id": normalize_text(row.get("telegram_id", "")),
                "individual_markup_access": individual_flag in ("TRUE", "ТАК"),
                "promo_access": promo_flag in ("TRUE", "ТАК"),
            }

    return None


def update_allowed_user_telegram_id_by_phone(phone: str, telegram_id: int):
    normalized_phone = normalize_phone(phone)
    rows, ws, headers = load_allowed_users_with_row_numbers()

    telegram_id_col = find_header_col_number(headers, ["telegram_id"])
    if telegram_id_col is None:
        raise Exception("У листі allowed_users не знайдено колонку telegram_id")

    for row in rows:
        row_phone = normalize_phone(row.get("phone", ""))
        if row_phone == normalized_phone:
            ws.update_cell(row["_row_number"], telegram_id_col, str(telegram_id))
            return True

    return False


def get_admin_telegram_ids() -> List[int]:
    rows, _ws = load_allowed_users()
    result = []

    for row in rows:
        if not is_active_flag(row.get("is_active", "")):
            continue

        if normalize_text(row.get("role", "")).lower() != "admin":
            continue

        telegram_id = normalize_text(row.get("telegram_id", ""))
        if telegram_id.isdigit():
            result.append(int(telegram_id))

    return result


def get_main_keyboard(user_id: int):
    keyboard = [
        [KeyboardButton(text="Оновити довідники")],
        [KeyboardButton(text="Розрахувати ціну")],
        [KeyboardButton(text="📝 Опитувальник")],
    ]

    if has_individual_markup_access(user_id):
        keyboard.append([KeyboardButton(text="💰 Індивідуальна націнка")])

    if has_promo_access(user_id):
        keyboard.append([KeyboardButton(text="🎟 Промокод")])

    if is_admin(user_id):
        keyboard.append([KeyboardButton(text="👤 Нові заявки")])
        keyboard.append([KeyboardButton(text="⚙️ Доступ до індивідуальної націнки")])
        keyboard.append([KeyboardButton(text="🎟 Доступ до промокодів")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )


def get_after_result_keyboard(user_id: int):
    if is_admin(user_id):
        return after_result_keyboard_admin
    return after_result_keyboard_user


def get_cost_keyboard(user_id: int):
    if is_admin(user_id):
        return cost_keyboard_admin
    return cost_keyboard_user


def build_paginated_keyboard(items: List[str], page: int, extra_bottom_buttons=None):
    total = len(items)
    total_pages = (total - 1) // PAGE_SIZE + 1 if total > 0 else 1

    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = items[start:end]

    keyboard_rows = []

    for item in page_items:
        keyboard_rows.append([KeyboardButton(text=item)])

    nav_row = []
    if page > 0:
        nav_row.append(KeyboardButton(text="⬅️ Назад"))
    if end < total:
        nav_row.append(KeyboardButton(text="➡️ Далі"))

    if nav_row:
        keyboard_rows.append(nav_row)

    if extra_bottom_buttons:
        for row in extra_bottom_buttons:
            keyboard_rows.append(row)

    keyboard_rows.append([KeyboardButton(text="🔄 Новий розрахунок")])
    keyboard_rows.append([KeyboardButton(text="🔙 Головне меню")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard_rows,
        resize_keyboard=True
    ), total_pages


def allowed_user_exists(phone: str) -> bool:
    normalized_phone = normalize_phone(phone)
    rows, _ws = load_allowed_users()

    for row in rows:
        row_phone = normalize_phone(row.get("phone", ""))
        if row_phone == normalized_phone:
            return True

    return False


def registration_request_exists(telegram_id: int, phone: str) -> bool:
    rows, _ws = load_registration_requests()
    normalized_phone = normalize_phone(phone)
    telegram_id_text = str(telegram_id)

    for row in rows:
        row_phone = normalize_phone(row.get("phone", ""))
        row_telegram_id = normalize_text(row.get("telegram_id", ""))
        row_status = normalize_text(row.get("status", "")).lower()

        if row_phone == normalized_phone and row_telegram_id == telegram_id_text and row_status in ("new", "pending"):
            return True

    return False


def add_registration_request(user: Dict[str, Any]) -> bool:
    _rows, ws = load_registration_requests()

    phone = normalize_phone(user.get("phone", ""))
    telegram_id = str(user.get("telegram_id", ""))
    username = normalize_text(user.get("username", ""))
    full_name = normalize_text(user.get("full_name", ""))

    if registration_request_exists(int(telegram_id), phone):
        return False

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ws.append_row(
        [created_at, telegram_id, username, full_name, phone, "new"],
        value_input_option="USER_ENTERED"
    )

    return True


def get_new_requests():
    rows, _ws, _headers = load_registration_requests_with_row_numbers()
    result = []

    for row in rows:
        if normalize_text(row.get("status", "")).lower() == "new":
            result.append(row)

    return result


def append_allowed_user_from_request(request_row: Dict[str, Any]):
    phone = normalize_phone(request_row.get("phone", ""))
    full_name = normalize_text(request_row.get("full_name", ""))
    telegram_id = normalize_text(request_row.get("telegram_id", ""))

    if allowed_user_exists(phone):
        return False, "Користувач уже є в allowed_users"

    _rows, ws, headers = load_allowed_users_with_row_numbers()
    if not headers:
        raise Exception("У листі allowed_users немає заголовків")

    values_by_header = {
        "phone": phone,
        "full_name": full_name,
        "role": "manager",
        "is_active": "TRUE",
        "telegram_id": telegram_id,
        INDIVIDUAL_ACCESS_COLUMN: "",
        "first_name": "",
        "last_name": "",
        "department": "",
        PROMO_ACCESS_COLUMN: "",
    }

    row = []
    for header in headers:
        row.append(values_by_header.get(header, values_by_header.get(normalize_text(header), "")))

    ws.append_row(row, value_input_option="USER_ENTERED")
    return True, "Менеджера додано в allowed_users"


def approve_request(row_number: int):
    _rows, ws, headers = load_registration_requests_with_row_numbers()

    status_col = find_header_col_number(headers, ["status"])
    if status_col is None:
        raise Exception("У листі registration_requests не знайдено колонку status")

    ws.update_cell(row_number, status_col, "approved")


async def notify_admin_about_request(user: Dict[str, Any]):
    username = f"@{user['username']}" if user.get("username") else "немає"

    text = (
        "📩 Новий запит на доступ до бота\n\n"
        f"Ім'я: {user.get('full_name', '')}\n"
        f"Username: {username}\n"
        f"Telegram ID: {user.get('telegram_id', '')}\n"
        f"Телефон: {user.get('phone', '')}\n"
        f"Статус: new"
    )

    for admin_id in get_admin_telegram_ids():
        try:
            await bot.send_message(chat_id=admin_id, text=text)
        except Exception:
            pass


async def require_phone_verification(message: types.Message):
    user_state[message.from_user.id] = {"step": "await_phone"}

    await message.answer(
        "🔐 Для доступу до бота потрібно пройти авторизацію.\n\n"
        "Натисни кнопку нижче, щоб поділитися своїм номером телефону.",
        reply_markup=phone_request_keyboard
    )


async def show_next_registration_request(message: types.Message, request_index: int = 0):
    new_requests = get_new_requests()

    if not new_requests:
        await message.answer("✅ Нових заявок немає.", reply_markup=get_main_keyboard(message.from_user.id))
        return

    if request_index < 0:
        request_index = 0

    if request_index >= len(new_requests):
        request_index = 0

    request_row = new_requests[request_index]

    user_state[message.from_user.id] = {
        "step": "admin_review_requests",
        "request_index": request_index,
        "request_row_number": request_row["_row_number"],
        "request_phone": normalize_phone(request_row.get("phone", "")),
        "request_full_name": normalize_text(request_row.get("full_name", "")),
        "request_username": normalize_text(request_row.get("username", "")),
        "request_telegram_id": normalize_text(request_row.get("telegram_id", "")),
    }

    username = f"@{request_row.get('username', '')}" if normalize_text(request_row.get("username", "")) else "немає"

    text = (
        f"👤 Заявка {request_index + 1} з {len(new_requests)}\n\n"
        f"Ім'я: {normalize_text(request_row.get('full_name', ''))}\n"
        f"Username: {username}\n"
        f"Telegram ID: {normalize_text(request_row.get('telegram_id', ''))}\n"
        f"Телефон: {normalize_phone(request_row.get('phone', ''))}\n"
        f"Статус: {normalize_text(request_row.get('status', ''))}"
    )

    await message.answer(text, reply_markup=admin_requests_keyboard)


def get_access_column_index(headers: List[str], column_name: str) -> Optional[int]:
    for idx, header in enumerate(headers, start=1):
        if normalize_text(header) == column_name:
            return idx
    return None


def get_managers_for_access(column_name: str):
    rows, _ws, _headers = load_allowed_users_with_row_numbers()
    result = []

    for row in rows:
        if not is_active_flag(row.get("is_active", "")):
            continue

        role = normalize_text(row.get("role", "")).lower()
        if role not in ("manager", "top_manager"):
            continue

        full_name = normalize_text(row.get("full_name", ""))
        phone = normalize_phone(row.get("phone", ""))
        telegram_id = normalize_text(row.get("telegram_id", ""))
        access = normalize_text(row.get(column_name, "")).upper() in ("TRUE", "ТАК")

        if not full_name:
            full_name = phone if phone else telegram_id

        result.append({
            "row_number": row.get("_row_number"),
            "full_name": full_name,
            "phone": phone,
            "telegram_id": telegram_id,
            "access": access,
        })

    return result


def filter_access_managers(managers: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    if not query:
        return managers

    normalized_query = normalize_text(query).lower()
    filtered = []

    for manager in managers:
        full_name = normalize_text(manager.get("full_name", "")).lower()
        phone = normalize_text(manager.get("phone", "")).lower()
        telegram_id = normalize_text(manager.get("telegram_id", "")).lower()

        if (
            normalized_query in full_name
            or normalized_query in phone
            or normalized_query in telegram_id
        ):
            filtered.append(manager)

    return filtered


def build_access_managers_keyboard(managers: List[Dict[str, Any]], page: int = 0):
    total = len(managers)
    total_pages = (total - 1) // PAGE_SIZE_ACCESS + 1 if total > 0 else 1

    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1

    start = page * PAGE_SIZE_ACCESS
    end = start + PAGE_SIZE_ACCESS
    page_managers = managers[start:end]

    keyboard_rows = []
    for manager in page_managers:
        status = "✅" if manager.get("access") else "❌"
        keyboard_rows.append([
            KeyboardButton(text=f"{status} {manager.get('full_name', '')}")
        ])

    nav_row = []
    if page > 0:
        nav_row.append(KeyboardButton(text="⬅️ Назад"))
    if end < total:
        nav_row.append(KeyboardButton(text="➡️ Далі"))

    if nav_row:
        keyboard_rows.append(nav_row)

    keyboard_rows.append([KeyboardButton(text="🔎 Пошук менеджера")])
    keyboard_rows.append([KeyboardButton(text="🔙 Головне меню")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard_rows,
        resize_keyboard=True
    ), total_pages


async def show_access_managers(message: types.Message, access_type: str, page: int = 0, query: str = ""):
    if access_type == "individual":
        column_name = INDIVIDUAL_ACCESS_COLUMN
        title = "💰 Індивідуальна націнка"
        step = "individual_access_select_manager"
    elif access_type == "promo":
        column_name = PROMO_ACCESS_COLUMN
        title = "🎟 Промокод"
        step = "promo_access_select_manager"
    else:
        await message.answer("❌ Невідомий тип доступу", reply_markup=get_main_keyboard(message.from_user.id))
        return

    managers = get_managers_for_access(column_name)

    if not managers:
        await message.answer(
            "❌ Немає активних менеджерів у allowed_users.",
            reply_markup=get_main_keyboard(message.from_user.id)
        )
        return

    filtered_managers = filter_access_managers(managers, query)
    if not filtered_managers:
        user_state[message.from_user.id] = {
            "step": step,
            "access_type": access_type,
            "access_column": column_name,
            "managers": managers,
            "filtered_managers": [],
            "page": 0,
            "query": query,
        }

        await message.answer(
            f"❌ Менеджерів за запитом '{query}' не знайдено. Спробуйте інший запит.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="🔎 Пошук менеджера")],
                    [KeyboardButton(text="🔙 Головне меню")],
                ],
                resize_keyboard=True
            )
        )
        return

    keyboard, total_pages = build_access_managers_keyboard(filtered_managers, page)
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1

    user_state[message.from_user.id] = {
        "step": step,
        "access_type": access_type,
        "access_column": column_name,
        "managers": managers,
        "filtered_managers": filtered_managers,
        "page": page,
        "query": query,
    }

    page_text = f"\nСторінка {page + 1} з {total_pages}" if total_pages > 1 else ""
    search_text = f"\nПошук: {query}" if query else ""

    await message.answer(
        f"Оберіть менеджера, якому потрібно увімкнути або вимкнути кнопку:\n{title}{page_text}{search_text}",
        reply_markup=keyboard
    )


async def show_access_actions(message: types.Message, manager: Dict[str, Any], access_type: str, access_column: str):
    user_state[message.from_user.id] = {
        "step": "access_action",
        "access_type": access_type,
        "access_column": access_column,
        "selected_manager": manager,
    }

    access_text = "✅ Увімкнено" if manager.get("access") else "❌ Вимкнено"

    await message.answer(
        f"Менеджер: {manager.get('full_name', '')}\n"
        f"Телефон: {manager.get('phone', '')}\n"
        f"Telegram ID: {manager.get('telegram_id', '')}\n\n"
        f"Поточний доступ: {access_text}",
        reply_markup=access_action_keyboard
    )


def update_access(row_number: int, column_name: str, enabled: bool):
    _rows, ws, headers = load_allowed_users_with_row_numbers()

    access_col = get_access_column_index(headers, column_name)

    if access_col is None:
        raise Exception(f"У листі allowed_users не знайдено колонку: {column_name}")

    value = "TRUE" if enabled else ""
    ws.update_cell(row_number, access_col, value)
    return True


def load_rules():
    rules, _conditions = load_rules_and_conditions()
    return rules


def get_all_categories():
    rules = load_rules()
    values = []

    for row in rules:
        values.extend(split_multi_value(row.get("categories", "")))

    return unique_sorted(values)


def get_all_brands():
    rules = load_rules()
    values = []

    for row in rules:
        values.extend(split_multi_value(row.get("brands", "")))

    return unique_sorted(values)


def get_categories_by_supplier(selected_supplier: str):
    rules = load_rules()

    if not selected_supplier:
        return get_all_categories()

    result = []
    supplier_lower = selected_supplier.lower()

    for row in rules:
        suppliers = [x.lower() for x in split_multi_value(row.get("suppliers", ""))]
        if supplier_lower in suppliers:
            result.extend(split_multi_value(row.get("categories", "")))

    result = unique_sorted(result)

    if result:
        return result

    return get_all_categories()


def get_brands_by_filters(selected_supplier: str, selected_category: str):
    rules = load_rules()
    result = []

    supplier_lower = selected_supplier.lower() if selected_supplier else ""
    category_lower = selected_category.lower() if selected_category else ""

    for row in rules:
        suppliers = [x.lower() for x in split_multi_value(row.get("suppliers", ""))]
        categories = [x.lower() for x in split_multi_value(row.get("categories", ""))]
        brands = split_multi_value(row.get("brands", ""))

        supplier_match = True
        category_match = True

        if supplier_lower:
            supplier_match = supplier_lower in suppliers

        if category_lower:
            category_match = category_lower in categories

        if supplier_match and category_match:
            result.extend(brands)

    result = unique_sorted(result)

    if result:
        return result

    return get_all_brands()


def calculate_prices_with_vat(cost_without_vat: float, margin_percent: float):
    markup_coef_no_vat = round(1 + (margin_percent / 100), 4)
    markup_coef_with_vat = round(markup_coef_no_vat * (1 + VAT_RATE), 4)

    sale_without_vat = round(cost_without_vat * markup_coef_no_vat, 2)
    sale_with_vat = round(cost_without_vat * markup_coef_with_vat, 2)

    return {
        "markup_coef_no_vat": markup_coef_no_vat,
        "markup_coef_with_vat": markup_coef_with_vat,
        "sale_without_vat": sale_without_vat,
        "sale_with_vat": sale_with_vat,
    }


def format_result_message(result: Dict[str, Any], supplier: str, category: str, brand: str, user_id: int):
    role = get_user_role_from_cache(user_id)

    supplier_text = supplier if supplier else "не вказано"
    category_text = category if category else "не вказано"
    brand_text = brand if brand else "не вказано"

    prices = calculate_prices_with_vat(result["cost"], result["margin_percent"])

    lines = [
        "✅ Розрахунок виконано",
        "",
        f"👥 Група клієнта: {result['client_group']}",
        f"🚚 Постачальник: {supplier_text}",
        f"📂 Категорія: {category_text}",
        f"🏷 Бренд: {brand_text}",
        f"💰 Ціна постачальника без ПДВ: {result['cost']}",
        f"🧾 Ціна продажу без ПДВ: {prices['sale_without_vat']}",
        f"🛒 Ціна продажу з ПДВ: {prices['sale_with_vat']}",
    ]

    if role == "top_manager":
        lines.append(f"📐 Коефіцієнт ціни з ПДВ: {prices['markup_coef_with_vat']}")

    if role == "admin":
        lines.extend([
            "",
            f"🧠 Правило: {result['rule_type']}",
            f"📌 Dynamic margin: {result['margin_name']}",
            f"📈 Націнка: {result['margin_percent']} %",
            f"📐 Коефіцієнт ціни без ПДВ: {prices['markup_coef_no_vat']}",
            f"📐 Коефіцієнт ціни з ПДВ: {prices['markup_coef_with_vat']}",
        ])

    return "\n".join(lines)


def reset_user_calculation(user_id: int):
    user_state[user_id] = {}


async def show_calc_client_groups_page(message: types.Message, page: int):
    catalogs = load_catalogs()
    client_groups = catalogs.get("calc_client_groups", [])

    if not client_groups:
        await message.answer(
            "❌ Немає клієнтських груп для розрахунку. Спочатку онови довідники.",
            reply_markup=get_main_keyboard(message.from_user.id)
        )
        return

    keyboard, total_pages = build_paginated_keyboard(client_groups, page)

    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1

    user_state[message.from_user.id] = {
        "step": "select_calc_client_group",
        "page": page,
    }

    await message.answer(
        f"Обери групу клієнта для розрахунку:\nСторінка {page + 1} з {total_pages}",
        reply_markup=keyboard
    )


async def show_suppliers_page(message: types.Message, page: int):
    catalogs = load_catalogs()
    suppliers = catalogs.get("suppliers", [])

    if not suppliers:
        await message.answer(
            "❌ Немає постачальників. Спочатку онови довідники.",
            reply_markup=get_main_keyboard(message.from_user.id)
        )
        return

    keyboard, total_pages = build_paginated_keyboard(
        suppliers,
        page,
        extra_bottom_buttons=[[KeyboardButton(text="⏭ Пропустити постачальника")]]
    )

    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1

    if message.from_user.id not in user_state:
        user_state[message.from_user.id] = {}

    user_state[message.from_user.id]["step"] = "select_supplier"
    user_state[message.from_user.id]["page"] = page

    await message.answer(
        f"Обери постачальника:\nСторінка {page + 1} з {total_pages}",
        reply_markup=keyboard
    )


async def show_categories_page(message: types.Message, page: int):
    user_id = message.from_user.id
    state = user_state.get(user_id, {})
    selected_supplier = state.get("supplier", "")

    categories = get_categories_by_supplier(selected_supplier)

    if not categories:
        await message.answer("❌ Не вдалося отримати категорії", reply_markup=get_main_keyboard(user_id))
        return

    keyboard, total_pages = build_paginated_keyboard(
        categories,
        page,
        extra_bottom_buttons=[[KeyboardButton(text="⏭ Пропустити категорію")]]
    )

    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1

    user_state[user_id]["step"] = "select_category"
    user_state[user_id]["page"] = page
    user_state[user_id]["available_categories"] = categories

    supplier_text = selected_supplier if selected_supplier else "не вибрано"

    await message.answer(
        f"Обери категорію:\nПостачальник: {supplier_text}\nСторінка {page + 1} з {total_pages}",
        reply_markup=keyboard
    )


async def show_brands_page(message: types.Message, page: int):
    user_id = message.from_user.id
    state = user_state.get(user_id, {})

    selected_supplier = state.get("supplier", "")
    selected_category = state.get("category", "")

    brands = get_brands_by_filters(selected_supplier, selected_category)

    if not brands:
        await message.answer(
            "❌ Не вдалося отримати бренди",
            reply_markup=get_main_keyboard(user_id)
        )
        return

    keyboard, total_pages = build_paginated_keyboard(
        brands,
        page,
        extra_bottom_buttons=[[KeyboardButton(text="⏭ Пропустити бренд")]]
    )

    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1

    if user_id not in user_state:
        user_state[user_id] = {}

    user_state[user_id]["step"] = "select_brand"
    user_state[user_id]["page"] = page
    user_state[user_id]["available_brands"] = brands

    supplier_text = selected_supplier if selected_supplier else "не вказано"
    category_text = selected_category if selected_category else "не вказано"

    await message.answer(
        f"Обери бренд:\n"
        f"Постачальник: {supplier_text}\n"
        f"Категорія: {category_text}\n"
        f"Сторінка {page + 1} з {total_pages}",
        reply_markup=keyboard
    )


async def show_cost_input(message: types.Message):
    user_id = message.from_user.id

    if user_id not in user_state:
        user_state[user_id] = {}

    user_state[user_id]["step"] = "enter_cost"

    state = user_state.get(user_id, {})
    client_group = state.get("client_group", "")
    supplier = state.get("supplier", "")
    category = state.get("category", "")
    brand = state.get("brand", "")

    await message.answer(
        "✅ Параметри вибрано\n\n"
        f"👥 Група клієнта: {client_group}\n"
        f"🚚 Постачальник: {supplier if supplier else 'не вказано'}\n"
        f"📂 Категорія: {category if category else 'не вказано'}\n"
        f"🏷 Бренд: {brand if brand else 'не вказано'}\n\n"
        "Введи ціну постачальника без ПДВ.\n"
        "Приклад: 100\n"
        "Або: 100,50",
        reply_markup=get_cost_keyboard(user_id)
    )


async def save_individual_markup(data: Dict[str, Any], manager_name: str = ""):
    spreadsheet = get_individual_spreadsheet()
    ws = spreadsheet.worksheet(INDIVIDUAL_SHEET_NAME)

    headers = ws.row_values(1)
    if not headers:
        raise Exception("У таблиці індивідуальної націнки немає заголовків у першому рядку")

    row = [""] * len(headers)

    header_aliases = {
        "client_name": ["Найменування клієнта", "Client name"],
        "client_phone": ["Телефон клієнта", "Telefon", "Phone"],
        "client_uuid": ["UID клієнта", "Uid клієнта", "UUID клієнта"],
        "brand": ["Бренд для зміни"],
        "reason": ["Причина зміни"],
        "markup": ["Зміна націнки (%)", "Зміна націнки %"],
        "competitor": ["Конкурент (найменування)", "Конкурент"],
        "client_group": ["Клієнтська поточна цінова група"],
        "manager": ["Manager", "Менеджер"],
    }

    values_map = {
        "client_name": normalize_text(data.get("client_name", "")),
        "client_phone": normalize_text(data.get("client_phone", "")),
        "client_uuid": normalize_text(data.get("client_uuid", "")),
        "brand": normalize_text(data.get("brand", "")),
        "reason": normalize_text(data.get("reason", "")),
        "markup": normalize_text(data.get("markup", "")),
        "competitor": normalize_text(data.get("competitor", "")),
        "client_group": normalize_text(data.get("client_group", "")),
        "manager": normalize_text(manager_name),
    }

    for field_name, aliases in header_aliases.items():
        idx = find_header_index(headers, aliases)
        if idx is not None:
            row[idx] = values_map.get(field_name, "")

    next_row = get_next_empty_row(ws)
    last_col_letter = col_to_letter(len(headers))
    target_range = f"A{next_row}:{last_col_letter}{next_row}"

    ws.update(target_range, [row], value_input_option="USER_ENTERED")


async def notify_admin_about_individual_markup(user_id: int, answers: Dict[str, Any], manager_name: str = ""):
    text = (
        "💰 Нова заявка на індивідуальну націнку\n\n"
        f"👤 Менеджер: {normalize_text(manager_name)}\n"
        f"🏢 Найменування клієнта: {normalize_text(answers.get('client_name', ''))}\n"
        f"📞 Телефон клієнта: {normalize_text(answers.get('client_phone', ''))}\n"
        f"🆔 UID клієнта: {normalize_text(answers.get('client_uuid', ''))}\n"
        f"🏷 Бренд для зміни: {normalize_text(answers.get('brand', ''))}\n"
        f"📝 Причина зміни: {normalize_text(answers.get('reason', ''))}\n"
        f"📈 Зміна націнки (%): {normalize_text(answers.get('markup', ''))}\n"
        f"🏪 Конкурент: {normalize_text(answers.get('competitor', ''))}\n"
        f"📂 Клієнтська поточна цінова група: {normalize_text(answers.get('client_group', ''))}"
    )

    for admin_id in get_admin_telegram_ids():
        try:
            if int(admin_id) != int(user_id):
                await bot.send_message(chat_id=admin_id, text=text)
        except Exception:
            pass


async def start_individual_markup(message: types.Message):
    user_state[message.from_user.id] = {
        "step": "individual_markup",
        "field_index": 0,
        "answers": {}
    }
    await ask_individual_question(message)


async def ask_individual_question(message: types.Message):
    state = user_state[message.from_user.id]
    index = state.get("field_index", 0)

    if index >= len(INDIVIDUAL_FIELDS):
        manager_name = authorized_users_cache.get(message.from_user.id, {}).get("full_name", "")

        await save_individual_markup(state.get("answers", {}), manager_name=manager_name)
        await notify_admin_about_individual_markup(
            user_id=message.from_user.id,
            answers=state.get("answers", {}),
            manager_name=manager_name
        )

        await message.answer(
            "✅ Дані по індивідуальній націнці збережено",
            reply_markup=get_main_keyboard(message.from_user.id)
        )

        user_state.pop(message.from_user.id, None)
        return

    field = INDIVIDUAL_FIELDS[index]
    await message.answer(INDIVIDUAL_TITLES[field])


def load_departments() -> List[str]:
    try:
        spreadsheet = get_spreadsheet()
        ws = spreadsheet.worksheet(DEPARTMENTS_SHEET_NAME)
        values = ws.get_all_values()

        if not values:
            return DEFAULT_DEPARTMENTS

        result = []
        for row in values[1:]:
            if not row:
                continue
            department = normalize_text(row[0])
            if department:
                result.append(department)

        departments = unique_sorted(result)
        if departments:
            return departments

        return DEFAULT_DEPARTMENTS
    except Exception:
        return DEFAULT_DEPARTMENTS


def build_departments_keyboard(departments: List[str]):
    keyboard = []
    for department in departments:
        keyboard.append([KeyboardButton(text=department)])

    keyboard.append([KeyboardButton(text="🔙 Головне меню")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )


def build_promo_fields_for_user(user_id: int) -> List[str]:
    profile = get_allowed_user_profile(user_id)
    fields = []

    for field in PROMO_BASE_FIELDS:
        if field == "manager_first_name" and profile.get("first_name"):
            continue
        if field == "manager_last_name" and profile.get("last_name"):
            continue
        if field == "department" and profile.get("department"):
            continue
        fields.append(field)

    return fields


async def save_promo(data: Dict[str, Any], manager_name: str = ""):
    spreadsheet = get_individual_spreadsheet()
    ws = spreadsheet.worksheet(PROMO_SHEET_NAME)

    headers = ws.row_values(1)
    if not headers:
        raise Exception("У листі PROMO немає заголовків у першому рядку")

    row = [""] * len(headers)

    header_aliases = {
        "client_name": ["Client name", "Найменування клієнта"],
        "client_phone": ["Telefon", "Телефон", "Телефон клієнта"],
        "client_uuid": ["UID клієнта", "UID кліента", "UID клієнта"],
        "date_request": ["Date request", "Дата заявки"],
        "manager": ["Manager", "Менеджер"],
        "manager_first_name": ["First name", "Ім’я менеджера", "Имя менеджера"],
        "manager_last_name": ["Last Name", "Last name", "Прізвище менеджера", "Фамилия менеджера"],
        "department": ["department", "Департамент"],
        "description": ["description", "Опис", "Проблема"],
        "dissatisfaction_level": ["level of dissatisfaction", "Рівень незадоволеності"],
        "discount_amount": ["Discount amount", "Розмір знижки"],
    }

    values_map = {
        "client_name": normalize_text(data.get("client_name", "")),
        "client_phone": normalize_text(data.get("client_phone", "")),
        "client_uuid": normalize_text(data.get("client_uuid", "")),
        "date_request": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "manager": normalize_text(manager_name),
        "manager_first_name": normalize_text(data.get("manager_first_name", "")),
        "manager_last_name": normalize_text(data.get("manager_last_name", "")),
        "department": normalize_text(data.get("department", "")),
        "description": normalize_text(data.get("description", "")),
        "dissatisfaction_level": normalize_text(data.get("dissatisfaction_level", "")),
        "discount_amount": normalize_text(data.get("discount_amount", "")),
    }

    for field_name, aliases in header_aliases.items():
        idx = find_header_index(headers, aliases)
        if idx is not None:
            row[idx] = values_map.get(field_name, "")

    next_row = get_next_empty_row(ws)
    last_col_letter = col_to_letter(len(headers))
    target_range = f"A{next_row}:{last_col_letter}{next_row}"

    ws.update(target_range, [row], value_input_option="USER_ENTERED")


async def notify_admin_about_promo(user_id: int, answers: Dict[str, Any], manager_name: str = ""):
    text = (
        "🎟 Нова заявка на промокод\n\n"
        f"👤 Менеджер: {normalize_text(manager_name)}\n"
        f"Ім’я менеджера: {normalize_text(answers.get('manager_first_name', ''))}\n"
        f"Прізвище менеджера: {normalize_text(answers.get('manager_last_name', ''))}\n"
        f"Департамент: {normalize_text(answers.get('department', ''))}\n"
        f"🏢 Клієнт: {normalize_text(answers.get('client_name', ''))}\n"
        f"📞 Телефон: {normalize_text(answers.get('client_phone', ''))}\n"
        f"🆔 UID: {normalize_text(answers.get('client_uuid', ''))}\n"
        f"📝 Проблема: {normalize_text(answers.get('description', ''))}\n"
        f"⚠️ Рівень незадоволеності: {normalize_text(answers.get('dissatisfaction_level', ''))}\n"
        f"💸 Знижка: {normalize_text(answers.get('discount_amount', ''))}"
    )

    for admin_id in get_admin_telegram_ids():
        try:
            if int(admin_id) != int(user_id):
                await bot.send_message(chat_id=admin_id, text=text)
        except Exception:
            pass


async def start_promo(message: types.Message):
    user_id = message.from_user.id
    profile = get_allowed_user_profile(user_id)

    answers = {
        "manager_first_name": profile.get("first_name", ""),
        "manager_last_name": profile.get("last_name", ""),
        "department": profile.get("department", ""),
    }

    fields = build_promo_fields_for_user(user_id)

    user_state[user_id] = {
        "step": "promo",
        "field_index": 0,
        "fields": fields,
        "answers": answers,
    }

    await ask_promo_question(message)


async def ask_promo_question(message: types.Message):
    user_id = message.from_user.id
    state = user_state[user_id]
    fields = state.get("fields", [])
    index = state.get("field_index", 0)

    if index >= len(fields):
        manager_name = authorized_users_cache.get(user_id, {}).get("full_name", "")

        await save_promo(state.get("answers", {}), manager_name=manager_name)
        await notify_admin_about_promo(
            user_id=user_id,
            answers=state.get("answers", {}),
            manager_name=manager_name
        )

        await message.answer(
            "✅ Дані по промокоду збережено",
            reply_markup=get_main_keyboard(user_id)
        )

        user_state.pop(user_id, None)
        return

    field = fields[index]

    if field == "department":
        departments = load_departments()
        state["available_departments"] = departments
        await message.answer(
            PROMO_TITLES[field],
            reply_markup=build_departments_keyboard(departments)
        )
        return

    await message.answer(PROMO_TITLES[field])


@dp.message()
async def handle_message(message: types.Message):
    raw_text = message.text or ""
    text = norm_cmd(raw_text)
    user_id = message.from_user.id

    if is_survey_active(user_id):
        handled = await handle_survey_message(message)
        if handled:
            return

    if text == "/start":
        refresh_user_role_from_google(user_id)

        if is_user_authorized(user_id):
            reset_user_calculation(user_id)
            await message.answer(
                "Бот готовий. Обери дію:",
                reply_markup=get_main_keyboard(user_id)
            )
            return

        await require_phone_verification(message)
        return

    if message.contact:
        contact = message.contact

        if contact.user_id != user_id:
            await message.answer(
                "❌ Потрібно надіслати саме свій номер телефону.",
                reply_markup=phone_request_keyboard
            )
            return

        phone = normalize_phone(contact.phone_number)
        full_name = " ".join(
            part for part in [
                normalize_text(message.from_user.first_name),
                normalize_text(message.from_user.last_name),
            ] if part
        )

        allowed_user = find_allowed_user_by_phone(phone)

        if allowed_user:
            update_allowed_user_telegram_id_by_phone(phone, user_id)
            authorize_user_session(
                telegram_user_id=user_id,
                phone=phone,
                full_name=allowed_user.get("full_name", full_name),
                role=allowed_user.get("role", ""),
                individual_markup_access=allowed_user.get("individual_markup_access", False),
                promo_access=allowed_user.get("promo_access", False),
            )

            await message.answer(
                "✅ Доступ дозволено.\n\nБот готовий. Обери дію:",
                reply_markup=get_main_keyboard(user_id)
            )
            return

        request_user = {
            "telegram_id": user_id,
            "username": message.from_user.username or "",
            "full_name": full_name,
            "phone": phone,
        }

        created = add_registration_request(request_user)
        if created:
            await notify_admin_about_request(request_user)

        await message.answer(
            "⛔ Ваш номер не знайдено в базі менеджерів.\n\n"
            "Запит на реєстрацію відправлено адміністратору.",
            reply_markup=phone_request_keyboard
        )
        return

    if not is_user_authorized(user_id):
        await require_phone_verification(message)
        return

    state = user_state.get(user_id, {})
    step = state.get("step")

    if text == "🔙 головне меню":
        reset_user_calculation(user_id)
        await message.answer(
            "Повернулись у головне меню.",
            reply_markup=get_main_keyboard(user_id)
        )
        return

    if text == "💰 індивідуальна націнка":
        if not has_individual_markup_access(user_id):
            await message.answer("❌ Немає доступу", reply_markup=get_main_keyboard(user_id))
            return
        await start_individual_markup(message)
        return

    if text == "🎟 промокод":
        if not has_promo_access(user_id):
            await message.answer("❌ Немає доступу", reply_markup=get_main_keyboard(user_id))
            return
        await start_promo(message)
        return

    if "доступ до індивідуальної націнки" in text:
        if not is_admin(user_id):
            await message.answer("❌ Ця дія доступна лише адміну.", reply_markup=get_main_keyboard(user_id))
            return
        await show_access_managers(message, access_type="individual")
        return

    if "доступ до промокодів" in text:
        if not is_admin(user_id):
            await message.answer("❌ Ця дія доступна лише адміну.", reply_markup=get_main_keyboard(user_id))
            return
        await show_access_managers(message, access_type="promo")
        return

    if step == "individual_markup":
        index = state.get("field_index", 0)

        if index < len(INDIVIDUAL_FIELDS):
            field = INDIVIDUAL_FIELDS[index]
            state["answers"][field] = raw_text
            state["field_index"] = index + 1
            await ask_individual_question(message)
            return

    if step == "promo":
        fields = state.get("fields", [])
        index = state.get("field_index", 0)

        if index < len(fields):
            field = fields[index]

            if field == "department":
                departments = state.get("available_departments", DEFAULT_DEPARTMENTS)
                if raw_text not in departments:
                    await message.answer(
                        "❌ Обери департамент кнопкою зі списку.",
                        reply_markup=build_departments_keyboard(departments)
                    )
                    return

            if field == "dissatisfaction_level":
                if normalize_text(raw_text) not in ("1", "2", "3"):
                    await message.answer("❌ Введіть тільки 1, 2 або 3")
                    return

            state["answers"][field] = raw_text
            state["field_index"] = index + 1
            await ask_promo_question(message)
            return

    if step == "access_search":
        if not is_admin(user_id):
            await message.answer("❌ Ця дія доступна лише адміну.", reply_markup=get_main_keyboard(user_id))
            return

        query = raw_text.strip()
        if not query:
            await message.answer("❌ Введіть ім'я, телефон або telegram_id для пошуку.")
            return

        await show_access_managers(
            message,
            access_type=state.get("access_type", ""),
            page=0,
            query=query,
        )
        return

    if step in ("individual_access_select_manager", "promo_access_select_manager"):
        if not is_admin(user_id):
            await message.answer("❌ Ця дія доступна лише адміну.", reply_markup=get_main_keyboard(user_id))
            return

        current_page = state.get("page", 0)
        current_query = state.get("query", "")
        access_type = state.get("access_type", "")
        filtered_managers = state.get("filtered_managers", [])

        if text == "➡️ далі":
            await show_access_managers(message, access_type=access_type, page=current_page + 1, query=current_query)
            return

        if text == "⬅️ назад":
            await show_access_managers(message, access_type=access_type, page=current_page - 1, query=current_query)
            return

        if text == "🔎 пошук менеджера":
            user_state[user_id]["step"] = "access_search"
            await message.answer(
                "Введіть ім'я, телефон або telegram_id менеджера для пошуку:",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="🔙 Головне меню")]],
                    resize_keyboard=True
                )
            )
            return

        selected_manager = None
        for manager in filtered_managers:
            label_enabled = f"✅ {manager.get('full_name', '')}"
            label_disabled = f"❌ {manager.get('full_name', '')}"
            if raw_text == label_enabled or raw_text == label_disabled:
                selected_manager = manager
                break

        if not selected_manager:
            await message.answer(
                "❌ Обери менеджера кнопкою зі списку.",
                reply_markup=build_access_managers_keyboard(filtered_managers, current_page)[0]
            )
            return

        await show_access_actions(
            message=message,
            manager=selected_manager,
            access_type=access_type,
            access_column=state.get("access_column", ""),
        )
        return

    if step == "access_action":
        if not is_admin(user_id):
            await message.answer("❌ Ця дія доступна лише адміну.", reply_markup=get_main_keyboard(user_id))
            return

        selected_manager = state.get("selected_manager", {})
        access_column = state.get("access_column", "")
        access_type = state.get("access_type", "")
        current_page = state.get("page", 0)
        current_query = state.get("query", "")

        if text == "✅ увімкнути доступ":
            update_access(selected_manager.get("row_number"), access_column, True)
            if selected_manager.get("telegram_id", "") == str(user_id) and user_id in authorized_users_cache:
                if access_column == INDIVIDUAL_ACCESS_COLUMN:
                    authorized_users_cache[user_id]["individual_markup_access"] = True
                if access_column == PROMO_ACCESS_COLUMN:
                    authorized_users_cache[user_id]["promo_access"] = True

            await message.answer("✅ Доступ оновлено")
            await show_access_managers(message, access_type=access_type, page=current_page, query=current_query)
            return

        if text == "❌ вимкнути доступ":
            update_access(selected_manager.get("row_number"), access_column, False)
            if selected_manager.get("telegram_id", "") == str(user_id) and user_id in authorized_users_cache:
                if access_column == INDIVIDUAL_ACCESS_COLUMN:
                    authorized_users_cache[user_id]["individual_markup_access"] = False
                if access_column == PROMO_ACCESS_COLUMN:
                    authorized_users_cache[user_id]["promo_access"] = False

            await message.answer("✅ Доступ оновлено")
            await show_access_managers(message, access_type=access_type, page=current_page, query=current_query)
            return

        if text == "🔙 до списку менеджерів":
            await show_access_managers(message, access_type=access_type, page=current_page, query=current_query)
            return

        await message.answer("Обери дію кнопкою.", reply_markup=access_action_keyboard)
        return

    if text == "оновити довідники":
        try:
            await message.answer("🔄 Оновлюю довідники...")
            catalogs = save_catalogs()
            errors = validate_catalogs(catalogs)

            if errors:
                error_text = "\n".join([f"❌ {e}" for e in errors])
                await message.answer(
                    f"⚠️ Довідники оновлено, але є проблеми:\n\n{error_text}",
                    reply_markup=get_main_keyboard(user_id)
                )
            else:
                await message.answer(
                    "✅ Довідники успішно оновлено",
                    reply_markup=get_main_keyboard(user_id)
                )
        except Exception as e:
            await message.answer(f"❌ Помилка: {e}", reply_markup=get_main_keyboard(user_id))
        return

    if text == "👤 нові заявки":
        if not is_admin(user_id):
            await message.answer("❌ Ця дія доступна лише адміну.", reply_markup=get_main_keyboard(user_id))
            return
        await show_next_registration_request(message, request_index=0)
        return

    if text == "📝 опитувальник":
        try:
            await start_survey(message, default_manager="")
        except Exception as e:
            await message.answer(f"❌ Помилка запуску опитувальника: {e}", reply_markup=get_main_keyboard(user_id))
        return

    if text == "розрахувати ціну" or text == "🔄 новий розрахунок":
        await show_calc_client_groups_page(message, page=0)
        return

    if step == "admin_review_requests" and is_admin(user_id):
        if text == "✅ додати менеджера":
            row_number = state.get("request_row_number")
            phone = state.get("request_phone", "")
            full_name = state.get("request_full_name", "")
            telegram_id = state.get("request_telegram_id", "")

            success, info = append_allowed_user_from_request({
                "phone": phone,
                "full_name": full_name,
                "telegram_id": telegram_id,
            })

            approve_request(row_number)

            if success:
                await message.answer("✅ Менеджера додано. Заявку переведено в approved.")
            else:
                await message.answer(f"ℹ️ {info}. Заявку переведено в approved.")

            await show_next_registration_request(message, request_index=state.get("request_index", 0))
            return

        if text == "⏭ наступна заявка":
            await show_next_registration_request(message, request_index=state.get("request_index", 0) + 1)
            return

    if step == "select_calc_client_group":
        catalogs = load_catalogs()
        client_groups = catalogs.get("calc_client_groups", [])
        current_page = state.get("page", 0)

        if text == "➡️ далі":
            await show_calc_client_groups_page(message, current_page + 1)
            return

        if text == "⬅️ назад":
            await show_calc_client_groups_page(message, current_page - 1)
            return

        if raw_text in client_groups:
            user_state[user_id] = {"step": "select_supplier", "client_group": raw_text, "page": 0}
            await message.answer(f"✅ Обрано групу клієнта: {raw_text}")
            await show_suppliers_page(message, page=0)
            return

    if step == "select_supplier":
        catalogs = load_catalogs()
        suppliers = catalogs.get("suppliers", [])
        current_page = state.get("page", 0)

        if text == "➡️ далі":
            await show_suppliers_page(message, current_page + 1)
            return

        if text == "⬅️ назад":
            await show_suppliers_page(message, current_page - 1)
            return

        if text == "⏭ пропустити постачальника":
            user_state[user_id]["supplier"] = ""
            await message.answer("✅ Постачальника пропущено.")
            await show_categories_page(message, page=0)
            return

        if raw_text in suppliers:
            user_state[user_id]["supplier"] = raw_text
            await message.answer(f"✅ Обрано постачальника: {raw_text}")
            await show_categories_page(message, page=0)
            return

    if step == "select_category":
        categories = state.get("available_categories", [])
        current_page = state.get("page", 0)

        if text == "➡️ далі":
            await show_categories_page(message, current_page + 1)
            return

        if text == "⬅️ назад":
            await show_categories_page(message, current_page - 1)
            return

        if text == "⏭ пропустити категорію":
            user_state[user_id]["category"] = ""
            await message.answer("✅ Категорію пропущено.")
            await show_brands_page(message, page=0)
            return

        if raw_text in categories:
            user_state[user_id]["category"] = raw_text
            await message.answer(f"✅ Обрано категорію: {raw_text}")
            await show_brands_page(message, page=0)
            return

    if step == "select_brand":
        brands = state.get("available_brands", [])
        current_page = state.get("page", 0)

        if text == "➡️ далі":
            await show_brands_page(message, current_page + 1)
            return

        if text == "⬅️ назад":
            await show_brands_page(message, current_page - 1)
            return

        if text == "⏭ пропустити бренд":
            user_state[user_id]["brand"] = ""
            await message.answer("✅ Бренд пропущено.")
            await show_cost_input(message)
            return

        if raw_text in brands:
            user_state[user_id]["brand"] = raw_text
            await message.answer(f"✅ Обрано бренд: {raw_text}")
            await show_cost_input(message)
            return

    if step == "enter_cost":
        try:
            cost = parse_cost(raw_text)
        except Exception:
            await message.answer(
                "❌ Невірний формат ціни.\n"
                "Введи число, наприклад:\n"
                "100\n"
                "або\n"
                "100,50",
                reply_markup=get_cost_keyboard(user_id)
            )
            return

        client_group = state.get("client_group", "")
        supplier = state.get("supplier", "")
        category = state.get("category", "")
        brand = state.get("brand", "")

        result = calculate_margin_result(
            supplier=supplier,
            category=category,
            brand=brand,
            client_group=client_group,
            cost=cost
        )

        if result.get("success"):
            await message.answer(
                format_result_message(result, supplier, category, brand, user_id),
                reply_markup=get_after_result_keyboard(user_id)
            )
        else:
            error_message = "❌ Не вдалося виконати розрахунок\n\n"
            error_message += f"Причина: {result.get('message', 'Невідома помилка')}"

            if is_admin(user_id):
                if result.get("margin_name"):
                    error_message += f"\nDynamic margin: {result['margin_name']}"
                if result.get("rule_type"):
                    error_message += f"\nПравило: {result['rule_type']}"

            error_message += (
                "\n\n"
                f"Група клієнта: {client_group}\n"
                f"Постачальник: {supplier if supplier else 'не вказано'}\n"
                f"Категорія: {category if category else 'не вказано'}\n"
                f"Бренд: {brand if brand else 'не вказано'}\n"
                f"Ціна постачальника без ПДВ: {cost}"
            )

            await message.answer(error_message, reply_markup=get_after_result_keyboard(user_id))

        reset_user_calculation(user_id)
        return

    await message.answer(
        "Не розумію команду. Обери дію з меню.",
        reply_markup=get_main_keyboard(user_id)
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
