# -*- coding: utf-8 -*-

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


SELECTORS: Dict[str, Any] = {
    "overlay": "div.q-loading, .q-inner-loading, .loading, [role='progressbar']",
    "shell": {
        "sidebar": "//aside | //div[contains(@class,'q-drawer')] | //nav",
        "dashboard_ready": (
            "//aside | //div[contains(@class,'q-drawer')] | //nav | "
            "//main | //div[contains(@class,'q-page')]"
        ),
        "liquids_sidebar": [
            "//aside//*[contains(normalize-space(),'Рідини') or contains(normalize-space(),'Liquids')]",
            (
                "//div[contains(@class,'q-drawer')]//*[contains(normalize-space(),'Рідини') "
                "or contains(normalize-space(),'Liquids')]"
            ),
            "//nav//*[contains(normalize-space(),'Рідини') or contains(normalize-space(),'Liquids')]",
            "//a[contains(@href,'/console/liquid')]",
        ],
        "liquids_tab": (
            "//*[contains(@class,'q-tab') or contains(@class,'q-router-link') or contains(@class,'q-item')]"
            "[contains(normalize-space(),'Рідини') or contains(normalize-space(),'Liquids')]"
        ),
    },
    "login": {
        "af_ids_button": "//button[.//div[contains(text(),'AF IDS')] or contains(.,'AF IDS')]",
        "username": "//input[@name='Username' or @name='username']",
        "password": "//input[@name='Password' or @name='password']",
        "submit": "//button[contains(.,'Вход') or contains(.,'Login') or contains(.,'Sign in')]",
        "cookies": "//button[contains(.,'Accept') or contains(.,'Принять') or contains(.,'Прийняти')]",
    },
    "liquids": {
        "search_button": (
            ".//button[contains(.,'Пошук') or contains(.,'Search')] | "
            ".//*[contains(@class,'q-btn')][contains(.,'Пошук') or contains(.,'Search')]"
        ),
        "filter_panel": (
            "//*[.//*[contains(normalize-space(),'Фільтри') or contains(normalize-space(),'Filters') "
            "or contains(normalize-space(),'FILTER')]][.//input]"
            "[contains(@class,'q-card') or contains(@class,'q-page') or contains(@class,'q-pa') "
            "or contains(@class,'q-layout') or contains(@class,'q-tab-panel') or self::div]"
        ),
        "results_area": (
            "//table | //div[contains(@class,'q-table')] | "
            "//div[contains(.,'Основна колекція')] | //div[contains(@class,'q-card')]"
        ),
        "empty_state": "//*[contains(.,'Ой, нічогісінько') or contains(.,'нічого') or contains(.,'No data')]",
        "filters": {
            "brand": {
                "labels": ["Бренди", "Бренд", "Brands", "Brand"],
                "placeholders": ["Бренди", "Бренд", "Brands", "Brand"],
            },
            "liquid_type": {
                "labels": ["Тип", "Type"],
                "placeholders": ["Тип", "Type"],
            },
            "viscosity": {
                "labels": ["В'язкості", "В’язкості", "Вязкості", "Viscosity", "Viscosities"],
                "placeholders": ["В'язкості", "В’язкості", "Вязкості", "Viscosity", "Viscosities"],
            },
            "color": {
                "labels": ["Колір", "Color"],
                "placeholders": ["Колір", "Color"],
            },
            "volume_from": {
                "labels": ["Від", "From"],
                "placeholders": ["Від", "From"],
            },
            "volume_to": {
                "labels": ["До", "To"],
                "placeholders": ["До", "To"],
            },
            "composition": {
                "labels": ["Специфікації", "Склад", "Composition", "Specification", "Specifications"],
                "placeholders": ["Специфікації", "Склад", "Composition", "Specification", "Specifications"],
            },
            "article": {
                "labels": ["Номер", "Артикул", "Article", "Number"],
                "placeholders": ["Номер", "Артикул", "Article", "Number"],
            },
        },
    },
}


def debug_log(message: str, debug_dir: Optional[Path] = None) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {message}"
    print(line, flush=True)
    if not debug_dir:
        return
    debug_dir.mkdir(parents=True, exist_ok=True)
    with (debug_dir / "catalog_search.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def save_debug_screenshot(driver, debug_dir: Path, name: str) -> Path:
    debug_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name)
    path = debug_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_name}.png"
    driver.save_screenshot(str(path))
    return path


def wait_overlay_gone(driver, timeout: int = 25) -> None:
    try:
        WebDriverWait(driver, timeout).until_not(
            EC.presence_of_element_located((By.CSS_SELECTOR, SELECTORS["overlay"]))
        )
    except TimeoutException:
        pass


def wait_any_xpath(driver, xpath: str, timeout: int = 25):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )


def wait_results_loaded(driver, timeout: int = 30) -> None:
    wait_overlay_gone(driver, timeout)
    WebDriverWait(driver, timeout).until(
        EC.any_of(
            EC.presence_of_element_located((By.XPATH, SELECTORS["liquids"]["results_area"])),
            EC.presence_of_element_located((By.XPATH, SELECTORS["liquids"]["empty_state"])),
        )
    )
    time.sleep(0.5)
    wait_overlay_gone(driver, 10)


def require_liquids_page(driver) -> None:
    current_url = driver.current_url or ""
    if "/console/liquid" not in current_url:
        raise RuntimeError(f"Очікувалась сторінка Рідини, але зараз відкрито: {current_url}")


