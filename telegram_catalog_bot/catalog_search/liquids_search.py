# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import Dict, List

from selenium.common.exceptions import InvalidSessionIdException
from selenium.webdriver.common.keys import Keys

from config import CATALOG_SEARCH_LIMIT
from .crm_session import get_crm_session
from .filter_helpers import (
    debug_log,
    find_liquids_search_button,
    require_liquids_page,
    safe_click,
    save_debug_screenshot,
    set_filter_value,
    wait_results_loaded,
)
from .result_parser import CatalogProduct, parse_products


@dataclass
class LiquidsFilters:
    client_group: str = ""
    brand: str = ""
    liquid_type: str = ""
    viscosity: str = ""
    color: str = ""
    volume_from: str = ""
    volume_to: str = ""
    composition: str = ""
    article: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "LiquidsFilters":
        return cls(
            client_group=(data.get("client_group") or "").strip(),
            brand=(data.get("brand") or "").strip(),
            liquid_type=(data.get("liquid_type") or "").strip(),
            viscosity=(data.get("viscosity") or "").strip(),
            color=(data.get("color") or "").strip(),
            volume_from=(data.get("volume_from") or "").strip(),
            volume_to=(data.get("volume_to") or "").strip(),
            composition=(data.get("composition") or "").strip(),
            article=(data.get("article") or "").strip(),
        )

    def active_values(self) -> Dict[str, str]:
        return {
            key: value
            for key, value in {
                "client_group": self.client_group,
                "brand": self.brand,
                "liquid_type": self.liquid_type,
                "viscosity": self.viscosity,
                "color": self.color,
                "volume_from": self.volume_from,
                "volume_to": self.volume_to,
                "composition": self.composition,
                "article": self.article,
            }.items()
            if value
        }

    def filter_values(self) -> Dict[str, str]:
        return {
            key: value
            for key, value in self.active_values().items()
            if key != "client_group"
        }


def search_liquids(filters: LiquidsFilters, limit: int = CATALOG_SEARCH_LIMIT) -> List[CatalogProduct]:
    session = get_crm_session()

    with session.lock:
        try:
            return _search_liquids_locked(session, filters, limit)
        except Exception as exc:
            if not is_invalid_selenium_session(exc):
                raise

            debug_log("Autofun Selenium session expired. Restart CRM driver and retry search once.", session.debug_dir)
            session.close()
            return _search_liquids_locked(session, filters, limit)


def _search_liquids_locked(session, filters: LiquidsFilters, limit: int) -> List[CatalogProduct]:
    driver = session.driver

    debug_log(f"Liquids search start: {filters.active_values()}", session.debug_dir)
    session.open_liquids_from_sidebar()
    require_liquids_page(driver)

    if filters.client_group:
        session.set_client_group(filters.client_group)

    save_debug_screenshot(driver, session.debug_dir, "liquids_before_filters")

    apply_liquids_filters(driver, filters, session.debug_dir)
    save_debug_screenshot(driver, session.debug_dir, "liquids_after_filters")

    search_button = find_liquids_search_button(driver)
    if not safe_click(driver, search_button):
        raise RuntimeError("Не вдалося натиснути кнопку Пошук")

    wait_results_loaded(driver)
    save_debug_screenshot(driver, session.debug_dir, "liquids_after_search")

    products = parse_products(driver, limit=limit)
    debug_log(f"Liquids search parsed products: {len(products)}", session.debug_dir)
    return products[:limit]


def is_invalid_selenium_session(exc: Exception) -> bool:
    return isinstance(exc, InvalidSessionIdException) or "invalid session id" in str(exc).lower()


def apply_liquids_filters(driver, filters: LiquidsFilters, debug_dir) -> None:
    values = filters.filter_values()
    for field_name, value in values.items():
        debug_log(f"Set Liquids filter: {field_name}={value}", debug_dir)
        try:
            set_filter_value(driver, field_name, value)
        except Exception as exc:
            if field_name != "brand":
                raise
            close_optional_filter(driver)
            debug_log(f"Skip unknown Liquids brand: {value}. Error: {exc}", debug_dir)
            continue
        debug_log(f"Set Liquids filter OK: {field_name}", debug_dir)


def close_optional_filter(driver) -> None:
    try:
        driver.switch_to.active_element.send_keys(Keys.ESCAPE)
    except Exception:
        pass
    try:
        driver.execute_script("document.body.click();")
    except Exception:
        pass


def format_products_for_telegram(products: List[CatalogProduct]) -> List[str]:
    if not products:
        return ["❌ Товари не знайдено."]

    messages: List[str] = []
    current = ""

    for product in products:
        block = format_product(product)
        if len(current) + len(block) > 3500:
            messages.append(current.strip())
            current = ""
        current += block + "\n\n"

    if current.strip():
        messages.append(current.strip())

    return messages


def format_product(product: CatalogProduct) -> str:
    title = product.article or product.name or "Liquids"

    lines = [f"🚗 {title}"]
    lines.append("")
    if product.brand:
        lines.append(f"🏷 Бренд: {product.brand}")
    if product.liquid_type:
        lines.append(f"🛢 Тип: {product.liquid_type}")
    if product.viscosity:
        lines.append(f"🌡 Вʼязкість: {product.viscosity}")
    if product.capacity:
        lines.append(f"🧴 Обʼєм: {product.capacity}")
    if product.specifications:
        lines.append(f"📋 Специфікації: {product.specifications}")
    lines.append(f"💶 Ціна: {product.price or 'не вказано'}")
    lines.append(f"📦 Наявність: {product.availability or 'не вказано'}")
    lines.append(f"🚚 Доставка: {product.delivery or 'не вказано'}")

    if product.url:
        lines.append(f"🔗 {product.url}")

    lines.append("")
    lines.append("--------------------")
    return "\n".join(lines)
