# -*- coding: utf-8 -*-

import re
from dataclasses import dataclass
from typing import Dict, List
from urllib.parse import unquote, urlparse

from selenium.webdriver.common.by import By


@dataclass
class CatalogProduct:
    article: str = ""
    name: str = ""
    brand: str = ""
    liquid_type: str = ""
    specifications: str = ""
    viscosity: str = ""
    capacity: str = ""
    cost: str = ""
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
            "liquid_type": self.liquid_type,
            "specifications": self.specifications,
            "viscosity": self.viscosity,
            "capacity": self.capacity,
            "cost": self.cost,
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
ICON_WORD_RE = re.compile(
    r"\b(?:event|access_time|star|star_border|star_half|tag|shopping_cart|sync|info|content_copy)\b",
    re.IGNORECASE,
)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def clean_icon_text(value: str) -> str:
    return clean_text(ICON_WORD_RE.sub(" ", value or ""))


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

            cell_elements = row.find_elements(By.XPATH, ".//td")
            cells = [cell_text_with_inputs(td) for td in cell_elements]
            cells, cell_elements = align_cells_to_headers(headers, cells, cell_elements)
            if not cells or not any(cells):
                continue

            product = product_from_table_cells(headers, cells, cell_elements)
            product.url = extract_row_url(row)
            if product.article or product.name or product.price:
                products.append(product)

            if len(products) >= limit:
                return products

    return products


def product_from_table_cells(headers: List[str], cells: List[str], cell_elements=None) -> CatalogProduct:
    def by_header(*needles: str) -> str:
        index = header_index(headers, *needles)
        if index is None or index >= len(cells):
            return ""
        return cells[index]

    article_raw = by_header("article", "артикул", "номер")
    name_raw = by_header("name", "назва", "опис", "description")

    brand_index = header_index(headers, "brand", "бренд")
    brand = ""
    if brand_index is not None and cell_elements and brand_index < len(cell_elements):
        brand = extract_brand_from_cell(cell_elements[brand_index])
    if not brand:
        brand = clean_brand_text(by_header("brand", "бренд"))
    if not brand:
        brand = infer_brand_from_name(article_raw or name_raw)

    article = clean_article_title(article_raw, brand)
    name = clean_article_title(name_raw, brand)

    liquid_type = clean_icon_text(by_header("type", "тип"))
    specifications = clean_icon_text(by_header("specifications", "специф", "склад"))
    viscosity = clean_icon_text(by_header("viscosity", "в'яз", "вязк"))
    capacity = clean_icon_text(by_header("capacity", "об'єм", "обʼєм", "volume"))
    cost = by_header("cost", "собіварт", "закуп")
    joined = "\n".join(cells)
    price = by_header("price", "ціна", "цена") or first_match(PRICE_RE, joined)
    availability = clean_availability(by_header("available", "availability", "наяв", "доступ", "stock", "qty", "залиш"))
    delivery = clean_delivery(by_header("delivery", "достав"))

    return CatalogProduct(
        article=article,
        name=name,
        brand=brand,
        liquid_type=liquid_type,
        specifications=specifications,
        viscosity=viscosity,
        capacity=capacity,
        cost=cost,
        price=price,
        availability=availability,
        delivery=delivery,
    )


def header_index(headers: List[str], *needles: str):
    for index, header in enumerate(headers):
        if any(needle in header for needle in needles):
            return index
    return None


def align_cells_to_headers(headers: List[str], cells: List[str], cell_elements):
    if len(cells) == len(headers) + 1 and headers:
        first_header = headers[0]
        if not any(word in first_header for word in ("image", "зображ", "фото")):
            try:
                first_has_image = bool(cell_elements[0].find_elements(By.XPATH, ".//img"))
            except Exception:
                first_has_image = False
            if first_has_image:
                return cells[1:], cell_elements[1:]
    return cells, cell_elements


def cell_text_with_inputs(cell) -> str:
    parts = []
    try:
        for inp in cell.find_elements(By.XPATH, ".//input"):
            value = clean_text(inp.get_attribute("value") or "")
            if value:
                parts.append(value)
    except Exception:
        pass

    text = clean_text(cell.text or "")
    if text:
        parts.append(text)

    cleaned = []
    for part in parts:
        if part not in cleaned:
            cleaned.append(part)
    return clean_text(" ".join(cleaned))


