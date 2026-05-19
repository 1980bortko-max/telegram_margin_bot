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

from .runtime_settings import is_catalog_search_headless


SELECTORS: Dict[str, Any] = {
    "overlay": "div.q-loading, .q-inner-loading, .loading, [role='progressbar']",
    "shell": {
        "sidebar": "//aside | //div[contains(@class,'q-drawer')] | //nav",
        "dashboard_ready": (
            "//aside | //div[contains(@class,'q-drawer')] | //nav | "
            "//main | //div[contains(@class,'q-page')]"
        ),
        "liquids_sidebar": [
            "//a[contains(@href,'/console/liquid')]",
            "//aside//*[contains(normalize-space(),'Рідини') or contains(normalize-space(),'Liquids')]",
            (
                "//div[contains(@class,'q-drawer')]//*[contains(normalize-space(),'Рідини') "
                "or contains(normalize-space(),'Liquids')]"
            ),
            "//nav//*[contains(normalize-space(),'Рідини') or contains(normalize-space(),'Liquids')]",
        ],
        "liquids_tab": (
            "//*[contains(@class,'q-tab') or contains(@class,'q-router-link') or contains(@class,'q-item')]"
            "[contains(normalize-space(),'Рідини') or contains(normalize-space(),'Liquids')]"
        ),
        "client_group_labels": ["Client group", "Клієнтська група", "Клиентская группа"],
        "client_group_update_buttons": [
            "NEU LADEN",
            "RELOAD",
            "UPDATE",
            "ОНОВИТИ",
            "ОБНОВИТЬ",
            "ОБНОВИТИ",
        ],
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
        "search_button_global": (
            "//button[contains(normalize-space(.),'Пошук') or contains(normalize-space(.),'Search')] | "
            "//*[contains(@class,'q-btn')]"
            "[contains(normalize-space(.),'Пошук') or contains(normalize-space(.),'Search')]"
        ),
        "filter_panel": (
            "//*[.//*[contains(normalize-space(),'Фільтри') or contains(normalize-space(),'Filters') "
            "or contains(normalize-space(),'FILTER')]][.//input]"
            "[contains(@class,'q-card') or contains(@class,'q-page') or contains(@class,'q-pa') "
            "or contains(@class,'q-layout') or contains(@class,'q-tab-panel') or self::div]"
        ),
        "filter_panel_css": (
            ".filter-tires-container, .filter-liquids-container, "
            ".filter-tires-body-card, .filter-liquids-body-card"
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
                "labels": ["# Number", "# Номер", "Номер", "Артикул", "Article", "Number"],
                "placeholders": ["# Number", "# Номер", "Номер", "Артикул", "Article", "Number"],
            },
        },
    },
}

QUASAR_OPTION_CSS = (
    ".q-menu .q-item, "
    ".q-menu [role='option'], "
    ".q-virtual-scroll__content .q-item, "
    "[role='listbox'] .q-item, "
    ".q-item[role='option']"
)


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


def clickable_ancestor(driver, el):
    try:
        return driver.execute_script(
            """
            const el = arguments[0];
            return el.closest('a[href], button, [role="button"], .q-item, .q-btn') || el;
            """,
            el,
        )
    except Exception:
        return el


