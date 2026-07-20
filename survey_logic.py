# -*- coding: utf-8 -*-

from datetime import datetime
from typing import Dict, Any, List, Optional

from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from catalogs_storage import (
    get_google_client,
    load_catalogs,
)
from config import SURVEY_SPREADSHEET_URL


SURVEY_RESPONSE_SHEET_NAME = "Відповіді форми (1)"

survey_state: Dict[int, Dict[str, Any]] = {}

CLIENT_TYPE_NEW = "Новий клієнт"
CLIENT_TYPE_EXISTING = "Клієнт, з яким вже працюємо"


NEW_CLIENT_FIELDS = [
    "client_type",
    "client_name",
    "client_phone",
    "manager_type",
    "manager",
    "client_group_type",
    "revenue_range",
    "orders_range",
    "debounce_percent",
    "debounce_days",
    "returns_percent",
    "focus_value",
    "logistics_zone",
    "new_nextis_group",
    "new_oms_group",
]

EXISTING_CLIENT_FIELDS = [
    "client_type",
    "client_phone",
    "manager_type",
    "manager",
    "client_group_type",
    "revenue_range",
    "debounce_days",
    "logistics_zone",
    "current_oms_group",
    "current_nextis_markup",
    "new_nextis_group",
    "new_oms_group",
    "price_change_reason",
]


FIELD_TITLES = {
    "client_type": "Тип клієнта",
    "client_name": "Найменування клієнта",
    "client_phone": "Телефон клієнта",
    "client_uuid": "ID (UUID) клієнта (OMC)",
    "manager_type": "Тип менеджера",
    "manager": "Менеджер",
    "client_group_type": "Тип клієнтської групи",
    "revenue_range": "Виручка від реалізіції (Загалний очікуваний оборот за місяць)",
    "orders_range": "Кількість замовлень на місяць",
    "debounce_percent": (
        '% дебіторської заборгованості (Сума дебіторської заборгованості/(Суму обороту за місяць*30) "днів") \n'
        "___________________________________\n"
        '"Коефіцієнт дороговизни клієнта" - DSO'
    ),
    "debounce_days": "Кількість днів дебіторської заборгованості",
    "returns_percent": "% повернень",
    "focus_value": "Фокус задача % (фокус бренди) продажі",
    "logistics_zone": "Логістична зона (доставка - км) від основго складу. Рахується, як туди і назад",
    "new_nextis_group": "Нова цінова група Nextis",
    "new_oms_group": "Нова цінова група OMS",
    "current_oms_group": "Діюча група націнки OMS",
    "current_nextis_markup": "Діюча націнка (Nextis)",
    "price_change_reason": "Причина зміни націнки",
}