def safe_click(driver, el) -> bool:
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.05)
        el.click()
        return True
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", el)
            return True
        except Exception:
            return False


def quasar_get_value(driver, inp) -> str:
    try:
        return (inp.get_attribute("value") or "").strip()
    except Exception:
        try:
            return (driver.execute_script("return arguments[0].value || '';", inp) or "").strip()
        except Exception:
            return ""


def quasar_clear_input(driver, inp) -> None:
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", inp)
        time.sleep(0.05)
    except Exception:
        pass

    try:
        inp.click()
        inp.send_keys(Keys.COMMAND, "a")
        inp.send_keys(Keys.BACKSPACE)
    except Exception:
        pass

    driver.execute_script(
        """
        const el = arguments[0];
        el.focus();
        el.value = '';
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new Event('blur', { bubbles: true }));
        """,
        inp,
    )


def quasar_set_value(driver, inp, value: str, timeout: float = 2.0) -> None:
    value = (value or "").strip()
    quasar_clear_input(driver, inp)

    try:
        inp.click()
        inp.send_keys(value)
        time.sleep(0.1)
        click_matching_quasar_option(driver, value)
        inp.send_keys(Keys.TAB)
    except Exception:
        pass

    driver.execute_script(
        """
        const el = arguments[0];
        const val = arguments[1];
        el.focus();
        el.value = val;
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new Event('blur', { bubbles: true }));
        """,
        inp,
        value,
    )

    t0 = time.time()
    while time.time() - t0 < timeout:
        if quasar_get_value(driver, inp):
            return
        time.sleep(0.1)


def xpath_literal(value: str) -> str:
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    parts = value.split("'")
    return "concat(" + ', "\"\'\"", '.join(f"'{part}'" for part in parts) + ")"


def _candidate_input_xpath(labels: Iterable[str], placeholders: Iterable[str]) -> str:
    label_checks = []
    for label in labels:
        literal = xpath_literal(label)
        label_checks.append(f"@aria-label={literal}")
        label_checks.append(f"contains(@aria-label,{literal})")

    placeholder_checks = []
    for placeholder in placeholders:
        literal = xpath_literal(placeholder)
        placeholder_checks.append(f"@placeholder={literal}")
        placeholder_checks.append(f"contains(@placeholder,{literal})")

    checks = label_checks + placeholder_checks
    direct = ".//input[" + " or ".join(checks) + "]"

    field_checks = []
    for label in labels:
        literal = xpath_literal(label)
        field_checks.append(f".//*[normalize-space()={literal} or contains(normalize-space(),{literal})]")
    via_field = (
        ".//*[contains(@class,'q-field') or contains(@class,'q-select') or contains(@class,'q-input')]"
        "[" + " or ".join(field_checks) + "]//input"
    )
    return f"({direct}) | ({via_field})"


def find_liquids_filter_panel(driver):
    panels = driver.find_elements(By.XPATH, SELECTORS["liquids"]["filter_panel"])
    visible_panels = [panel for panel in panels if panel.is_displayed()]
    if not visible_panels:
        raise RuntimeError("Не знайшов блок фільтрів на сторінці Рідини")

    # Prefer the smallest visible block that still contains all filters. This avoids
    # accidentally using the global header search or another open tab.
    visible_panels.sort(key=lambda panel: panel.size.get("height", 999999) * panel.size.get("width", 999999))
    return visible_panels[0]


def find_filter_input(driver, filter_name: str, timeout: int = 10):
    require_liquids_page(driver)
    config = SELECTORS["liquids"]["filters"][filter_name]
    xpath = _candidate_input_xpath(config.get("labels", []), config.get("placeholders", []))
    end_at = time.time() + timeout
    last_error = None

    while time.time() < end_at:
        try:
            panel = find_liquids_filter_panel(driver)
            inputs = panel.find_elements(By.XPATH, xpath)
            visible = [inp for inp in inputs if inp.is_displayed()]
            if visible:
                return visible[0]
        except Exception as exc:
            last_error = exc
        time.sleep(0.2)

    raise RuntimeError(f"Filter input not found: {filter_name}. Last error: {last_error}")


def click_matching_quasar_option(driver, value: str) -> bool:
    value_norm = value.strip().lower()
    if not value_norm:
        return False
    value_norm_literal = xpath_literal(value_norm)
    value_literal = xpath_literal(value)

    option_xpaths = [
        (
            "//*[contains(@class,'q-menu') or contains(@class,'q-virtual-scroll') or "
            "contains(@class,'q-item')]//*[contains(translate(normalize-space(), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZАБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ', "
            "'abcdefghijklmnopqrstuvwxyzабвгґдеєжзиіїйклмнопрстуфхцчшщьюя'), "
            f"{value_norm_literal})]"
        ),
        (
            "//*[contains(@class,'q-menu') or contains(@class,'q-virtual-scroll')]"
            f"//*[normalize-space()={value_literal}]"
        ),
    ]

    for xpath in option_xpaths:
        try:
            options = driver.find_elements(By.XPATH, xpath)
            visible = [opt for opt in options if opt.is_displayed()]
            if visible:
                return safe_click(driver, visible[0])
        except Exception:
            pass

    try:
        active = driver.switch_to.active_element
        active.send_keys(Keys.ENTER)
        return True
    except Exception:
        return False


def set_filter_value(driver, filter_name: str, value: str) -> None:
    value = (value or "").strip()
    if not value:
        return
    inp = find_filter_input(driver, filter_name)
    quasar_set_value(driver, inp, value)