def visible_text(driver, el) -> str:
    try:
        return (
            driver.execute_script(
                "return arguments[0].innerText || arguments[0].textContent || '';",
                el,
            )
            or ""
        )
    except Exception:
        try:
            return el.text or ""
        except Exception:
            return ""


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

    field = None
    is_select = False
    try:
        field = driver.execute_script(
            "return arguments[0].closest('.q-field, .q-select, .q-input') || arguments[0];",
            inp,
        )
        is_select = bool(
            driver.execute_script(
                "return !!arguments[0].closest('.q-select');",
                inp,
            )
        )
    except Exception:
        field = inp

    try:
        safe_click(driver, field or inp)
        time.sleep(0.25)
        if click_matching_quasar_option(driver, value) and wait_field_choice(driver, field or inp, value):
            return
        driver.execute_script(
            """
            const el = arguments[0];
            el.removeAttribute('readonly');
            el.removeAttribute('disabled');
            el.focus();
            """,
            inp,
        )
        inp.send_keys(value)
        time.sleep(0.35)
        if click_matching_quasar_option(driver, value) and wait_field_choice(driver, field or inp, value):
            return
        inp.send_keys(Keys.TAB)
    except Exception:
        pass

    if is_select:
        raise RuntimeError(f"Не вдалося вибрати значення зі списку: {value}")

    driver.execute_script(
        """
        const el = arguments[0];
        const val = arguments[1];
        el.removeAttribute('readonly');
        el.removeAttribute('disabled');
        el.focus();
        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
        if (setter) {
            setter.call(el, val);
        } else {
            el.value = val;
        }
        el.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true, inputType: 'insertText', data: val }));
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


def find_filter_field(driver, filter_name: str, timeout: int = 10):
    require_liquids_page(driver)
    config = SELECTORS["liquids"]["filters"][filter_name]
    targets = [
        normalize_choice_text(value)
        for value in list(config.get("labels", [])) + list(config.get("placeholders", []))
    ]
    end_at = time.time() + timeout
    last_error = None

    while time.time() < end_at:
        try:
            panel = find_liquids_filter_panel(driver)
            field = driver.execute_script(
                """
                const panel = arguments[0];
                const targets = arguments[1];
                const filterName = arguments[2];
                const norm = (value) => String(value || '')
                    .replace(/[\\u2010\\u2011\\u2012\\u2013\\u2014\\u2212]/g, '-')
                    .trim()
                    .replace(/\\s+/g, ' ')
                    .toLowerCase();
                const visible = (el) => {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    return rect.width > 0 && rect.height > 0 &&
                        style.display !== 'none' && style.visibility !== 'hidden';
                };
                const fields = Array.from(panel.querySelectorAll('.q-field, .q-select, .q-input'))
                    .filter(visible);
                if (filterName === 'liquid_type') {
                    const labelElement = Array.from(panel.querySelectorAll('*'))
                        .filter(visible)
                        .find((el) => norm(el.innerText || el.textContent || '') === 'type');
                    const labelField = labelElement && labelElement.closest('.q-field, .q-select, .q-input');
                    if (labelField && visible(labelField)) {
                        return labelField;
                    }
                    const typeField = fields.find((field) => {
                        const text = norm(field.innerText || field.textContent || '');
                        return (text === 'type' || text.startsWith('type ')) &&
                            !text.includes('specification') &&
                            !text.includes('viscos') &&
                            !text.includes('brand') &&
                            !text.includes('color');
                    });
                    if (typeField) {
                        return typeField;
                    }
                }
                for (const field of fields) {
                    const label = field.querySelector('.q-field__label');
                    const input = field.querySelector('input');
                    const labelNorm = norm(label && label.innerText);
                    if (targets.includes(labelNorm)) {
                        return field;
                    }
                }
                for (const field of fields) {
                    const input = field.querySelector('input');
                    const values = [
                        input && input.placeholder,
                        input && input.getAttribute('aria-label')
                    ].map(norm);
                    if (values.some((value) => targets.includes(value))) {
                        return field;
                    }
                }
                return null;
                """,
                panel,
                targets,
                filter_name,
            )
            if field and field.is_displayed():
                return field
        except Exception as exc:
            last_error = exc
        time.sleep(0.2)

    raise RuntimeError(f"Filter field not found: {filter_name}. Last error: {last_error}")


def find_client_group_field(driver, timeout: int = 10):
    targets = [
        normalize_choice_text(value)
        for value in SELECTORS["shell"]["client_group_labels"]
    ]
    end_at = time.time() + timeout
    last_error = None

    while time.time() < end_at:
        try:
            field = driver.execute_script(
                """
                const targets = arguments[0];
                const norm = (value) => String(value || '')
                    .replace(/[\\u2010\\u2011\\u2012\\u2013\\u2014\\u2212]/g, '-')
                    .trim()
                    .replace(/\\s+/g, ' ')
                    .toLowerCase();
                const visible = (el) => {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    return rect.width > 0 && rect.height > 0 &&
                        style.display !== 'none' && style.visibility !== 'hidden';
                };
                const isClientGroup = (field) => {
                    const label = field.querySelector('.q-field__label');
                    const input = field.querySelector('input');
                    const values = [
                        label && label.innerText,
                        input && input.placeholder,
                        input && input.getAttribute('aria-label'),
                        field.innerText || field.textContent
                    ].map(norm).filter(Boolean);

                    return values.some((value) =>
                        targets.some((target) =>
                            value === target ||
                            value.startsWith(target + ' ') ||
                            value.includes(target)
                        )
                    );
                };

                const fields = Array.from(document.querySelectorAll('.q-field, .q-select'))
                    .filter(visible)
                    .filter((field) => !field.closest(
                        '.filter-tires-container, .filter-liquids-container, ' +
                        '.filter-tires-body-card, .filter-liquids-body-card'
                    ));

                const topBarFields = fields.filter((field) =>
                    field.closest('.q-header, header, .q-toolbar, .q-layout__section--marginal')
                );
                return topBarFields.find(isClientGroup) || fields.find(isClientGroup) || null;
                """,
                targets,
            )
            if field and field.is_displayed():
                return field
        except Exception as exc:
            last_error = exc
        time.sleep(0.2)

    raise RuntimeError(f"Client group field not found. Last error: {last_error}")


def xpath_literal(value: str) -> str:
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    parts = value.split("'")
    return "concat(" + ', "\"\'\"", '.join(f"'{part}'" for part in parts) + ")"


def normalize_choice_text(value: str) -> str:
    text = value or ""
    for dash in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"):
        text = text.replace(dash, "-")
    return " ".join(text.split()).lower()


def _candidate_input_xpath(labels: Iterable[str], placeholders: Iterable[str]) -> str:
    label_checks = []
    for label in labels:
        literal = xpath_literal(label)
        label_checks.append(f"@aria-label={literal}")
        label_checks.append(f"@label={literal}")

    placeholder_checks = []
    for placeholder in placeholders:
        literal = xpath_literal(placeholder)
        placeholder_checks.append(f"@placeholder={literal}")

    checks = label_checks + placeholder_checks
    direct = ".//input[" + " or ".join(checks) + "]"

    field_checks = []
    for label in labels:
        literal = xpath_literal(label)
        field_checks.append(
            ".//*[contains(concat(' ', normalize-space(@class), ' '), ' q-field__label ') "
            f"and normalize-space()={literal}]"
        )
    via_field = (
        ".//*[contains(@class,'q-field') or contains(@class,'q-select') or contains(@class,'q-input')]"
        "[" + " or ".join(field_checks) + "]//input"
    )
    return f"({direct}) | ({via_field})"


def find_liquids_filter_panel(driver):
    panels = driver.find_elements(By.CSS_SELECTOR, SELECTORS["liquids"]["filter_panel_css"])
    visible_panels = [
        panel for panel in panels
        if panel.is_displayed() and panel.find_elements(By.XPATH, ".//input")
    ]

    if not visible_panels:
        panels = driver.find_elements(By.XPATH, SELECTORS["liquids"]["filter_panel"])
        visible_panels = [
            panel for panel in panels
            if panel.is_displayed() and panel.find_elements(By.XPATH, ".//input")
        ]

    if not visible_panels:
        raise RuntimeError("Не знайшов блок фільтрів на сторінці Рідини")

    # Pick the visible panel with the most inputs. It is the real Liquids filters
    # card; smaller matches are often individual q-field wrappers.
    visible_panels.sort(
        key=lambda panel: len([inp for inp in panel.find_elements(By.XPATH, ".//input") if inp.is_displayed()]),
        reverse=True,
    )
    return visible_panels[0]


def find_article_field(driver, timeout: int = 10):
    require_liquids_page(driver)
    end_at = time.time() + timeout
    last_error = None

    while time.time() < end_at:
        try:
            panel = find_liquids_filter_panel(driver)
            field = driver.execute_script(
                """
                const panel = arguments[0];
                const norm = (value) => String(value || '')
                    .replace(/[\\u2010\\u2011\\u2012\\u2013\\u2014\\u2212]/g, '-')
                    .trim()
                    .replace(/\\s+/g, ' ')
                    .toLowerCase();
                const visible = (el) => {
                    if (!el) return false;
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    return rect.width > 0 && rect.height > 0 &&
                        style.display !== 'none' && style.visibility !== 'hidden' && !el.disabled;
                };
                const panelFields = Array.from(panel.querySelectorAll('.q-field, .q-input'))
                    .filter(visible);
                const pageFields = Array.from(document.querySelectorAll('.q-field, .q-input'))
                    .filter(visible);
                const isNumberField = (field) => {
                    const input = field.querySelector('input, textarea');
                    if (!input) return false;

                    const label = field.querySelector('.q-field__label');
                    const prefix = field.querySelector('.q-field__prefix, .q-field__prepend');
                    const values = [
                        label && label.innerText,
                        input.placeholder,
                        input.getAttribute('aria-label'),
                        input.getAttribute('label'),
                        input.getAttribute('name'),
                        field.innerText || field.textContent,
                        prefix && prefix.innerText,
                    ].map(norm).filter(Boolean);

                    if (values.some((value) =>
                        value === 'від' ||
                        value === 'до' ||
                        value === 'from' ||
                        value === 'to' ||
                        value.includes("об'єм") ||
                        value.includes('обʼєм') ||
                        value.includes('volume') ||
                        value.includes('capacity')
                    )) {
                        return false;
                    }

                    if (values.some((value) =>
                        value === '# number' ||
                        value === '# номер' ||
                        value.includes('# number') ||
                        value.includes('# номер')
                    )) {
                        return true;
                    }

                    return values.some((value) =>
                        value === 'number' ||
                        value === 'номер' ||
                        value === 'артикул' ||
                        value.includes('number') ||
                        value.includes('номер') ||
                        value.includes('артикул')
                    );
                };

                for (const field of panelFields) {
                    if (isNumberField(field)) {
                        return field;
                    }
                }

                for (const field of pageFields) {
                    if (isNumberField(field)) {
                        return field;
                    }
                }

                const searchButtons = Array.from(document.querySelectorAll('button, .q-btn'))
                    .filter(visible)
                    .filter((button) => {
                        const text = norm(button.innerText || button.textContent);
                        return text.includes('search') || text.includes('пошук');
                    });

                for (const button of searchButtons) {
                    const searchRect = button.getBoundingClientRect();
                    const rowFields = pageFields
                        .filter((field) => field.querySelector('input, textarea'))
                        .filter((field) => {
                            const rect = field.getBoundingClientRect();
                            const centerY = rect.top + rect.height / 2;
                            return rect.left < searchRect.left &&
                                rect.right <= searchRect.left + 5 &&
                                Math.abs(centerY - (searchRect.top + searchRect.height / 2)) < 35 &&
                                rect.width > 300;
                        })
                        .sort((a, b) => b.getBoundingClientRect().right - a.getBoundingClientRect().right);
                    if (rowFields.length) {
                        return rowFields[0];
                    }
                }

                return null;
                """,
                panel,
            )
            if field and field.is_displayed():
                return field
        except Exception as exc:
            last_error = exc
        time.sleep(0.2)

    raise RuntimeError(f"Filter field not found: article. Last error: {last_error}")


def set_article_value(driver, value: str) -> None:
    value = (value or "").strip()
    inp = find_article_input(driver)
    field = driver.execute_script(
        "return arguments[0].closest('.q-field, .q-input') || arguments[0];",
        inp,
    )

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", field)
    except Exception:
        pass

    if not safe_click(driver, field):
        raise RuntimeError("Не вдалося натиснути поле Номер / артикул")

    driver.execute_script(
        """
        const el = arguments[0];
        el.removeAttribute('readonly');
        el.removeAttribute('disabled');
        el.focus();
        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
        if (setter) {
            setter.call(el, '');
        } else {
            el.value = '';
        }
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        inp,
    )

    if is_catalog_search_headless():
        _js_set_text_input(driver, inp, value)
    else:
        inp.send_keys(value)
        driver.execute_script(
            """
            const el = arguments[0];
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            el.dispatchEvent(new Event('blur', { bubbles: true }));
            """,
            inp,
        )

    end_at = time.time() + 2
    while time.time() < end_at:
        try:
            current = quasar_get_value(driver, inp)
            if current == value:
                return
        except Exception:
            pass
        time.sleep(0.1)

    raise RuntimeError("Не вдалося заповнити поле Номер / артикул")