HEADER_ALIASES = {
    "timestamp": [
        "Позначка часу",
        "Timestamp",
    ],
    "client_type": [
        "Тип клієнта",
    ],
    "client_name": [
        "Найменування клієнта",
        "Найменування клієнта - з яким працюємо",
    ],
    "client_phone": [
        "Телефон клієнта (+43...)",
        "Телефон клієнта",
        "Телефон клієнта - з яким працюємо",
    ],
    "client_uuid": [
        "ID (UUID) клієнта",
        "ID (UUID) клієнта (OMC)",
        "ID (UUID) клієнта NEW",
        "ID (UUID) клієнта NEW (OMC)",
    ],
    "manager_type": [
        "Тип менеджера",
        "Тим менеджера",
    ],
    "manager": [
        "Менеджер",
    ],
    "client_group_type": [
        "Тип клієнтської групи",
    ],
    "revenue_range": [
        "Виручка від реалізації",
        "Виручка від реалізації (Загальний очікуваний оборот за місяць)",
        "Виручка від реалізіції (Загалний очікуваний оборот за місяць)",
    ],
    "orders_range": [
        "Кількість замовлень на місяць",
    ],
    "debounce_percent": [
        "% дебіторської заборгованості",
        "коефіцієнт дороговизни клієнта - dso",
        "dso",
    ],
    "debounce_days": [
        "Кількість днів дебіторської заборгованості",
    ],
    "returns_percent": [
        "% повернень",
    ],
    "focus_value": [
        "Фокус задача %",
        "Фокус задача % (фокус бренду) продажі",
        "Фокус задача % (фокус бренди) продажі",
    ],
    "logistics_zone": [
        "Логістична зона",
        "Логістична зона (доставка - км) від основного складу. Рахується, як туди і назад",
        "Логістична зона (доставка - км) від основго складу. Рахується, як туди і назад",
    ],
    "new_nextis_group": [
        "Нова цінова група Nextis",
        "Присвоєна націнка (Nextis)",
        "Нова ціна",
        "Nextis",
    ],
    "new_oms_group": [
        "Нова цінова група OMS",
    ],
    "current_oms_group": [
        "Діюча група націнки OMS",
        "Діюча цінова група OMS",
        "Поточна група націнки OMS",
    ],
    "current_nextis_markup": [
        "Діюча націнка (Nextis)",
        "Поточна націнка (Nextis)",
        "Діюча група Nextis",
    ],
    "price_change_reason": [
        "Причина зміни націнки",
    ],
    "source": [
        "source",
    ],
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    text = text.replace('"', "")
    text = text.replace("'", "")
    text = text.replace("`", "")

    while "  " in text:
        text = text.replace("  ", " ")

    return text.strip()


def normalize_text_lower(value: Any) -> str:
    return normalize_text(value).lower()


def col_to_letter(col_num: int) -> str:
    result = ""
    while col_num > 0:
        col_num, rem = divmod(col_num - 1, 26)
        result = chr(65 + rem) + result
    return result


def find_header_indexes(headers: List[str], aliases: List[str]) -> List[int]:
    normalized_headers = [normalize_text_lower(h) for h in headers]
    indexes: List[int] = []

    for alias in aliases:
        alias_norm = normalize_text_lower(alias)

        for idx, header in enumerate(normalized_headers):
            if header == alias_norm and idx not in indexes:
                indexes.append(idx)

        for idx, header in enumerate(normalized_headers):
            if alias_norm and alias_norm in header and idx not in indexes:
                indexes.append(idx)

    return indexes


def build_row_by_headers(headers: List[str], answers: Dict[str, Any]) -> List[str]:
    row = [""] * len(headers)

    client_phone = str(answers.get("client_phone", ""))

    values_map = {
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        "client_type": str(answers.get("client_type", "")),
        "client_name": str(answers.get("client_name", "")) or client_phone,
        "client_phone": client_phone,
        "client_uuid": str(answers.get("client_uuid", "")) or client_phone,
        "manager_type": str(answers.get("manager_type", "")),
        "manager": str(answers.get("manager", "")),
        "client_group_type": str(answers.get("client_group_type", "")),
        "revenue_range": str(answers.get("revenue_range", "")),
        "orders_range": str(answers.get("orders_range", "")),
        "debounce_percent": str(answers.get("debounce_percent", "")),
        "debounce_days": str(answers.get("debounce_days", "")),
        "returns_percent": str(answers.get("returns_percent", "")),
        "focus_value": str(answers.get("focus_value", "")),
        "logistics_zone": str(answers.get("logistics_zone", "")),
        "new_nextis_group": str(answers.get("new_nextis_group", "")),
        "new_oms_group": str(answers.get("new_oms_group", "")),
        "current_oms_group": str(answers.get("current_oms_group", "")),
        "current_nextis_markup": str(answers.get("current_nextis_markup", "")),
        "price_change_reason": str(answers.get("price_change_reason", "")),
        "source": "telegram",
    }

    for field_name, aliases in HEADER_ALIASES.items():
        indexes = find_header_indexes(headers, aliases)
        for idx in indexes:
            row[idx] = values_map.get(field_name, "")

    return row


def get_next_empty_row(ws) -> int:
    values = ws.get_all_values()
    return len(values) + 1


def save_survey_result_to_google(answers: Dict[str, Any]):
    client = get_google_client()
    spreadsheet = client.open_by_url(SURVEY_SPREADSHEET_URL)
    ws = spreadsheet.worksheet(SURVEY_RESPONSE_SHEET_NAME)

    headers = ws.row_values(1)
    if not headers:
        raise Exception("У листі відповідей немає заголовків у першому рядку")

    row = build_row_by_headers(headers, answers)
    next_row = get_next_empty_row(ws)
    last_col_letter = col_to_letter(len(headers))
    target_range = f"A{next_row}:{last_col_letter}{next_row}"

    ws.update(
        target_range,
        [row],
        value_input_option="USER_ENTERED"
    )


def build_keyboard(items: List[str]) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=item)] for item in items]
    rows.append([KeyboardButton(text="❌ Скасувати опитування")])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True
    )


def build_text_input_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Скасувати опитування")]],
        resize_keyboard=True
    )


_main_keyboard_provider = None


def set_main_keyboard_provider(provider) -> None:
    global _main_keyboard_provider
    _main_keyboard_provider = provider


def build_finish_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    if _main_keyboard_provider is not None:
        return _main_keyboard_provider(user_id)

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Оновити довідники")],
            [KeyboardButton(text="Розрахувати ціну")],
            [KeyboardButton(text="📝 Зміна групи націнки")],
        ],
        resize_keyboard=True
    )


def is_text_field(field: str) -> bool:
    return field in [
        "client_name",
        "client_phone",
        "client_uuid",
        "price_change_reason",
    ]


def is_survey_active(user_id: int) -> bool:
    return user_id in survey_state


def get_fields_for_client_type(client_type: str) -> List[str]:
    if client_type == CLIENT_TYPE_NEW:
        return NEW_CLIENT_FIELDS
    return EXISTING_CLIENT_FIELDS


