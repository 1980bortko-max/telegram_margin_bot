# -*- coding: utf-8 -*-

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

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
    clear_filter_value,
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


@dataclass
class LiquidsAppliedFiltersReport:
    requested: Dict[str, str] = field(default_factory=dict)
    applied: Dict[str, str] = field(default_factory=dict)
    skipped: Dict[str, str] = field(default_factory=dict)


@dataclass
class LiquidsSearchResult:
    products: List[CatalogProduct]
    report: LiquidsAppliedFiltersReport


def search_liquids(filters: LiquidsFilters, limit: int = CATALOG_SEARCH_LIMIT) -> List[CatalogProduct]:
    return search_liquids_with_report(filters, limit=limit).products


def search_liquids_with_report(
    filters: LiquidsFilters,
    limit: int = CATALOG_SEARCH_LIMIT,
    on_filters_applied: Optional[Callable[[LiquidsAppliedFiltersReport], None]] = None,
) -> LiquidsSearchResult:
    session = get_crm_session()

    with session.lock:
        try:
            return _search_liquids_locked(session, filters, limit, on_filters_applied)
        except Exception as exc:
            if not is_invalid_selenium_session(exc):
                raise

            debug_log("Autofun Selenium session expired. Restart CRM driver and retry search once.", session.debug_dir)
            session.close()
            return _search_liquids_locked(session, filters, limit, on_filters_applied)


def _search_liquids_locked(
    session,
    filters: LiquidsFilters,
    limit: int,
    on_filters_applied: Optional[Callable[[LiquidsAppliedFiltersReport], None]] = None,
) -> LiquidsSearchResult:
    driver = session.driver
    report = LiquidsAppliedFiltersReport(requested=filters.active_values())

    debug_log(f"Liquids search start: {filters.active_values()}", session.debug_dir)
    session.open_liquids_page_fresh()
    require_liquids_page(driver)

    if filters.client_group:
        session.set_client_group(filters.client_group)
        report.applied["client_group"] = filters.client_group

    save_debug_screenshot(driver, session.debug_dir, "liquids_before_filters")

    filter_report = apply_liquids_filters(driver, filters, session.debug_dir)
    report.applied.update(filter_report.applied)
    report.skipped.update(filter_report.skipped)

    save_debug_screenshot(driver, session.debug_dir, "liquids_after_filters")

    if on_filters_applied:
        on_filters_applied(report)

    validation_filters = filters_for_validation(filters, report)
    search_button = find_liquids_search_button(driver)
    if not safe_click(driver, search_button):
        raise RuntimeError("Не вдалося натиснути кнопку Пошук")

    wait_results_loaded(driver)
    save_debug_screenshot(driver, session.debug_dir, "liquids_after_search")

    products = parse_products(driver, limit=limit)
    debug_log(f"Liquids search parsed products: {len(products)}", session.debug_dir)

    products = products[:limit]

    # Clear brands that were mis-parsed as product type words (e.g. "Antifreeze", "Hybrid")
    for p in products:
        if _brand_is_product_type(p.brand):
            p.brand = ""

    # Post-filter by brand in Python when brand is requested.
    # Handles headless mode where the CRM chip may not be selected (returns mixed results).
    # Also tolerates mis-parsed brands: when the parser can't read the brand logo image,
    # it falls back to the product type word (e.g. "Antifreeze") — keep those products.
    if filters.brand:
        filtered = [
            p for p in products
            if text_matches(filters.brand, p.brand)
            or not p.brand  # brand image not parsed at all
            or _brand_is_product_type(p.brand)  # parser mis-read type word as brand
        ]
        # Replace mis-parsed brand (logo read as product type) with the requested brand name
        for p in filtered:
            if not p.brand or _brand_is_product_type(p.brand):
                p.brand = filters.brand
        debug_log(
            f"Brand post-filter '{filters.brand}': {len(products)} → {len(filtered)} products",
            session.debug_dir,
        )
        products = filtered

    try:
        validate_products_match_filters(products, validation_filters, session.debug_dir)
    except RuntimeError:
        save_debug_screenshot(driver, session.debug_dir, "liquids_result_validation_error")
        products = []

    return LiquidsSearchResult(products=products, report=report)


_LIQUID_TYPE_TOKENS: frozenset = frozenset({
    "engineoil", "hydraulicfluids", "breakfluids", "transmissionoil",
    "antifreeze", "axlegearoil", "lubrication", "compressoroil",
    "hydraulicoil", "coolant", "fluid", "oil", "hybrid",
})


def _brand_is_product_type(brand: str) -> bool:
    """Return True when the parsed brand looks like a liquid-type word rather than a real brand.
    This happens when the parser cannot read the brand logo image and falls back to
    the product name, incorrectly extracting the product type (e.g. 'Antifreeze') as brand."""
    return normalize_compare_text(brand) in _LIQUID_TYPE_TOKENS


def is_invalid_selenium_session(exc: Exception) -> bool:
    return isinstance(exc, InvalidSessionIdException) or "invalid session id" in str(exc).lower()