def find_article_input(driver, timeout: int = 10):
    end_at = time.time() + timeout
    strict_xpath = _candidate_input_xpath(
        ["# Number", "# Номер"],
        ["# Number", "# Номер"],
    )

    while time.time() < end_at:
        try:
            inputs = driver.find_elements(By.XPATH, strict_xpath)
            visible = [inp for inp in inputs if inp.is_displayed() and inp.is_enabled()]
            if visible:
                return visible[0]
        except Exception:
            pass
        time.sleep(0.1)

    field = find_article_field(driver, timeout)
    end_at = time.time() + timeout

    while time.time() < end_at:
        try:
            inp = driver.execute_script(
                """
                const field = arguments[0];
                const visible = (el) => {
                    if (!el) return false;
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    return rect.width > 0 && rect.height > 0 &&
                        style.display !== 'none' && style.visibility !== 'hidden' && !el.disabled;
                };
                return Array.from(field.querySelectorAll('input, textarea')).find(visible) || null;
                """,
                field,
            )
            if inp and inp.is_displayed():
                return inp
        except Exception:
            pass
        time.sleep(0.1)

    raise RuntimeError("Filter input not found: article")


def find_filter_input(driver, filter_name: str, timeout: int = 10):
    if filter_name == "article":
        return find_article_input(driver, timeout)

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