def get_catalog_options(catalogs: Dict[str, Any], field: str, answers: Optional[Dict[str, Any]] = None) -> List[str]:
    if field == "manager_type":
        managers_by_type = catalogs.get("managers_by_type", {})
        return sorted((str(x) for x in managers_by_type.keys() if str(x).strip()), key=lambda v: v.lower())

    if field == "manager":
        managers_by_type = catalogs.get("managers_by_type", {})
        manager_type = str((answers or {}).get("manager_type", "")).strip()
        values = managers_by_type.get(manager_type, []) or catalogs.get("managers", [])
        return [str(x) for x in values if str(x).strip()]

    price_group_fields = {
        "new_oms_group": ("oms_price_groups_by_client_group", "oms_price_groups"),
        "current_oms_group": ("oms_price_groups_by_client_group", "oms_price_groups"),
        "new_nextis_group": ("nextis_price_groups_by_client_group", "nextis_price_groups"),
        "current_nextis_markup": ("nextis_price_groups_by_client_group", "nextis_price_groups"),
    }

    if field in price_group_fields:
        grouped_key, flat_key = price_group_fields[field]
        grouped = catalogs.get(grouped_key, {})
        client_group_type = str((answers or {}).get("client_group_type", "")).strip()
        values = grouped.get(client_group_type, []) or catalogs.get(flat_key, [])
        return [str(x) for x in values if str(x).strip()]

    mapping = {
        "client_type": catalogs.get("client_types", []),
        "client_group_type": catalogs.get("survey_client_groups", []),
        "revenue_range": catalogs.get("revenue_ranges", []),
        "orders_range": catalogs.get("orders_ranges", []),
        "debounce_percent": catalogs.get("debounce_percent_ranges", []),
        "debounce_days": catalogs.get("debounce_days_ranges", []),
        "returns_percent": catalogs.get("returns_percent_ranges", []),
        "focus_value": catalogs.get("focus_values", []),
        "logistics_zone": catalogs.get("logistics_zones", []),
    }

    values = mapping.get(field, [])
    return [str(x) for x in values if str(x).strip()]


def get_current_field(user_id: int) -> Optional[str]:
    state = survey_state.get(user_id)
    if not state:
        return None

    fields = state.get("scenario_fields", [])
    step = state.get("step", 0)

    if step < 0 or step >= len(fields):
        return None

    return fields[step]


async def ask_current_question(message: types.Message):
    user_id = message.from_user.id
    state = survey_state[user_id]

    fields = state.get("scenario_fields", [])
    step = state.get("step", 0)

    while step < len(fields):
        field = fields[step]

        if is_text_field(field):
            break

        options = get_catalog_options(state.get("catalogs", {}), field, state.get("answers", {}))
        if options:
            break

        step += 1

    state["step"] = step

    if step >= len(fields):
        save_survey_result_to_google(state["answers"])
        await message.answer(
            "✅ Опитування завершено. Дані успішно записані в Google таблицю.",
            reply_markup=build_finish_keyboard(user_id)
        )
        del survey_state[user_id]
        return

    field = fields[step]

    if is_text_field(field):
        await message.answer(
            FIELD_TITLES[field],
            reply_markup=build_text_input_keyboard()
        )
        return

    catalogs = state.get("catalogs", {})
    options = get_catalog_options(catalogs, field, state.get("answers", {}))

    await message.answer(
        f"Обери значення:\n{FIELD_TITLES[field]}",
        reply_markup=build_keyboard(options)
    )


async def start_survey(message: types.Message, default_manager: str = ""):
    catalogs = load_catalogs()

    if not catalogs:
        raise Exception("Каталоги не завантажені. Спочатку натисни 'Оновити довідники'.")

    survey_state[message.from_user.id] = {
        "step": 0,
        "answers": {},
        "default_manager": str(default_manager).strip(),
        "scenario_fields": ["client_type"],
        "catalogs": catalogs,
    }

    await ask_current_question(message)


async def handle_survey_message(message: types.Message):
    user_id = message.from_user.id

    if user_id not in survey_state:
        return False

    raw_text = (message.text or "").strip()

    if raw_text == "❌ Скасувати опитування":
        del survey_state[user_id]
        await message.answer(
            "❌ Опитування скасовано.",
            reply_markup=build_finish_keyboard(user_id)
        )
        return True

    try:
        state = survey_state[user_id]
        field = get_current_field(user_id)

        if not field:
            del survey_state[user_id]
            await message.answer(
                "❌ Стан опитування пошкоджено. Запусти опитування ще раз.",
                reply_markup=build_finish_keyboard(user_id)
            )
            return True

        if not is_text_field(field):
            options = get_catalog_options(state.get("catalogs", {}), field, state.get("answers", {}))
            if raw_text not in options:
                await message.answer(
                    f"❌ Обери значення кнопкою для поля:\n{FIELD_TITLES[field]}",
                    reply_markup=build_keyboard(options)
                )
                return True

        state["answers"][field] = raw_text

        if field == "client_type":
            state["scenario_fields"] = get_fields_for_client_type(raw_text)

        state["step"] += 1
        await ask_current_question(message)
        return True

    except Exception as e:
        await message.answer(
            f"❌ Помилка зміни групи націнки: {e}",
            reply_markup=build_finish_keyboard(user_id)
        )

        if user_id in survey_state:
            del survey_state[user_id]

        return True


def get_survey_answers(user_id: int) -> Dict[str, Any]:
    if user_id not in survey_state:
        return {}
    return survey_state[user_id].get("answers", {})