def apply_liquids_filters(driver, filters: LiquidsFilters, debug_dir) -> LiquidsAppliedFiltersReport:
    report = LiquidsAppliedFiltersReport(requested=filters.filter_values())
    values = filters.filter_values()
    for field_name, value in values.items():
        debug_log(f"Set Liquids filter: {field_name}={value}", debug_dir)
        try:
            applied_value = set_filter_value(driver, field_name, value)
        except Exception as exc:
            close_optional_filter(driver)
            save_debug_screenshot(driver, debug_dir, f"liquids_filter_error_{field_name}")
            debug_log(f"Liquids filter failed: {field_name}={value}. Error: {exc}", debug_dir)
            if field_name == "brand":
                clear_filter_value(driver, field_name)
                report.skipped[field_name] = "не найдено в CRM"
                continue
            raise RuntimeError(
                f"Не вдалося застосувати фільтр {filter_title(field_name)}: {value}"
            ) from exc
        report.applied[field_name] = applied_value or value
        debug_log(f"Set Liquids filter OK: {field_name}", debug_dir)
    return report


def filters_for_validation(filters: LiquidsFilters, report: LiquidsAppliedFiltersReport) -> LiquidsFilters:
    return LiquidsFilters(
        client_group=filters.client_group if "client_group" in report.applied else "",
        brand=report.applied.get("brand", ""),
        liquid_type=report.applied.get("liquid_type", ""),
        viscosity=report.applied.get("viscosity", ""),
        color=report.applied.get("color", ""),
        volume_from=report.applied.get("volume_from", ""),
        volume_to=report.applied.get("volume_to", ""),
        composition=report.applied.get("composition", ""),
        article=report.applied.get("article", ""),
    )


def filter_title(field_name: str) -> str:
    titles = {
        "client_group": "Клієнтська група",
        "brand": "Бренд",
        "liquid_type": "Тип",
        "viscosity": "В'язкість",
        "volume_from": "Об'єм від",
        "volume_to": "Об'єм до",
        "article": "Номер / артикул",
    }
    return titles.get(field_name, field_name)


def validate_products_match_filters(
    products: List[CatalogProduct],
    filters: LiquidsFilters,
    debug_dir,
) -> None:
    if not products:
        return

    mismatches: List[str] = []

    for product in products[: min(len(products), 10)]:
        mismatch = product_filter_mismatch(product, filters)
        if mismatch:
            mismatches.append(mismatch)

    if not mismatches:
        return

    active = filters.active_values()
    sample = [
        {
            "article": product.article,
            "name": product.name,
            "brand": product.brand,
            "type": product.liquid_type,
            "viscosity": product.viscosity,
            "capacity": product.capacity,
        }
        for product in products[:5]
    ]
    debug_log(
        f"Liquids result validation failed. Filters={active}. Sample={sample}. "
        f"Mismatch={mismatches[0]}",
        debug_dir,
    )
    raise RuntimeError(
        "CRM повернула товари не за заданими фільтрами. "
        f"Пошук зупинено: {mismatches[0]}"
    )


def product_filter_mismatch(product: CatalogProduct, filters: LiquidsFilters) -> Optional[str]:
    product_title = " ".join(part for part in (product.article, product.name) if part).strip()

    if filters.brand and not (
        text_matches(filters.brand, product.brand)
        or not product.brand
        or _brand_is_product_type(product.brand)
    ):
        return f"бренд очікували {filters.brand}, отримали {product.brand or 'порожньо'}"

    if filters.liquid_type and not text_matches(filters.liquid_type, product.liquid_type):
        return f"тип очікували {filters.liquid_type}, отримали {product.liquid_type or 'порожньо'}"

    if filters.viscosity and not text_matches(filters.viscosity, product.viscosity):
        return f"в'язкість очікували {filters.viscosity}, отримали {product.viscosity or 'порожньо'}"

    capacity_mismatch = validate_capacity(product.capacity, filters.volume_from, filters.volume_to)
    if capacity_mismatch:
        return capacity_mismatch

    if filters.article:
        haystack = " ".join(part for part in (product.article, product.name) if part)
        if not text_contains(haystack, filters.article):
            return f"номер / артикул очікували {filters.article}, отримали {product_title or 'порожньо'}"

    return None


def normalize_compare_text(value: str) -> str:
    text = value or ""
    for dash in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"):
        text = text.replace(dash, "-")
    text = text.lower()
    return re.sub(r"[^0-9a-zа-яіїєґ]+", "", text)


def text_matches(expected: str, actual: str) -> bool:
    expected_norm = normalize_compare_text(expected)
    actual_norm = normalize_compare_text(actual)
    return bool(expected_norm and expected_norm == actual_norm)


def text_contains(actual: str, expected: str) -> bool:
    expected_norm = normalize_compare_text(expected)
    actual_norm = normalize_compare_text(actual)
    return bool(expected_norm and expected_norm in actual_norm)


def parse_decimal(value: str) -> Optional[float]:
    if not value:
        return None
    match = re.search(r"\d+(?:[.,]\d+)?", str(value))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def validate_capacity(capacity: str, volume_from: str, volume_to: str) -> Optional[str]:
    minimum = parse_decimal(volume_from)
    maximum = parse_decimal(volume_to)
    if minimum is None and maximum is None:
        return None

    actual = parse_decimal(capacity)
    expected = []
    if minimum is not None:
        expected.append(f"від {minimum:g}")
    if maximum is not None:
        expected.append(f"до {maximum:g}")
    expected_text = " ".join(expected)

    if actual is None:
        return f"об'єм очікували {expected_text}, отримали {capacity or 'порожньо'}"

    tolerance = 0.001
    if minimum is not None and actual + tolerance < minimum:
        return f"об'єм очікували {expected_text}, отримали {capacity}"
    if maximum is not None and actual - tolerance > maximum:
        return f"об'єм очікували {expected_text}, отримали {capacity}"

    return None


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
        return ["❌ По заданим критеріям нічого не знайдено."]

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