def visible_quasar_options(driver) -> List[Any]:
    options = driver.find_elements(By.CSS_SELECTOR, QUASAR_OPTION_CSS)
    return [
        opt
        for opt in options
        if opt.is_displayed() and normalize_choice_text(visible_text(driver, opt))
    ]


def best_option_match(driver, value: str):
    value_norm = normalize_choice_text(value)
    if not value_norm:
        return None, ""

    visible = visible_quasar_options(driver)
    exact = [
        option for option in visible
        if normalize_choice_text(visible_text(driver, option)) == value_norm
    ]
    if exact:
        option = exact[0]
        return option, visible_text(driver, option).strip()

    contains = [
        option for option in visible
        if value_norm in normalize_choice_text(visible_text(driver, option))
        or normalize_choice_text(visible_text(driver, option)) in value_norm
    ]
    if contains:
        contains.sort(key=lambda option: len(normalize_choice_text(visible_text(driver, option))))
        option = contains[0]
        return option, visible_text(driver, option).strip()

    return None, ""


def click_best_quasar_option(driver, value: str, timeout: float = 4.0) -> str:
    end_at = time.time() + timeout

    while time.time() < end_at:
        try:
            option, selected_text = best_option_match(driver, value)
            if option and safe_click(driver, clickable_ancestor(driver, option)):
                time.sleep(0.3)
                return selected_text or value
        except Exception:
            pass
        time.sleep(0.1)

    return ""