def article_and_name_from_text(value: str):
    text = clean_icon_text(value)
    article = first_match(ARTICLE_RE, text)
    name = clean_product_name(text, article)
    return article, name


def clean_product_name(value: str, article: str = "") -> str:
    text = clean_icon_text(value)
    if article:
        text = clean_text(text.replace(article, " ", 1))
    return clean_text(text)


def clean_article_title(value: str, brand: str = "") -> str:
    text = clean_product_name(value)
    brand = clean_brand_text(brand)
    if not text or not brand:
        return text

    match = re.search(rf"\b{re.escape(brand)}\b", text, flags=re.IGNORECASE)
    if not match:
        return text

    prefix = text[:match.start()]
    if not any(looks_like_product_code(token) for token in prefix.split()):
        return clean_text(text[match.start():])
    return text


def clean_brand_text(value: str) -> str:
    text = clean_icon_text(value)
    if re.fullmatch(r"\d+(?:[.,]\d+)?\s*(?:l|л|ml|мл)", text, flags=re.IGNORECASE):
        return ""
    if not text or not re.search(r"[A-Za-zА-Яа-я]", text):
        return ""
    return text


def extract_brand_from_cell(cell) -> str:
    try:
        for image in cell.find_elements(By.XPATH, ".//img"):
            for attr in ("alt", "title", "aria-label"):
                brand = clean_brand_text(image.get_attribute(attr) or "")
                if brand:
                    return brand

            src_brand = brand_from_url(image.get_attribute("src") or "")
            if src_brand:
                return src_brand
    except Exception:
        pass
    return ""


def brand_from_url(value: str) -> str:
    if not value:
        return ""
    path = unquote(urlparse(value).path)
    filename = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    filename = re.sub(r"[_-]+", " ", filename)
    filename = re.sub(r"\b(?:logo|brand|image|img)\b", " ", filename, flags=re.IGNORECASE)
    filename = clean_brand_text(filename)
    if 2 <= len(filename) <= 40 and not re.fullmatch(r"[0-9a-f]{8,}", filename, flags=re.IGNORECASE):
        return filename.upper()
    return ""


def infer_brand_from_name(value: str) -> str:
    text = clean_text(value)
    if not text:
        return ""
    for token in text.split():
        token = clean_brand_text(token)
        if not token:
            continue
        if looks_like_viscosity(token) or looks_like_capacity(token) or looks_like_spec(token):
            continue
        if looks_like_product_code(token):
            continue
        if re.search(r"[A-Za-zА-Яа-я]", token):
            return token
    return ""


def looks_like_product_code(value: str) -> bool:
    token = clean_text(value)
    if looks_like_viscosity(token) or looks_like_capacity(token) or looks_like_spec(token):
        return False
    return bool(re.search(r"\d", token) and len(token) >= 5)


def looks_like_viscosity(value: str) -> bool:
    return bool(re.fullmatch(r"\d{1,2}w[- ]?\d{1,2}", value or "", flags=re.IGNORECASE))


def looks_like_capacity(value: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:[.,]\d+)?\s*(?:l|л|ml|мл)", value or "", flags=re.IGNORECASE))


def looks_like_spec(value: str) -> bool:
    token = value or ""
    if "-" in token or "/" in token:
        return bool(re.fullmatch(r"[A-ZА-Я]{1,4}[-/]?[A-ZА-Я]?\d(?:/[A-ZА-Я]?\d)?", token, flags=re.IGNORECASE))
    return bool(re.fullmatch(r"[AC]\d", token, flags=re.IGNORECASE))


def clean_availability(value: str) -> str:
    text = clean_icon_text(value)
    match = re.search(r"\b(\d+)\s*(?:of|з|із)\s*(\d+)\b", text, re.IGNORECASE)
    if match:
        return f"{match.group(1)} of {match.group(2)}"
    match = re.search(r"\b\d+\b", text)
    if match:
        return match.group(0)
    return ""


def clean_delivery(value: str) -> str:
    text = clean_icon_text(value)
    match = re.search(r"\b(\d+)\s+(\d{1,2}:\d{2})\b", text)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return text


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
