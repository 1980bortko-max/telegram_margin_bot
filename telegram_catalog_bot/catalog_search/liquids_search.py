# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import Dict, List

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


def search_liquids(filters: LiquidsFilters, limit: int = CATALOG_SEARCH_LIMIT) -> List[CatalogProduct]:
    session = get_crm_session()

    with session.lock:
        driver = session.driver

        debug_log(f"Liquids search start: {filters.active_values()}", session.debug_dir)
        session.open_liquids_from_sidebar()
        require_liquids_page(driver)
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


def apply_liquids_filters(driver, filters: LiquidsFilters, debug_dir) -> None:
    values = filters.active_values()
    for field_name, value in values.items():
        debug_log(f"Set Liquids filter: {field_name}={value}", debug_dir)
        set_filter_value(driver, field_name, value)
        debug_log(f"Set Liquids filter OK: {field_name}", debug_dir)


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
    title_parts = []
    if product.brand:
        title_parts.append(product.brand)
    if product.article:
        title_parts.append(product.article)
    if product.name:
        title_parts.append(product.name)

    title = " ".join(title_parts).strip() or "Liquids"

    lines = [f"🚗 {title}"]
    lines.append("")
    lines.append(f"💶 Ціна: {product.price or 'не вказано'}")
    lines.append(f"📦 Наявність: {product.availability or 'не вказано'}")
    lines.append(f"🏬 Склад: {product.warehouse or 'не вказано'}")
    lines.append(f"🚚 Доставка: {product.delivery or 'не вказано'}")
    lines.append(f"🏷 Бренд: {product.brand or 'не вказано'}")

    if product.url:
        lines.append(f"🔗 {product.url}")

    lines.append("")
    lines.append("--------------------")
    return "\n".join(lines)
