# -*- coding: utf-8 -*-

import re
from dataclasses import dataclass
from typing import Dict, List

from selenium.webdriver.common.by import By


@dataclass
class CatalogProduct:
    article: str = ""
    name: str = ""
    brand: str = ""
    price: str = ""
    availability: str = ""
    warehouse: str = ""
    delivery: str = ""
    url: str = ""

    def as_dict(self) -> Dict[str, str]:
        return {
            "article": self.article,
            "name": self.name,
            "brand": self.brand,
            "price": self.price,
            "availability": self.availability,
            "warehouse": self.warehouse,
            "delivery": self.delivery,
            "url": self.url,
        }


PRICE_RE = re.compile(r"(?:€|EUR)\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*(?:€|EUR)")
ARTICLE_RE = re.compile(r"\b(?=[A-ZА-Я0-9._/-]*\d)[A-ZА-Я0-9][A-ZА-Я0-9._/-]{2,}\b")
WAREHOUSE_RE = re.compile(r"\bAF\d+\b|\b[A-Z]{1,4}\d{1,4}\b")
DELIVERY_RE = re.compile(r"\b\d+\s*(?:день|дні|днів|day|days)\b", re.IGNORECASE)
AVAILABILITY_RE = re.compile(r"(?:наявність|stock|qty|залишок)\D{0,20}(\d+)", re.IGNORECASE)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_products(driver, limit: int = 20) -> List[CatalogProduct]:
    products = parse_table_products(driver, limit=limit)
    if products:
        return products[:limit]
    return parse_card_products(driver, limit=limit)


def parse_table_products(driver, limit: int = 20) -> List[CatalogProduct]:
    tables = driver.find_elements(By.XPATH, "//table")
    products: List[CatalogProduct] = []

    for table in tables:
        if not table.is_displayed():
            continue

        headers = [
            clean_text(th.text).lower()
            for th in table.find_elements(By.XPATH, ".//thead//th")
        ]
        rows = table.find_elements(By.XPATH, ".//tbody/tr")

        for row in rows:
            if not row.is_displayed():
                continue

            cells = [clean_text(td.text) for td in row.find_elements(By.XPATH, ".//td")]
            if not cells or not any(cells):
                continue

            product = product_from_table_cells(headers, cells)
            product.url = extract_row_url(row)
            if product.article or product.name or product.price:
                products.append(product)

            if len(products) >= limit:
                return products

    return products


def product_from_table_cells(headers: List[str], cells: List[str]) -> CatalogProduct:
    def by_header(*needles: str) -> str:
        for index, header in enumerate(headers):
            if index >= len(cells):
                continue
            if any(needle in header for needle in needles):
                return cells[index]
        return ""

    joined = "\n".join(cells)
    article = by_header("article", "артикул", "номер") or first_match(ARTICLE_RE, joined)
    name = by_header("name", "назва", "опис", "description") or first_non_empty(cells)
    brand = by_header("brand", "бренд")
    price = by_header("price", "ціна", "цена") or first_match(PRICE_RE, joined)
    availability = by_header("availability", "наяв", "доступ", "stock", "qty", "залиш")
    warehouse = by_header("warehouse", "склад") or first_match(WAREHOUSE_RE, joined)
    delivery = by_header("delivery", "достав") or first_match(DELIVERY_RE, joined)

    return CatalogProduct(
        article=article,
        name=name,
        brand=brand,
        price=price,
        availability=availability,
        warehouse=warehouse,
        delivery=delivery,
    )


def parse_card_products(driver, limit: int = 20) -> List[CatalogProduct]:
    candidates = driver.find_elements(
        By.XPATH,
        (
            "//*[contains(@class,'q-card') or contains(@class,'product') or contains(@class,'card')]"
            "[.//*[contains(text(),'€') or contains(text(),'EUR')] or contains(.,'€') or contains(.,'EUR')]"
        ),
    )
    products: List[CatalogProduct] = []
    seen = set()

    for card in candidates:
        if not card.is_displayed():
            continue

        raw_text = card.text or ""
        text = clean_text(raw_text)
        if not text or text in seen:
            continue
        seen.add(text)

        product = product_from_card_text(raw_text)
        product.url = extract_row_url(card)

        if product.article or product.name or product.price:
            products.append(product)

        if len(products) >= limit:
            return products

    return products


def product_from_card_text(text: str) -> CatalogProduct:
    lines = [clean_text(line) for line in text.splitlines() if clean_text(line)]
    if len(lines) <= 1:
        lines = [part for part in re.split(r"\s{2,}", text) if part]

    title = lines[0] if lines else text
    article = first_match(ARTICLE_RE, title)
    name = title

    if article and article in title:
        name = clean_text(title.replace(article, ""))

    price = first_match(PRICE_RE, text)
    warehouse = first_match(WAREHOUSE_RE, text)
    delivery = first_match(DELIVERY_RE, text)
    availability = ""
    match = AVAILABILITY_RE.search(text)
    if match:
        availability = match.group(1)

    brand = ""
    if article:
        brand = clean_text(title.split(article)[0])
    elif lines:
        brand = lines[0].split(" ")[0]

    return CatalogProduct(
        article=article,
        name=name,
        brand=brand,
        price=price,
        availability=availability,
        warehouse=warehouse,
        delivery=delivery,
    )


def extract_row_url(element) -> str:
    try:
        link = element.find_element(By.XPATH, ".//a[@href]")
        return link.get_attribute("href") or ""
    except Exception:
        pass

    try:
        nearest = element.find_element(By.XPATH, "./ancestor-or-self::*[@href][1]")
        return nearest.get_attribute("href") or ""
    except Exception:
        pass

    for attr in ("data-id", "data-row-key", "id"):
        try:
            value = element.get_attribute(attr)
            if value:
                return value
        except Exception:
            pass

    return ""


def first_match(pattern: re.Pattern, text: str) -> str:
    match = pattern.search(text or "")
    if not match:
        return ""
    return clean_text(match.group(0))


def first_non_empty(values: List[str]) -> str:
    for value in values:
        if clean_text(value):
            return clean_text(value)
    return ""