def close_open_quasar_popup(driver) -> None:
    try:
        driver.switch_to.active_element.send_keys(Keys.ESCAPE)
    except Exception:
        pass
    try:
        driver.execute_script("document.body.click();")
    except Exception:
        pass


def click_matching_quasar_option(driver, value: str) -> bool:
    value_norm = normalize_choice_text(value)
    if not value_norm:
        return False

    end_at = time.time() + 3

    while time.time() < end_at:
        try:
            for option in visible_quasar_options(driver):
                if normalize_choice_text(visible_text(driver, option)) == value_norm:
                    if safe_click(driver, clickable_ancestor(driver, option)):
                        time.sleep(0.25)
                        return True
        except Exception:
            pass
        time.sleep(0.1)

    if scroll_and_click_matching_quasar_option(driver, value_norm):
        return True

    js_clicked = driver.execute_script(
        """
        const target = arguments[0];
        const norm = (value) => String(value || '')
            .replace(/[\\u2010\\u2011\\u2012\\u2013\\u2014\\u2212]/g, '-')
            .trim()
            .replace(/\\s+/g, ' ')
            .toLowerCase();
        const visible = (el) => {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            return rect.width > 0 && rect.height > 0 &&
                style.display !== 'none' && style.visibility !== 'hidden';
        };
        const candidates = Array.from(document.querySelectorAll(
            '.q-menu .q-item, .q-menu [role="option"], ' +
            '.q-virtual-scroll__content .q-item, [role="listbox"] .q-item, ' +
            '.q-item[role="option"]'
        )).filter((el) => norm(el.innerText || el.textContent) === target);
        if (!candidates.length) {
            return false;
        }
        candidates.sort((a, b) => Number(visible(b)) - Number(visible(a)));
        const el = candidates[0];
        el.scrollIntoView({ block: 'center' });
        for (const eventName of ['pointerdown', 'mousedown', 'mouseup', 'click']) {
            el.dispatchEvent(new MouseEvent(eventName, {
                bubbles: true,
                cancelable: true,
                view: window
            }));
        }
        return true;
        """,
        value_norm,
    )
    if js_clicked:
        time.sleep(0.25)
        return True

    return False


def scroll_and_click_matching_quasar_option(driver, value_norm: str) -> bool:
    try:
        driver.execute_script(
            """
            for (const el of document.querySelectorAll('.q-menu .q-virtual-scroll, .q-menu .scroll, .q-menu')) {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                if (rect.width > 0 && rect.height > 0 &&
                    style.display !== 'none' && style.visibility !== 'hidden' &&
                    el.scrollHeight > el.clientHeight + 5) {
                    el.scrollTop = 0;
                }
            }
            """
        )
    except Exception:
        pass

    for _ in range(30):
        try:
            for option in visible_quasar_options(driver):
                if normalize_choice_text(visible_text(driver, option)) == value_norm:
                    if safe_click(driver, clickable_ancestor(driver, option)):
                        time.sleep(0.25)
                        return True

            did_scroll = driver.execute_script(
                """
                const candidates = Array.from(document.querySelectorAll(
                    '.q-menu .q-virtual-scroll, .q-menu .scroll, .q-menu'
                ));
                const visible = (el) => {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    return rect.width > 0 && rect.height > 0 &&
                        style.display !== 'none' && style.visibility !== 'hidden';
                };
                const scrollable = candidates.find((el) =>
                    visible(el) && el.scrollHeight > el.clientHeight + 5
                );
                if (!scrollable) return false;
                const before = scrollable.scrollTop;
                scrollable.scrollTop = before + Math.max(80, Math.floor(scrollable.clientHeight * 0.8));
                return scrollable.scrollTop !== before;
                """
            )
            if not did_scroll:
                return False
        except Exception:
            return False
        time.sleep(0.1)

    return False


def select_quasar_option(driver, field, value: str, timeout: float = 5.0) -> None:
    value = (value or "").strip()
    end_at = time.time() + timeout

    while time.time() < end_at:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", field)
        except Exception:
            pass

        if safe_click(driver, field):
            time.sleep(0.3)
            if click_matching_quasar_option(driver, value) and wait_field_choice(driver, field, value):
                return
            if press_open_select_option(driver, field, value) and wait_field_choice(driver, field, value):
                return
            if type_into_open_quasar_search(driver, field, value):
                if click_matching_quasar_option(driver, value) and wait_field_choice(driver, field, value):
                    return
                if press_open_select_option(driver, field, value) and wait_field_choice(driver, field, value):
                    return
                if press_enter_on_open_select(driver, field) and wait_field_choice(driver, field, value):
                    return

        try:
            arrows = field.find_elements(By.CSS_SELECTOR, ".q-field__append, .q-select__dropdown-icon")
            for arrow in arrows:
                if arrow.is_displayed() and safe_click(driver, arrow):
                    time.sleep(0.3)
                    if click_matching_quasar_option(driver, value) and wait_field_choice(driver, field, value):
                        return
                    if press_open_select_option(driver, field, value) and wait_field_choice(driver, field, value):
                        return
                    if type_into_open_quasar_search(driver, field, value):
                        if click_matching_quasar_option(driver, value) and wait_field_choice(driver, field, value):
                            return
                        if press_open_select_option(driver, field, value) and wait_field_choice(driver, field, value):
                            return
                        if press_enter_on_open_select(driver, field) and wait_field_choice(driver, field, value):
                            return
        except Exception:
            pass

        time.sleep(0.2)

    raise RuntimeError(f"Не вдалося вибрати значення зі списку: {value}")


def press_enter_on_open_select(driver, field) -> bool:
    try:
        target = driver.switch_to.active_element or field
        target.send_keys(Keys.ENTER)
        time.sleep(0.3)
        return True
    except Exception:
        return False


def press_open_select_option(driver, field, value: str) -> bool:
    value_norm = normalize_choice_text(value)

    for index, option in enumerate(visible_quasar_options(driver)):
        if normalize_choice_text(visible_text(driver, option)) != value_norm:
            continue

        try:
            target = driver.switch_to.active_element or field
            for _ in range(index + 1):
                target.send_keys(Keys.ARROW_DOWN)
            target.send_keys(Keys.ENTER)
            time.sleep(0.3)
            return True
        except Exception:
            return False

    return False


def select_searchable_quasar_option_headless(
    driver,
    field,
    value: str,
    timeout: float = 12.0,
    allow_typed_value: bool = False,
) -> str:
    value = (value or "").strip()
    end_at = time.time() + timeout
    last_selected = ""

    while time.time() < end_at:
        close_open_quasar_popup(driver)
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", field)
        except Exception:
            pass

        targets = [field]
        try:
            targets.extend(
                arrow for arrow in field.find_elements(By.CSS_SELECTOR, ".q-field__append, .q-select__dropdown-icon")
                if arrow.is_displayed()
            )
        except Exception:
            pass

        for target in targets:
            close_open_quasar_popup(driver)
            if not safe_click(driver, target):
                continue
            selected = try_select_open_quasar_value(driver, field, value, allow_typed_value)
            if selected:
                return selected

        time.sleep(0.25)

    raise RuntimeError(f"Не вдалося знайти і вибрати значення зі списку: {value}")


def try_select_open_quasar_value(driver, field, value: str, allow_typed_value: bool) -> str:
    time.sleep(0.35)
    wait_quasar_options(driver, timeout=3.0)
    selected = click_best_quasar_option(driver, value, timeout=2.0)
    if selected and wait_selected_field_choice(driver, field, selected, timeout=3.0):
        return selected
    if selected and wait_selected_field_choice(driver, field, value, timeout=3.0):
        return selected

    search_input = find_open_quasar_search_input(driver, field)
    if search_input:
        type_into_quasar_search_input(driver, search_input, value)
        wait_quasar_options(driver, timeout=4.0)
        selected = click_best_quasar_option(driver, value, timeout=4.0)
        if selected and wait_selected_field_choice(driver, field, selected, timeout=4.0):
            return selected
        if selected and wait_selected_field_choice(driver, field, value, timeout=4.0):
            return selected
        try:
            search_input.send_keys(Keys.ENTER)
            search_input.send_keys(Keys.TAB)
            time.sleep(0.3)
        except Exception:
            pass
        if allow_typed_value and wait_field_choice(driver, field, value, timeout=1.0):
            return value

    return ""


def find_open_quasar_search_input(driver, field):
    return driver.execute_script(
        """
        const field = arguments[0];
        const visible = (el) => {
            if (!el || el.tagName !== 'INPUT') return false;
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            return rect.width > 0 && rect.height > 0 &&
                style.display !== 'none' && style.visibility !== 'hidden' && !el.disabled;
        };
        const candidates = [
            (
                field.contains(document.activeElement) ||
                document.activeElement?.closest?.('.q-menu, [role="listbox"], .q-virtual-scroll__content')
            ) ? document.activeElement : null,
            ...Array.from(document.querySelectorAll(
                '.q-menu input, [role="listbox"] input, .q-virtual-scroll__content input'
            )),
            ...Array.from(field.querySelectorAll('input'))
        ].filter(visible);
        return candidates.find((el) => !el.readOnly) || candidates[0] || null;
        """,
        field,
    )


def type_into_quasar_search_input(driver, search_input, value: str) -> None:
    driver.execute_script(
        """
        const el = arguments[0];
        el.removeAttribute('readonly');
        el.removeAttribute('disabled');
        el.focus();
        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
        if (setter) {
            setter.call(el, '');
        } else {
            el.value = '';
        }
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        search_input,
    )

    try:
        safe_click(driver, search_input)
        search_input.send_keys(Keys.COMMAND, "a")
        search_input.send_keys(Keys.CONTROL, "a")
        search_input.send_keys(Keys.BACKSPACE)
        search_input.send_keys(value)
        time.sleep(0.35)
        typed_value = driver.execute_script("return arguments[0].value || '';", search_input) or ""
        if normalize_choice_text(value) in normalize_choice_text(typed_value):
            return
    except Exception:
        pass

    driver.execute_script(
        """
        const el = arguments[0];
        const value = arguments[1];
        el.removeAttribute('readonly');
        el.removeAttribute('disabled');
        el.focus();

        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
        if (setter) {
            setter.call(el, '');
            setter.call(el, value);
        } else {
            el.value = value;
        }

        el.dispatchEvent(new InputEvent('input', {
            bubbles: true,
            cancelable: true,
            inputType: 'insertText',
            data: value
        }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        search_input,
        value,
    )
    time.sleep(0.5)


def clear_filter_value(driver, filter_name: str) -> None:
    try:
        if filter_name == "article":
            inp = find_article_input(driver, timeout=2)
        else:
            inp = find_filter_input(driver, filter_name, timeout=2)
        quasar_clear_input(driver, inp)
        close_open_quasar_popup(driver)
    except Exception:
        close_open_quasar_popup(driver)


def wait_quasar_options(driver, timeout: float = 4.0) -> bool:
    end_at = time.time() + timeout
    while time.time() < end_at:
        try:
            if visible_quasar_options(driver):
                return True
        except Exception:
            pass
        time.sleep(0.1)
    return False


def read_field_choice(driver, field) -> str:
    try:
        parts = driver.execute_script(
            """
            const root = arguments[0];
            const parts = [];
            const push = (value) => {
                const text = String(value || '').trim();
                if (text) parts.push(...text.split(/\\n+/));
            };
            root.querySelectorAll('.q-chip, .q-chip__content, .q-field__native').forEach((el) => {
                push(el.innerText || el.textContent || el.value || '');
            });
            root.querySelectorAll('input').forEach((el) => push(el.value || ''));
            return parts;
            """,
            field,
        )
        values = [part.strip() for part in parts if part and part.strip()]
        return values[-1] if values else ""
    except Exception:
        return ""


def selected_field_parts(driver, field) -> List[str]:
    try:
        parts = driver.execute_script(
            """
            const root = arguments[0];
            const parts = [];
            const push = (value) => {
                const text = String(value || '').trim();
                if (text) parts.push(...text.split(/\\n+/));
            };
            root.querySelectorAll('.q-chip, .q-chip__content').forEach((el) => {
                push(el.innerText || el.textContent || '');
            });
            root.querySelectorAll('.q-field__native').forEach((el) => {
                if (el.tagName === 'INPUT' && el === document.activeElement) {
                    return;
                }
                push(el.innerText || el.textContent || el.value || '');
            });
            return parts;
            """,
            field,
        )
        return [part.strip() for part in parts if part and part.strip()]
    except Exception:
        return []


def wait_selected_field_choice(driver, field, value: str, timeout: float = 3.0) -> bool:
    value_norm = normalize_choice_text(value)
    end_at = time.time() + timeout

    while time.time() < end_at:
        try:
            if visible_quasar_options(driver):
                time.sleep(0.1)
                continue
        except Exception:
            pass

        parts = selected_field_parts(driver, field)
        if any(
            normalize_choice_text(part) == value_norm or value_norm in normalize_choice_text(part)
            for part in parts
        ):
            return True
        time.sleep(0.1)

    return False


def select_searchable_quasar_option(driver, field, value: str, timeout: float = 8.0) -> None:
    value = (value or "").strip()
    end_at = time.time() + timeout

    while time.time() < end_at:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", field)
        except Exception:
            pass

        if safe_click(driver, field):
            time.sleep(0.3)
            type_into_open_quasar_search(driver, field, value)
            if click_matching_quasar_option(driver, value) and wait_field_choice(driver, field, value, timeout=3.0):
                return

        try:
            arrows = field.find_elements(By.CSS_SELECTOR, ".q-field__append, .q-select__dropdown-icon")
            for arrow in arrows:
                if arrow.is_displayed() and safe_click(driver, arrow):
                    time.sleep(0.3)
                    type_into_open_quasar_search(driver, field, value)
                    if click_matching_quasar_option(driver, value) and wait_field_choice(
                        driver,
                        field,
                        value,
                        timeout=3.0,
                    ):
                        return
        except Exception:
            pass

        time.sleep(0.2)

    raise RuntimeError(f"Не вдалося знайти і вибрати значення зі списку: {value}")


def type_into_open_quasar_search(driver, field, value: str) -> bool:
    search_input = driver.execute_script(
        """
        const field = arguments[0];
        const visible = (el) => {
            if (!el || el.tagName !== 'INPUT') return false;
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            return rect.width > 0 && rect.height > 0 &&
                style.display !== 'none' && style.visibility !== 'hidden' && !el.disabled;
        };
        const candidates = [
            document.activeElement,
            ...Array.from(field.querySelectorAll('input')),
            ...Array.from(document.querySelectorAll(
                '.q-menu input, [role="listbox"] input, .q-virtual-scroll__content input'
            ))
        ].filter(visible);

        return candidates.find((el) => !el.readOnly) || candidates[0] || null;
        """,
        field,
    )
    if not search_input:
        return False

    try:
        safe_click(driver, search_input)
        search_input.send_keys(Keys.COMMAND, "a")
        search_input.send_keys(Keys.BACKSPACE)
        search_input.send_keys(value)
        time.sleep(0.2)
        typed_value = (
            driver.execute_script("return arguments[0].value || '';", search_input)
            or ""
        )
        if normalize_choice_text(value) in normalize_choice_text(typed_value):
            time.sleep(0.3)
            return True
    except Exception:
        pass

    driver.execute_script(
        """
        const el = arguments[0];
        const value = arguments[1];
        el.removeAttribute('readonly');
        el.removeAttribute('disabled');
        el.focus();

        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
        if (setter) {
            setter.call(el, value);
        } else {
            el.value = value;
        }

        el.dispatchEvent(new InputEvent('input', {
            bubbles: true,
            cancelable: true,
            inputType: 'insertText',
            data: value
        }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        search_input,
        value,
    )
    time.sleep(0.5)
    return True


def wait_field_choice(driver, field, value: str, timeout: float = 2.0) -> bool:
    value_norm = normalize_choice_text(value)
    end_at = time.time() + timeout

    while time.time() < end_at:
        try:
            parts = driver.execute_script(
                """
                const root = arguments[0];
                const parts = [];
                const push = (value) => {
                    const text = String(value || '').trim();
                    if (text) parts.push(...text.split(/\\n+/));
                };
                push(root.innerText || root.textContent || '');
                root.querySelectorAll('input, .q-chip, .q-chip__content, .q-field__native').forEach((el) => {
                    push(el.value || el.innerText || el.textContent || '');
                });
                return parts;
                """,
                field,
            )
            if any(
                normalize_choice_text(part) == value_norm or value_norm in normalize_choice_text(part)
                for part in parts
            ):
                return True
        except Exception:
            pass
        time.sleep(0.1)

    return False


def find_liquids_search_button(driver, timeout: int = 10):
    require_liquids_page(driver)
    end_at = time.time() + timeout

    while time.time() < end_at:
        try:
            buttons = driver.find_elements(By.XPATH, SELECTORS["liquids"]["search_button_global"])
            visible = [button for button in buttons if button.is_displayed()]
            if visible:
                return visible[0]
        except Exception:
            pass
        time.sleep(0.2)

    raise RuntimeError("Не знайшов кнопку Пошук на сторінці Рідини")


def _js_set_text_input(driver, inp, value: str) -> None:
    driver.execute_script(
        """
        const el = arguments[0];
        const val = arguments[1];
        el.removeAttribute('readonly');
        el.removeAttribute('disabled');
        el.focus();
        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
        if (setter) {
            setter.call(el, '');
            setter.call(el, val);
        } else {
            el.value = val;
        }
        el.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true, inputType: 'insertText', data: val }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new Event('blur', { bubbles: true }));
        """,
        inp,
        value,
    )
    time.sleep(0.3)


def set_filter_value(driver, filter_name: str, value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if filter_name == "article":
        set_article_value(driver, value)
        return value
    if filter_name == "brand":
        field = find_filter_field(driver, filter_name)
        if is_catalog_search_headless():
            # Scroll field near top of viewport so dropdown opens with room below
            try:
                driver.execute_script(
                    """
                    const rect = arguments[0].getBoundingClientRect();
                    if (rect.top > 300 || rect.top < 0) {
                        window.scrollBy(0, rect.top - 100);
                    }
                    """,
                    field,
                )
            except Exception:
                pass
        select_searchable_quasar_option(driver, field, value)
        return read_field_choice(driver, field) or value
    if filter_name in ("liquid_type", "viscosity"):
        field = find_filter_field(driver, filter_name)
        if is_catalog_search_headless():
            return select_searchable_quasar_option_headless(
                driver,
                field,
                value,
                allow_typed_value=True,
            )
        select_quasar_option(driver, field, value)
        return read_field_choice(driver, field) or value
    inp = find_filter_input(driver, filter_name)
    if is_catalog_search_headless():
        _js_set_text_input(driver, inp, value)
    else:
        quasar_set_value(driver, inp, value)
    return value
